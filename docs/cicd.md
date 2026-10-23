# CI/CD application trên Azure Container Apps

Production dùng Azure Container Apps. Pipeline không phụ thuộc Jira hoặc AI và
không provision hạ tầng Azure. AKS deploy/rollback được giữ lại cho trường hợp
chuyển đích triển khai; chỉ chạy khi `PRODUCTION_TARGET=aks`.

## Luồng phát hành

1. Mở PR vào `main`. `PR CI` chạy backend tests với PostgreSQL 16 thật, coverage
   tối thiểu 70%, frontend tests, production build, dependency audit, Bandit,
   Trivy secret/dependency scan, application deployment policy và deployment tests.
2. Chỉ merge khi `Quality Gate` thành công. `Build Release` gọi lại cùng workflow
   CI trên commit đã merge và yêu cầu commit đó thuộc một PR đã merge vào `main`.
3. Build image runtime, scan HIGH/CRITICAL và secret với exit code khác 0 khi có
   finding. Không bỏ qua lỗ hổng chưa có bản vá. Tạo CycloneDX SBOM, push ACR, lấy
   digest và tạo signed build provenance bằng GitHub artifact attestations.
4. `Deploy Container Apps` chỉ nhận release thành công từ `main` trong cùng
   repository. Job chờ reviewer của Environment `production` phê duyệt. Reviewer
   xem Build Release summary, các báo cáo và artifact `release-evidence` trước
   khi approve.
5. Xác minh checksum, commit, run ID, run attempt, registry và digest. Dùng OIDC
   đăng nhập Azure; kiểm tra cả hai app và khả năng truy cập mạng trước khi update.
6. Deploy backend theo digest, kiểm tra revision và HTTP `/health`, `/ready`,
   `/products/?limit=1`; sau đó deploy frontend và kiểm tra `/`, `/env.js` cùng
   `API_BASE`. Cuối cùng kiểm tra đường truy cập của người dùng, database readiness
   và JSON danh sách sản phẩm. Chỉ sau đó workflow mới thành công.

Coverage 70% là ngưỡng khởi đầu của repository, không phải con số do HLD quy định.
SBOM, signed provenance, image scan reports, manifest và checksum được giữ 90 ngày.
JUnit/coverage, SAST và source scan có artifact riêng trong cùng release run.

## GitHub Actions secrets cần điền

Khai báo các giá trị dưới đây tại Repository Settings → Secrets and variables →
Actions → Secrets. Workflow cũng chấp nhận Actions variables cùng tên; secrets
được ưu tiên. Không cần Azure client secret hoặc kubeconfig dài hạn.

| Secret | Giá trị |
|---|---|
| `ACR_NAME` | Tên registry, không gồm `.azurecr.io` |
| `ACR_LOGIN_SERVER` | `<ACR_NAME>.azurecr.io` |
| `AZURE_BUILD_CLIENT_ID` | Client ID của identity build/push |
| `AZURE_DEPLOY_CLIENT_ID` | Client ID của identity deployment |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription chứa các app |
| `PROD_SMOKE_TEST_URL` | Base URL frontend/gateway mà người dùng truy cập, gồm `https://` |

Giữ database, SMTP, JWT và storage secrets đang chạy trên Container Apps.
Pipeline này cập nhật image và frontend `API_BASE`; không ghi đè các secret đó.

## Actions variables tùy chọn

| Variable | Mặc định hoặc ý nghĩa |
|---|---|
| `PRODUCTION_TARGET` | `container-apps`; đặt `aks` để chuyển sang các workflow AKS thủ công |
| `CONTAINER_APPS_RESOURCE_GROUP` | `ThanhDT03-Lab` |
| `BACKEND_CONTAINER_APP` | `myapp-prod-be` |
| `FRONTEND_CONTAINER_APP` | `myapp-prod-fe` |
| `BACKEND_CONTAINER_NAME` | `backend` |
| `FRONTEND_CONTAINER_NAME` | `frontend` |
| `CONTAINER_APPS_API_BASE` | `/api`; có thể dùng URL HTTPS backend tuyệt đối |
| `DEPLOY_RUNNER_LABELS` | JSON array, mặc định `["ubuntu-latest"]` |

Ví dụ runner trên private network:
`["self-hosted","linux","x64","production-network"]`.
Runner cần `bash`, Azure CLI, `gh`, `jq`, `curl`, khả năng tải action và kết nối
registry. Private app phải có DNS/network route từ runner đến app origin và
customer gateway. Không skip smoke test khi app private. Preflight dừng trước
khi đổi image nếu runner không truy cập được origin.

Apps dùng Single revision mode; backend port 8000, frontend port 8080. Cấu hình
ACR pull identity/credential phải sẵn có. Với `API_BASE=/api`, gateway phải route
`/api` đến backend. Nếu dùng URL backend trực tiếp, cấu hình CORS phù hợp trên app.

## Identity và bảo vệ GitHub

Build identity cần federated subject
`repo:ThanhMiracle/docker:ref:refs/heads/main` và quyền push chỉ trong ACR.
Deployment identity cần subject
`repo:ThanhMiracle/docker:environment:production` và quyền update hai Container
Apps. Container Apps phải có quyền pull ACR. Cấu hình identity/RBAC này được thực
hiện riêng, không nằm trong pipeline provisioning.

Chạy từ repository bằng GitHub CLI có quyền admin:

```powershell
./scripts/configure-github-cicd.ps1 -ProductionReviewer ThanhMiracle
```

Script tạo Environment `production`, required reviewer, hạn chế deployment từ
`main`, đặt target Container Apps và bảo vệ `main` với PR, required `Quality Gate`,
conversation resolution, chặn force push/deletion và admin bypass.

Repository cá nhân mặc định `PullRequestApprovals=0`: vẫn mở PR và chờ `Quality Gate`
thành công, nhưng có thể tự merge mà không cần người khác approve. Script cập nhật
cả review rule trong ruleset đang áp dụng cho `main` và classic branch protection;
tắt yêu cầu approve lần push mới nhất cùng các review bắt buộc khác khi số approval
bằng 0. Chỉ đặt số approval về 0 trong Settings là chưa đủ nếu vẫn bật
`Require approval of the most recent reviewable push`.

Khi có collaborator, truyền `-PullRequestApprovals 1` để yêu cầu một người khác
review và approve lần push mới nhất. GitHub không cho tác giả tự approve PR.
Production reviewer ban đầu được phép duyệt deployment do chính
mình khởi tạo; có thể chọn reviewer khác và bật prevent self-review trong Settings.

## Rollback và failure

Mở workflow `Rollback Container Apps` trên `main`, nhập Build Release run ID của
bản ổn định và lý do. Reviewer phê duyệt tại `production`. Workflow xác minh release
và khôi phục backend/frontend bằng digest, không rebuild, rồi chạy lại cùng health
checks và customer smoke test.

Deploy và rollback dùng chung concurrency group. Khi lỗi, workflow dừng, lưu summary
và revision diagnostics để người vận hành quyết định rollback, recovery hoặc
roll-forward. Nếu backend đã đổi nhưng frontend lỗi, backend vẫn ở phiên bản vừa
đổi; không có rollback ngầm. Rollback image không khôi phục database/schema hoặc
cấu hình app cũ. Kiểm tra tương thích trước khi chọn release để restore.

Release evidence và image ACR cần còn tồn tại. Tạm dừng merge/release mới trong lúc
xử lý incident để deployment tiếp theo không thay đổi phiên bản vừa restore.

## Cập nhật dependency và kiểm tra cục bộ

Frontend dùng `npm ci` với `frontend/package-lock.json`; chạy `npm install` và
commit lockfile khi cập nhật dependency. Build production dùng Vite production mode.

Backend runtime cài dependency đã khóa version/hash từ `requirements.lock.txt`.
JWT dùng PyJWT thay cho python-jose và giữ định dạng HS256; bộ test kiểm tra
tương thích token cũ, thời hạn, chữ ký và giới hạn thuật toán.
Sau khi sửa `backend/requirements.txt`, tạo lại lockfile bằng:

```text
uv pip compile backend/requirements.txt --python-version 3.13 --python-platform x86_64-manylinux_2_28 --generate-hashes --output-file backend/requirements.lock.txt --no-header
```

Deployment tests: `python -m unittest discover -s scripts/tests -v` với PyYAML,
Git Bash và jq trên PATH. Trên Windows, đặt `BASH_EXE` đến Git Bash. Backend tests
mặc định dùng SQLite cục bộ; CI đặt `TEST_DATABASE_URL` đến PostgreSQL service
dùng riêng cho test. Không dùng thông tin kết nối production cho kiểm thử.
