#!/usr/bin/env bash
set -euo pipefail

namespace="${1:?Usage: verify-deployment.sh <namespace> <api-digest> <frontend-digest> <nginx-digest>}"
api_digest="${2:?Missing API digest}"
frontend_digest="${3:?Missing frontend digest}"
nginx_digest="${4:?Missing Nginx digest}"

validate_digest() {
  [[ "$1" =~ ^sha256:[a-f0-9]{64}$ ]] || {
    echo "Invalid image digest: $1" >&2
    exit 2
  }
}

verify_workload() {
  local workload="$1"
  local expected_digest="$2"
  local image_ids

  kubectl rollout status "deployment/${workload}" --namespace "$namespace" --timeout=300s
  kubectl get pods --namespace "$namespace" --selector "app=${workload}" -o wide

  image_ids="$(kubectl get pods --namespace "$namespace" --selector "app=${workload}" \
    -o jsonpath='{range .items[*].status.containerStatuses[*]}{.imageID}{"\n"}{end}')"
  [[ -n "$image_ids" ]] || {
    echo "No running image ID found for ${workload}" >&2
    exit 1
  }
  grep --fixed-strings --quiet "$expected_digest" <<<"$image_ids" || {
    echo "${workload} is not running approved digest ${expected_digest}" >&2
    printf '%s\n' "$image_ids" >&2
    exit 1
  }
}

validate_digest "$api_digest"
validate_digest "$frontend_digest"
validate_digest "$nginx_digest"

verify_workload api "$api_digest"
verify_workload frontend "$frontend_digest"
verify_workload nginx "$nginx_digest"

for service in api frontend nginx minio; do
  endpoints="$(kubectl get endpoints "$service" --namespace "$namespace" \
    -o jsonpath='{.subsets[*].addresses[*].ip}')"
  [[ -n "$endpoints" ]] || {
    echo "Service ${service} has no Ready endpoints" >&2
    exit 1
  }
done

echo "All workloads are Ready, service endpoints exist, and approved image digests are running."
