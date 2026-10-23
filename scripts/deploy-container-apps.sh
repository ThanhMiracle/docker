#!/usr/bin/env bash
set -euo pipefail
test -n "$FRONTEND_API_BASE"
test -n "${BACKEND_URL:?Backend origin is required for the health gate}"
test -n "${FRONTEND_URL:?Frontend origin is required for the health gate}"

deploy_app() {
  local app="$1" container="$2" image="$3" output="$4" url="$5"
  local suffix="${REVISION_PREFIX:-gh}${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
  local revision revision_json app_json state
  local -a paths
  local -a runtime_args=()

  if [[ "$output" == "frontend" && "${DEPLOY_OPERATION:-deploy}" != "rollback" ]]; then
    # Front Door and Application Gateway route /api to the private backend.
    runtime_args=(--set-env-vars "API_BASE=$FRONTEND_API_BASE")
  fi

  revision="$(az containerapp update \
    --name "$app" --resource-group "$RESOURCE_GROUP" \
    --container-name "$container" --image "$image" \
    "${runtime_args[@]}" \
    --revision-suffix "$suffix" \
    --query properties.latestRevisionName --output tsv --only-show-errors)"

  if [[ "$revision" != "$app--$suffix" ]]; then
    echo "::error::Unexpected revision for $app: $revision"
    exit 1
  fi

  printf '%s_revision=%s\n' "$output" "$revision" >> "$GITHUB_OUTPUT"

  # Verify the new image, healthy revision, and ready traffic target.
  for attempt in {1..60}; do
    revision_json="$(az containerapp revision show \
      --name "$app" --resource-group "$RESOURCE_GROUP" \
      --revision "$revision" --output json --only-show-errors)"
    app_json="$(az containerapp show \
      --name "$app" --resource-group "$RESOURCE_GROUP" \
      --output json --only-show-errors)"

    if jq -e --arg container "$container" --arg image "$image" '
      .properties.active == true and
      .properties.provisioningState == "Provisioned" and
      .properties.healthState == "Healthy" and
      any(.properties.template.containers[]; .name == $container and .image == $image)
    ' <<< "$revision_json" > /dev/null &&
      [[ "$(jq -r '.properties.latestReadyRevisionName' <<< "$app_json")" == "$revision" ]]; then
      echo "$app is serving verified revision $revision."
      break
    fi

    state="$(jq -r '.properties.provisioningState' <<< "$revision_json")"
    if [[ "$state" == "Failed" || "$state" == "ProvisioningFailed" || "$attempt" == 60 ]]; then
      echo "::error::$app revision $revision failed to become healthy and ready (state: $state)."
      exit 1
    fi

    echo "Waiting for $app revision $revision ($attempt/60)..."
    sleep 10
  done

  # Check private and public origins using the deployment runner's network.
  # Backend health endpoints are /health and /ready (not /api/health).
  if [[ "$output" == "backend" ]]; then
    paths=(/health /ready '/products/?limit=1')
  else
    paths=(/)
  fi

  for path in "${paths[@]}"; do
    curl --fail --silent --show-error --location \
      --connect-timeout 10 --max-time 30 \
      --retry 5 --retry-delay 10 --retry-all-errors \
      --output /dev/null "$url$path"
    echo "Smoke test passed: $app $path"
  done

  if [[ "$output" == "frontend" ]]; then
    # HTTP 200 alone can conceal an empty or cached runtime configuration.
    curl --fail --silent --show-error --location \
      --connect-timeout 10 --max-time 30 \
      --retry 5 --retry-delay 10 --retry-all-errors \
      --output "$RUNNER_TEMP/frontend-env.js" "$url/env.js?deployment=$suffix"
    grep -F -- "\"$FRONTEND_API_BASE\"" "$RUNNER_TEMP/frontend-env.js" > /dev/null || {
      echo "::error::Frontend env.js does not contain the deployed API_BASE."
      exit 1
    }
    echo "Runtime configuration check passed: $app /env.js"
  fi
}

# Preserve app secrets and identities; supply frontend browser routing.
deploy_app "$BACKEND_APP" "$BACKEND_CONTAINER" "$BACKEND_IMAGE" backend "$BACKEND_URL"
deploy_app "$FRONTEND_APP" "$FRONTEND_CONTAINER" "$FRONTEND_IMAGE" frontend "$FRONTEND_URL"
