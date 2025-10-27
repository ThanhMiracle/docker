#!/bin/sh

# tạo file env.js mỗi lần container start
cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = {
  API_BASE: "${API_BASE}"
};
EOF

# chạy nginx (CMD của Dockerfile sẽ được nối vào đây qua exec "$@")
exec "$@"
