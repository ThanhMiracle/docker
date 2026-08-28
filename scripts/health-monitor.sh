#!/bin/sh
set -eu

interval="${HEALTHCHECK_INTERVAL_SECONDS:-60}"
webhook_url="${ALERT_WEBHOOK_URL:-}"
was_healthy=true

notify() {
  [ -n "$webhook_url" ] || return 0
  curl -fsS --max-time 10 -X POST -H 'Content-Type: application/json' \
    --data "{\"text\":\"Moss & Market production health check: $1\"}" \
    "$webhook_url" >/dev/null || true
}

while :; do
  if curl -fsS --max-time 10 http://nginx/ >/dev/null \
    && curl -fsS --max-time 10 http://api:8000/health >/dev/null; then
    if [ "$was_healthy" = false ]; then notify "recovered"; fi
    was_healthy=true
  else
    if [ "$was_healthy" = true ]; then notify "FAILED"; fi
    was_healthy=false
  fi
  sleep "$interval"
done
