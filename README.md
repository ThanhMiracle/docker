# Simple Fullstack Docker — v3-fix (Azure Blob Storage)
Features: JWT auth, Products CRUD + ownership, My Products, real image uploads to Azure Blob Storage in production, SPA frontend.

## Run

```bash
docker compose up --build
```

MinIO is built locally from a pinned commit of the official source using
`minio/Dockerfile`, because the community container images are unavailable.
The first build downloads Go dependencies and can take several minutes.
The development Compose file uses this build; local MinIO data stays in
`minio_data`. Production uses Azure Blob Storage.

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
- **Image Uploads:** Production image uploads are stored in Azure Blob Storage; local development uses MinIO.
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

### Azure Blob Storage (production)

Production uploads use Azure Blob Storage with the VM or Container App's existing
managed identity. Set these environment variables on the API container:

```env
STORAGE_BACKEND=azure
AZURE_STORAGE_ACCOUNT_URL=https://your-account.blob.core.windows.net
AZURE_STORAGE_CONTAINER=products
AZURE_CLIENT_ID=
AZURE_STORAGE_AUTO_CREATE_CONTAINER=false
AZURE_STORAGE_CONNECTION_STRING=
AZURE_BLOB_PUBLIC_URL=
AZURE_BLOB_PROXY_URL=/api/files/images
```

The backend uses `DefaultAzureCredential` with the account URL. Leave
`AZURE_CLIENT_ID` blank for a system-assigned identity; set it to the client ID
of your assigned user identity when needed. No account key or connection string
is needed. See [Azure passwordless Blob authentication](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python).

Use your existing container. Container creation is disabled by default so the
API only needs its already-granted Blob read/write permissions. Set
`AZURE_STORAGE_AUTO_CREATE_CONTAINER=true` only if you want the API to create a
missing container and the identity has permission to do so.

Without `AZURE_BLOB_PUBLIC_URL`, uploads return stable API URLs such as
`/api/files/images/products/<object-key>`. The backend streams these objects
using the same identity, so the Blob container can stay private. Uploaded images
remain accessible to shop visitors through the API, like the previous MinIO
image URLs. A public CDN/custom base URL (including its container path) can be
set in `AZURE_BLOB_PUBLIC_URL` to bypass the API for image delivery.

With Compose/Nginx, use the default `AZURE_BLOB_PROXY_URL=/api/files/images`.
For a Container App exposing FastAPI directly, set it to the browser-reachable
API URL plus `/files/images`, for example
`https://your-api.example.com/files/images`. Azure Container Apps supplies its
managed identity endpoint to the container automatically. VM Docker containers
must be able to reach the VM's managed identity endpoint.

Connection-string authentication remains available when
`AZURE_STORAGE_ACCOUNT_URL` is empty. Keep `AZURE_STORAGE_CONNECTION_STRING`
in deployment secrets. When an account URL is provided, identity authentication
takes precedence.

Rebuild and publish the API image from `backend/` to include `azure-identity`
and the new image-read route before deploying it.

To deploy after configuring the environment:

```bash
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans
```

Existing MinIO uploads and database image URLs are not migrated by this change.
Copy the objects to Blob Storage and update their saved URLs before removing the
old MinIO deployment. Keep the existing MinIO volume until migration is verified.

See [Azure Blob read access](https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-overview)
for access configuration.

### Local MinIO testing

The default `docker-compose.yml` continues to use MinIO:

```bash
docker compose up --build
```

Local uploads use the `uploads` bucket and are available through
`http://localhost/uploads/<object-key>`. No Azure credentials are needed for
local testing.

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

## GitHub Actions CI/CD for Azure

Production delivery uses separate PR validation, immutable ACR release,
approved AKS deployment, and controlled rollback workflows. Azure access uses
GitHub OIDC; no long-lived Azure client secret or kubeconfig is required.

See [CI/CD setup and operations](docs/cicd.md) for the required GitHub
Environment, repository variables, Azure roles, approval flow, and rollback
procedure.

....
