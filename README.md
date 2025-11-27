# Simple Fullstack Docker — v3-fix (MinIO + esbuild fixed)
Features: JWT auth, Products CRUD + ownership, My Products, real image uploads to MinIO, SPA frontend.

## Run

```bash
docker compose up --build
```

Open:
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001  (user/pass: minioadmin / minioadmin)

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
- **Image Uploads:** Real image uploads are supported and stored in a local MinIO S3-compatible object storage.
- **DevOps:** All services (frontend, backend, MinIO, database) are orchestrated with Docker Compose for easy local development and testing.
- **Testing:** Backend tests are written with pytest and can be run inside the API container.
- **Infrastructure as Code:** Terraform scripts are included for provisioning cloud infrastructure if you want to deploy the stack outside local Docker.

### Main Technologies

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, MinIO SDK
- **Frontend:** React, esbuild
- **DevOps:** Docker, Docker Compose
- **Testing:** pytest
- **Infrastructure:** Terraform

### Folder Structure

- `api/` — FastAPI backend source code
- `frontend/` — React frontend source code
- `minio/` — MinIO configuration (if any)
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
### Postgres
- POSTGRES_USER=
- POSTGRES_PASSWORD=
- POSTGRES_DB=

### API
- DATABASE_URL=
- JWT_SECRET=
- JWT_EXPIRE_MINUTES=

### MinIO
- MINIO_ACCESS_KEY=
- MINIO_SECRET_KEY=
- MINIO_ENDPOINT=http://minio:9000
- MINIO_BUCKET=uploads
- MINIO_SECURE=false

### Expose public URLs
- MINIO_PUBLIC_URL=http://{public_IP}/minio-public

- VITE_API_BASE={public_IP}/api
