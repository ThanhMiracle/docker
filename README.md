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
1) `npm install --package-lock-only` to create a fresh, in-sync lockfile from package.json
2) `npm ci` for reproducible, clean installs
This avoids EUSAGE lock mismatch errors.



## ✅ Chạy test backend (pytest)
Trong container:
```bash
docker compose up -d
docker compose exec api pytest -q
```
