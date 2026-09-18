#!/bin/sh

set -u

ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
HEALTHCHECK_INTERVAL_SECONDS="${HEALTHCHECK_INTERVAL_SECONDS:-60}"

NGINX_HEALTH_URL="${NGINX_HEALTH_URL:-http://nginx/health}"
API_HEALTH_URL="${API_HEALTH_URL:-http://api:8000/health}"

NGINX_PREVIOUS_STATE="unknown"
API_PREVIOUS_STATE="unknown"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

send_alert() {
  message="$1"

  if [ -z "$ALERT_WEBHOOK_URL" ]; then
    log "Webhook not configured. Alert: $message"
    return 0
  fi

  escaped_message=$(printf '%s' "$message" | sed 's/\\/\\\\/g; s/"/\\"/g')

  curl \
    --silent \
    --show-error \
    --fail \
    --connect-timeout 5 \
    --max-time 10 \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"${escaped_message}\"}" \
    "$ALERT_WEBHOOK_URL" \
    >/dev/null 2>&1 || log "Failed to send webhook alert."
}

check_health() {
  url="$1"

  if curl \
    --silent \
    --fail \
    --connect-timeout 5 \
    --max-time 10 \
    "$url" \
    >/dev/null 2>&1
  then
    echo "healthy"
  else
    echo "unhealthy"
  fi
}

handle_state_change() {
  service_name="$1"
  current_state="$2"
  previous_state="$3"

  if [ "$current_state" != "$previous_state" ]; then
    case "$current_state" in
      healthy)
        message="✅ ${service_name} is HEALTHY"
        ;;
      unhealthy)
        message="🚨 ${service_name} is UNHEALTHY"
        ;;
      *)
        message="${service_name} state changed to ${current_state}"
        ;;
    esac

    log "$message"
    send_alert "$message"
  fi
}

log "Starting health monitor."
log "Nginx: $NGINX_HEALTH_URL"
log "API:   $API_HEALTH_URL"
log "Interval: ${HEALTHCHECK_INTERVAL_SECONDS}s"

while true; do
  NGINX_CURRENT_STATE=$(check_health "$NGINX_HEALTH_URL")
  API_CURRENT_STATE=$(check_health "$API_HEALTH_URL")

  handle_state_change \
    "nginx" \
    "$NGINX_CURRENT_STATE" \
    "$NGINX_PREVIOUS_STATE"

  handle_state_change \
    "api" \
    "$API_CURRENT_STATE" \
    "$API_PREVIOUS_STATE"

  NGINX_PREVIOUS_STATE="$NGINX_CURRENT_STATE"
  API_PREVIOUS_STATE="$API_CURRENT_STATE"

  sleep "$HEALTHCHECK_INTERVAL_SECONDS"
done