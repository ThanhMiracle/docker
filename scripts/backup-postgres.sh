#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
OUTPUT="$BACKUP_DIR/mydb-${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump -U postgres -d mydb | gzip > "$OUTPUT"
echo "Backup created: $OUTPUT"
