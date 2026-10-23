#!/usr/bin/env bash
set -euo pipefail

base_url="${1:?Usage: smoke-test.sh <application-url> [api-base-url]}"
base_url="${base_url%/}"
api_url="${2:-$base_url/api}"
api_url="${api_url%/}"
request() {
  curl --fail --silent --show-error --location --retry 3 --retry-all-errors \
    --connect-timeout 10 --max-time 30 "$1"
}

# Verify the customer route, not just the Azure control-plane revision state.
request "$base_url/" > /dev/null
request "$api_url/health" | jq -e '.status == "ok"' > /dev/null
request "$api_url/ready" | jq -e '.status == "ready"' > /dev/null
request "$api_url/products/?limit=1" | jq -e \
  'type == "object" and (.items | type == "array") and (.total | type == "number")' > /dev/null

echo "Application, database readiness, and product read smoke tests passed."
