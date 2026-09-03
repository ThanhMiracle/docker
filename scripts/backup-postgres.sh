#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
ENV_FILE="${ENV_FILE:-.env}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
OUTPUT="$BACKUP_DIR/mydb-${TIMESTAMP}.sql.gz"

if [ -z "${DATABASE_URL:-}" ] && [ -f "$ENV_FILE" ]; then
  # Read only the database URL; do not source a dotenv file as shell code.
  DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' "$ENV_FILE" | tail -n 1)"
fi

if [ -n "${DATABASE_URL:-}" ]; then
  docker run --rm -e PGPASSWORD="${PGPASSWORD:-}" postgres:15-alpine \
    pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip > "$OUTPUT"
else
  # Local Compose fallback where the database is a service in this project.
  docker compose exec -T db pg_dump -U postgres -d mydb | gzip > "$OUTPUT"
fi

find "$BACKUP_DIR" -type f -name 'mydb-*.sql.gz' -mtime "+$RETENTION_DAYS" -delete
echo "Backup created: $OUTPUT"
