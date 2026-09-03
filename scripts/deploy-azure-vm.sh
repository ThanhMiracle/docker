#!/usr/bin/env bash
set -euo pipefail

AZURE_VM_HOST="${1:-}"
AZURE_VM_USER="${2:-}"
SSH_KEY="${3:-}"
DEPLOY_PATH="${4:-/opt/my-app}"
IMAGE_TAG="${5:-}"
PUBLIC_BASE_URL="${6:-}"
FRONTEND_IMAGE="${7:-thanh2909/my-frontend}"
API_IMAGE="${8:-thanh2909/my-api}"
SSH_KNOWN_HOSTS="${9:-}"

for name in AZURE_VM_HOST AZURE_VM_USER SSH_KEY IMAGE_TAG PUBLIC_BASE_URL SSH_KNOWN_HOSTS; do
  if [ -z "${!name}" ]; then
    echo "$name is required" >&2
    exit 1
  fi
done
case "$DEPLOY_PATH" in /*) ;; *) echo "DEPLOY_PATH must be absolute" >&2; exit 1 ;; esac
case "$PUBLIC_BASE_URL" in http://*|https://*) ;; *) echo "PUBLIC_BASE_URL must begin with http:// or https://" >&2; exit 1 ;; esac

TARGET="${AZURE_VM_USER}@${AZURE_VM_HOST}"
SSH_OPTIONS=(
  -i "$SSH_KEY"
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$SSH_KNOWN_HOSTS"
)

ssh "${SSH_OPTIONS[@]}" "$TARGET" \
  "install -d -m 755 '$DEPLOY_PATH/nginx' '$DEPLOY_PATH/scripts'"

scp "${SSH_OPTIONS[@]}" docker-compose.prod.yml "$TARGET:$DEPLOY_PATH/docker-compose.prod.yml"
scp "${SSH_OPTIONS[@]}" nginx/nginx.prod.conf "$TARGET:$DEPLOY_PATH/nginx/nginx.prod.conf"
scp "${SSH_OPTIONS[@]}" scripts/health-monitor.sh scripts/backup-postgres.sh \
  "$TARGET:$DEPLOY_PATH/scripts/"

ssh "${SSH_OPTIONS[@]}" "$TARGET" /bin/bash -s -- \
  "$DEPLOY_PATH" "$IMAGE_TAG" "${PUBLIC_BASE_URL%/}" "$FRONTEND_IMAGE" "$API_IMAGE" <<'REMOTE'
set -euo pipefail
deploy_path="$1"
image_tag="$2"
public_base_url="$3"
frontend_image="$4"
api_image="$5"
env_file="$deploy_path/.env"

if [ ! -f "$env_file" ]; then
  echo "Missing $env_file. Create it on the Azure VM (preferably from Azure Key Vault) before deploying." >&2
  exit 1
fi

chmod 600 "$env_file"
sed -i '/^API_BASE=/d;/^FRONTEND_BASE_URL=/d;/^FRONTEND_IMAGE=/d;/^API_IMAGE=/d' "$env_file"
printf 'API_BASE=%s/api\nFRONTEND_BASE_URL=%s\nFRONTEND_IMAGE=%s\nAPI_IMAGE=%s\n' \
  "$public_base_url" "$public_base_url" "$frontend_image" "$api_image" >> "$env_file"
chmod 755 "$deploy_path/scripts/health-monitor.sh" "$deploy_path/scripts/backup-postgres.sh"

cd "$deploy_path"
export IMAGE_TAG="$image_tag"
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
docker compose --env-file .env -f docker-compose.prod.yml pull
docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans
docker compose --env-file .env -f docker-compose.prod.yml ps

for attempt in $(seq 1 12); do
  if docker compose --env-file .env -f docker-compose.prod.yml exec -T api \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    && docker compose --env-file .env -f docker-compose.prod.yml exec -T nginx \
      wget -q -O /dev/null http://localhost/; then
    echo "Deployment health checks passed."
    exit 0
  fi
  sleep 5
done

echo "Deployment health checks failed." >&2
exit 1
REMOTE
