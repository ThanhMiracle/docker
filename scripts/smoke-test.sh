#!/usr/bin/env bash
set -euo pipefail

# Pass the public production URL explicitly so the test verifies the same path
# customers use. Example: ./scripts/smoke-test.sh https://shop.example.com
base_url="${1:?Usage: smoke-test.sh <public-base-url>}"
base_url="${base_url%/}"

curl --fail --silent --show-error --retry 3 --retry-all-errors \
  --connect-timeout 10 --max-time 30 \
  "${base_url}/health" >/dev/null

curl --fail --silent --show-error --retry 3 --retry-all-errors \
  --connect-timeout 10 --max-time 30 \
  "${base_url}/api/health" >/dev/null

# Readiness includes a real database round-trip, so this also verifies the
# most important application dependency from the customer-facing route.
curl --fail --silent --show-error --retry 3 --retry-all-errors \
  --connect-timeout 10 --max-time 30 \
  "${base_url}/api/ready" >/dev/null

echo "Smoke tests passed for ${base_url}"
