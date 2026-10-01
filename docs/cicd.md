# GitHub Actions CI/CD for ACR and AKS

Luồng này tách riêng bốn trách nhiệm:

1. `pr-ci.yml`: kiểm tra Jira traceability, test, build, SAST, secret/dependency scan và Helm policy trên pull request.
2. `release.yml`: chạy lại quality gate trên commit đã merge, build ba image đúng một lần, scan, push ACR, lấy digest và xuất SBOM/evidence.
3. `deploy-prod.yml`: tải evidence theo release run ID, chờ approval của GitHub Environment, đăng nhập Azure bằng OIDC và deploy đúng digest bằng Helm.
4. `rollback-prod.yml`: sau quyết định của con người, xác minh revision chứa đúng artifact cũ rồi rollback và chạy lại verification.

Workflow không tự rollback khi verification production thất bại. Log và event được thu thập để người có thẩm quyền chọn rollback, recovery, roll-forward hoặc pause.

## 1. Repository rules

Cấu hình ruleset cho nhánh `master`:

- Require pull request và ít nhất một approval.
- Require conversation resolution.
- Require status check `PR CI / Quality Gate`.
- Require CODEOWNERS review sau khi tạo `.github/CODEOWNERS` với GitHub team thực tế.
- Chặn force push và branch deletion.
- Không cho phép bypass ngoại trừ tài khoản break-glass được kiểm soát.

Tên branch hoặc tiêu đề PR phải chứa Jira key, ví dụ
`feature/APP-123-update-auth`.

## 2. GitHub variables và secrets

Repository variables dùng cho release:

| Variable | Ý nghĩa |
|---|---|
| `ACR_NAME` | Tên ACR, không gồm `.azurecr.io` |
| `ACR_LOGIN_SERVER` | Ví dụ `myacr.azurecr.io` |
| `AZURE_BUILD_CLIENT_ID` | Client ID của identity chỉ có quyền push ACR |
| `AZURE_TENANT_ID` | Microsoft Entra tenant |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |

Tạo GitHub Environment tên `production`, bật Required reviewers và chỉ cho
deploy từ `master`. Khai báo các environment variables:

| Variable | Ý nghĩa |
|---|---|
| `AZURE_DEPLOY_CLIENT_ID` | Client ID của identity deploy AKS |
| `AKS_RESOURCE_GROUP` | Resource group của AKS |
| `AKS_NAME` | Tên AKS |
| `K8S_NAMESPACE` | Mặc định `platform` |
| `PROD_SMOKE_TEST_URL` | URL HTTPS public, không có dấu `/` cuối |
| `KEY_VAULT_ENABLED` | `true` hoặc `false` |
| `KEY_VAULT_NAME` | Bắt buộc khi Key Vault được bật |
| `API_KEYVAULT_CLIENT_ID` | Workload Identity client ID của API |

Environment secrets:

- `DATABASE_URL`: bắt buộc khi `KEY_VAULT_ENABLED=false`; khi bật Key Vault, secret này có thể để trống.
- `JWT_SECRET`, `ADMIN_EMAIL`.
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`.
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.
- `ALERT_WEBHOOK_URL` là tùy chọn.

Không tạo `AZURE_CLIENT_SECRET` hoặc `KUBECONFIG_B64`.

## 3. OIDC và least privilege

Tạo hai app registration hoặc user-assigned managed identity độc lập.

Build identity:

- Federated subject: `repo:<org>/<repo>:ref:refs/heads/master`.
- Role `AcrPush` chỉ tại scope ACR.

Production deploy identity:

- Federated subject: `repo:<org>/<repo>:environment:production`.
- Role `Azure Kubernetes Service Cluster User Role` tại scope AKS.
- Với AKS Azure RBAC, cấp thêm `Azure Kubernetes Service RBAC Writer` tại scope phù hợp. Với Kubernetes RBAC, tạo RoleBinding giới hạn trong namespace `platform`.
- Không cấp quyền push ACR.

AKS kubelet identity cần `AcrPull` tại scope ACR. API Workload Identity cần
`Key Vault Secrets User` chỉ trên vault chứa secret ứng dụng.

## 4. Release và deploy

1. Tạo branch có Jira key, mở PR và hoàn thành review.
2. Merge vào `master`; workflow `Build Release` tạo artifact
   `release-evidence` gồm manifest, ba SBOM và checksum.
3. Lấy run ID từ summary của workflow thành công.
4. Chạy `Deploy Production` với `release_run_id` và Jira key ghi trong manifest.
5. Reviewer kiểm tra Jira, PR, scan, SBOM và các digest ở job
   `Validate release evidence`, sau đó approve environment `production`.
6. Workflow deploy đúng ba reference dạng `repository@sha256:...`, kiểm tra rollout, readiness database, service endpoints, smoke test và digest thực tế trên Pod.

Manifest release là liên kết giữa Jira key, PR, commit, workflow run, image
digests và SBOM. Deployment ghi commit, Jira key và release run ID vào Pod
annotations; GitHub Environment và Azure Activity Log giữ evidence approval và
identity thực thi.

## 5. Failure và rollback

Nếu verification thất bại, không chạy lại release và không build image mới.
Người vận hành xem diagnostics rồi quyết định:

- recovery hoặc roll-forward;
- pause để điều tra;
- chạy `Rollback Production`.

Rollback cần:

- Jira change/incident cho quyết định rollback;
- Helm revision đích;
- Build Release run ID của artifact cần khôi phục;
- lý do quyết định.

Workflow xác minh manifest của Helm revision chứa đúng ba digest từ release
evidence trước khi rollback, sau đó chạy lại toàn bộ rollout, readiness, endpoint,
smoke và digest verification.

## 6. Lưu ý về secret đã từng commit

File production `.env` phải nằm ngoài Git. Nếu credential đã từng xuất hiện
trong lịch sử repository, hãy rotate/revoke credential trước, sau đó purge lịch
sử bằng quy trình được tổ chức phê duyệt. Xóa file ở commit mới không làm secret
biến mất khỏi các commit cũ.
