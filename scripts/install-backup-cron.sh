#!/usr/bin/env bash
set -euo pipefail

# Run this on exactly one designated production host, not every ASG instance.
PROJECT_DIR="${1:-/opt/my-app}"
SCHEDULE="${BACKUP_CRON_SCHEDULE:-15 2 * * *}"
LOG_FILE="${BACKUP_LOG_FILE:-/var/log/my-app-postgres-backup.log}"

ENTRY="${SCHEDULE} cd ${PROJECT_DIR} && ENV_FILE=.env ./scripts/backup-postgres.sh ${PROJECT_DIR}/backups >> ${LOG_FILE} 2>&1"
(crontab -l 2>/dev/null | grep -Fv 'backup-postgres.sh' || true; echo "$ENTRY") | crontab -
echo "Installed backup schedule: $SCHEDULE"
