# Simple Fullstack Docker — v3-fix (Amazon S3)
Features: JWT auth, Products CRUD + ownership, My Products, real image uploads to Amazon S3, SPA frontend.

## Run

```bash
docker compose up --build
```

Open:
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- MinIO console (local testing): http://localhost:9001 (`minioadmin` / `minioadmin`)

If you need to reset data:
```bash
docker compose down -v
docker compose up --build
```

## Frontend build with npm ci (lockfile generated inside image)

The frontend Dockerfile now runs:
1. `npm install --package-lock-only` to create a fresh, in-sync lockfile from package.json
2. `npm ci` for reproducible, clean installs

This avoids EUSAGE lock mismatch errors.

## ✅ Chạy test backend (pytest)

Trong container:
```bash
docker compose up -d
docker compose exec api pytest -q
```

## Project Overview

This project is a simple fullstack web application demonstrating modern development practices with Docker. It features:

- **Backend:** FastAPI (Python) REST API with JWT authentication, user registration/login, and CRUD operations for products. Each product is owned by a user.
- **Frontend:** Single Page Application (SPA) built with React and esbuild, providing a user-friendly interface for authentication and product management.
- **Image Uploads:** Real image uploads are stored in Amazon S3.
- **DevOps:** The frontend, backend, and database are orchestrated with Docker Compose.
- **Testing:** Backend tests are written with pytest and can be run inside the API container.
- **Infrastructure as Code:** Terraform scripts are included for provisioning cloud infrastructure if you want to deploy the stack outside local Docker.

### Main Technologies

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, boto3
- **Frontend:** React, esbuild
- **DevOps:** Docker, Docker Compose
- **Testing:** pytest
- **Infrastructure:** Terraform

### Folder Structure

- `api/` — FastAPI backend source code
- `frontend/` — React frontend source code
- `terraform/` — Infrastructure as Code scripts for provisioning cloud resources (e.g., servers, databases, object storage) using Terraform. Useful for deploying the stack to AWS, GCP, or other providers.
- `docker-compose.yml` — Service orchestration

### Typical Use Cases

- User registration and login with JWT tokens
- Create, read, update, and delete products (CRUD)
- Upload and manage product images
- View only your own products ("My Products" feature)
- Explore API documentation via Swagger UI
- Provision and manage cloud infrastructure using Terraform

For more details, see the code and comments in each directory.


### Reload/restart Nginx để nó resolve lại DNS:

docker exec proxy nginx -s reload || docker restart proxy


## Add .env file with this structure for product
### Local PostgreSQL (development only)
- POSTGRES_USER=
- POSTGRES_PASSWORD=
- POSTGRES_DB=

### Production API / RDS
- DATABASE_URL=postgresql://db_user:db_password@your-rds-endpoint:5432/db_name
- JWT_SECRET=
- JWT_EXPIRE_MINUTES=

### Amazon S3
- AWS_REGION=ap-southeast-1
- AWS_S3_BUCKET=your-upload-bucket
- AWS_ACCESS_KEY_ID=
- AWS_SECRET_ACCESS_KEY=
- AWS_SESSION_TOKEN= (only for temporary credentials)

On EC2/ECS, prefer an IAM role and omit the three credential variables. The role
needs `s3:PutObject` on `arn:aws:s3:::your-upload-bucket/*`.

### Public image URLs
- AWS_S3_PUBLIC_URL= (optional CloudFront/custom base URL)

If `AWS_S3_PUBLIC_URL` is omitted, the API returns the standard regional S3 URL.
The bucket/object must be publicly readable for browsers to display that URL.
For a private bucket, put CloudFront in front of it and set `AWS_S3_PUBLIC_URL`
to the distribution URL.

### Local MinIO testing

The default `docker-compose.yml` uses MinIO automatically while production
continues to use AWS S3:

```bash
docker compose up --build
```

Local uploads use the `uploads` bucket and are available through
`http://localhost:9008/uploads/<object-key>`. You do not need AWS credentials
for local testing. `docker-compose.prod.yml` explicitly disables the custom S3
endpoint and bucket auto-creation.

### Production database (Amazon RDS)

`docker-compose.prod.yml` does not run a PostgreSQL container. Set
`DATABASE_URL` to the RDS PostgreSQL connection string:

```env
DATABASE_URL=postgresql://db_user:db_password@your-rds-endpoint:5432/db_name
```

The RDS security group must allow PostgreSQL traffic on port `5432` from the
EC2 instance or ECS service running the API. Prefer referencing the
application's security group instead of allowing public access.

- VITE_API_BASE={public_IP}/api

## Production HTTPS, backups, and alerts

Production TLS terminates at an Azure gateway such as Application Gateway or
Front Door. Configure a certificate, redirect HTTP to HTTPS, and point your
domain DNS record to that gateway. Then set these values in the production
environment on the Azure VM:

```env
FRONTEND_BASE_URL=https://shop.example.com
API_BASE=https://shop.example.com/api
CORS_ORIGINS=https://shop.example.com
```

Set Jenkins `PUBLIC_BASE_URL` to `https://shop.example.com`; this ensures links
in verification and order emails use your domain rather than a VM IP address.

The `health-monitor` production service checks both Nginx and the API every 60
seconds. Set `ALERT_WEBHOOK_URL` to a Slack-compatible incoming webhook to get
an alert on a failure and a recovery message. Leave it blank to disable alerts.

To schedule PostgreSQL backups, run the following on one designated production
host:

```bash
cd /opt/my-app
BACKUP_CRON_SCHEDULE='15 2 * * *' ./scripts/install-backup-cron.sh /opt/my-app
```

Backups are written to `/opt/my-app/backups` and `BACKUP_RETENTION_DAYS`
controls automatic cleanup. Copy these archives to durable off-host storage.

## Jenkins CI/CD for Azure VM

The pipeline tests the API, builds and pushes tagged Docker Hub images, then
deploys the production Compose files to one Azure Linux VM using SSH.

Create these Jenkins credentials:

- `dockerhub-cred`: Docker Hub username and access token.
- `sonarqube-token`: SonarQube project analysis token stored as Secret text.
- `azure-vm-ssh`: SSH private key authorized for the Azure VM.
- `azure-vm-known-hosts`: Secret file containing the Azure VM's verified SSH host key.

Before the first deployment, install Docker Compose on the VM and create
`/opt/my-app/.env` with the real production values. Keep it mode `600`; use
Azure Key Vault to provision or rotate its secrets. Jenkins does not copy
secrets to the VM.

Set `AZURE_VM_HOST`, `DEPLOY_PATH`, and `PUBLIC_BASE_URL` in the Jenkins build
parameters. The SSH username comes from `azure-vm-ssh`. The real `.env` is
intentionally ignored by Git. Never commit it.

Use the `COMPONENT` build parameter to select the pipeline scope:

- `backend`: test, build, and push only the API image.
- `frontend`: build and push only the frontend image.
- `all`: build and push both images, then deploy them together from `main`.

Push stages run only on `main`. Deployment also requires `COMPONENT=all`, which
prevents Compose from deploying two services with a tag built for only one of
them.

Obtain the VM host key from a trusted source (for example, the VM console or
your provisioning output), save it in OpenSSH `known_hosts` format, and upload
that file to Jenkins as a Secret file with ID `azure-vm-known-hosts`. Do not
build this file from an unverified `ssh-keyscan` result inside the pipeline.

## SonarQube and Trivy checks

Create the `docker-shop` project in SonarQube, generate a project analysis
token, and store it in Jenkins as a Secret text credential with ID
`sonarqube-token`. Set the Jenkins `SONAR_HOST_URL` parameter to a URL that is
reachable from a Docker container on the Jenkins agent. If SonarQube runs on
the same machine, `localhost` inside the scanner container is not the host;
use a resolvable container name, host gateway, private IP, or DNS name.

The SonarScanner configuration is in `sonar-project.properties`. Analysis runs
on every branch and waits for the SonarQube quality gate, so a failed gate
blocks the image build and any later push or deployment.

Trivy uses the pinned official scanner container and scans each selected image
after it is built. Fixable HIGH or CRITICAL vulnerabilities fail the pipeline
before Docker Hub push. Its vulnerability database is cached in the Docker
volume `trivy-cache`; no additional Jenkins credential or plugin is required.
