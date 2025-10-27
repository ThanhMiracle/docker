#!/bin/sh
set -e

HTML_DIR=/usr/share/nginx/html

# inject runtime env vào env.js
if [ -n "$API_BASE" ]; then
  sed -i "s|__API_BASE__|$API_BASE|g" "$HTML_DIR/env.js"
#else
  # fallback nếu không set từ docker-compose
# sed -i "s|__API_BASE__|http://localhost:8000|g" "$HTML_DIR/env.js"
fi

exec "$@"
