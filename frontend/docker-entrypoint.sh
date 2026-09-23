#!/bin/sh

set -e

echo "Generating runtime env.js..."
echo "API_BASE=${API_BASE}"

cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = {
  API_BASE: "${API_BASE}"
};
EOF

echo "Generated env.js:"
cat /usr/share/nginx/html/env.js

exec "$@"