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

## Jenkins CI/CD

The `Jenkinsfile` runs three CI/CD phases:

1. **Test** — builds and runs the backend pytest image and compiles the frontend.
2. **Build/Push** — builds both production images, tags them with the Jenkins
   build number, and pushes them to Docker Hub.
3. **Deploy** — on the `main` branch, sends an SSM Run Command to every managed
   instance in the selected Auto Scaling Group. Each instance retrieves the
   production environment and runs Docker Compose locally.

The Jenkins agent does not deploy locally. It uses AWS Systems Manager Run
Command to deploy to all SSM-managed instances carrying the target Auto Scaling
Group tag. The Jenkins agent needs AWS CLI and `jq`.

Create these Jenkins credentials:

- `dockerhub-credentials`: **Username with password**, containing the Docker Hub
  username and access token.

Store the contents of `.env.example`, with real production values, as an SSM
Parameter Store **SecureString**. The default parameter name is
`/my-app/production/env`. Do not include `API_BASE`; deployment discovers and
adds it automatically.

Set the build parameters:

- `ALB_NAME`: the Application Load Balancer name, not its ARN or DNS name.
- `ALB_SCHEME`: `https` when the ALB has a public HTTPS listener, otherwise
  `http`.
- `AWS_DEPLOY_REGION`: the AWS region containing the ALB.
- `ASG_NAME`: the Auto Scaling Group name. All its currently managed instances
  are targeted through the `aws:autoscaling:groupName` tag.
- `PROD_ENV_PARAMETER`: the SSM SecureString parameter containing `.env`.

During deployment Jenkins resolves the current ALB DNS name with AWS CLI and
writes this value into the temporary `.env`:

```env
API_BASE=https://resolved-alb-dns-name/api
```

The Jenkins role needs:

- `elasticloadbalancing:DescribeLoadBalancers`
- `ssm:SendCommand`
- `ssm:DescribeInstanceInformation`
- `ssm:ListCommands`
- `ssm:ListCommandInvocations`

Each ASG instance needs SSM Agent, AWS CLI, Docker, Compose v2, and an instance
role with `ssm:GetParameter` for the environment parameter plus `kms:Decrypt`
when a customer-managed KMS key protects it.

For a manual deployment on the production host:

```bash
cp .env.example .env
# Edit .env with real production values.
chmod 600 .env
docker compose --env-file .env -f docker-compose.prod.yml pull
docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans
```

The real `.env` is intentionally ignored by Git. Never commit it.
