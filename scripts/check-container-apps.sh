#!/usr/bin/env bash
set -euo pipefail
az extension add --name containerapp --upgrade --only-show-errors

check_app() {
  local app="$1" container="$2" port="$3" output="$4"
  local app_json environment_id environment_json
  local ingress_external environment_internal public_network_access
  local fqdn url

  app_json="$(az containerapp show \
    --name "$app" --resource-group "$RESOURCE_GROUP" \
    --output json --only-show-errors)"

  # Keep configured ingress, pull identity, secrets, ports and traffic policy.
  jq -e --arg container "$container" --arg registry "$ACR_LOGIN_SERVER" --argjson port "$port" '
    .properties.configuration.activeRevisionsMode == "Single" and
    .properties.configuration.ingress.targetPort == $port and
    ([.properties.template.containers[] | select(.name == $container)] | length == 1) and
    any(.properties.configuration.registries[]?;
      .server == $registry and
      ((.identity // "") != "" or
       ((.username // "") != "" and (.passwordSecretRef // "") != "")))
  ' <<< "$app_json" > /dev/null || {
    echo "::error::$app requires container $container, port $port, Single revision mode, and an ACR pull identity or credentials for $ACR_LOGIN_SERVER."
    exit 1
  }

  # An app can have external ingress while its ENVIRONMENT is internal.
  # Such an FQDN is private and cannot be probed by GitHub-hosted runners.
  environment_id="$(jq -er '
    (.properties.managedEnvironmentId // .properties.environmentId)
    | select(type == "string" and length > 0)
  ' <<< "$app_json")"

  environment_json="$(az containerapp env show \
    --ids "$environment_id" --output json --only-show-errors)"

  environment_internal="$(jq -r '.properties.vnetConfiguration.internal // false' <<< "$environment_json")"
  public_network_access="$(jq -r '.properties.publicNetworkAccess // "Enabled"' <<< "$environment_json")"
  ingress_external="$(jq -r '.properties.configuration.ingress.external // false' <<< "$app_json")"
  fqdn="$(jq -er '
    .properties.configuration.ingress.fqdn
    | select(type == "string" and length > 0)
  ' <<< "$app_json")"
  # App origins can be private; browser traffic uses the public gateway.
  printf '%s_origin=https://%s\n' "$output" "$fqdn" >> "$GITHUB_OUTPUT"

  url="https://$fqdn"
  if [[ "$environment_internal" == "true" || "$public_network_access" == "Disabled" || "$ingress_external" != "true" ]]; then
    echo "::notice::$app is private. The deployment runner must have network and DNS access to its origin."
  fi
  # Any HTTP response proves reachability, including an unhealthy old revision.
  # Do not require the old application to be healthy before allowing rollback.
  curl --silent --show-error --connect-timeout 10 --max-time 30 \
    --output /dev/null "$url/" || {
    echo "::error::Cannot reach $app before deployment. Configure DEPLOY_RUNNER_LABELS for a runner on the application's private network."
    exit 1
  }

  printf '%s_url=%s\n' "$output" "$url" >> "$GITHUB_OUTPUT"
}

check_app "$BACKEND_APP" "$BACKEND_CONTAINER" 8000 backend
check_app "$FRONTEND_APP" "$FRONTEND_CONTAINER" 8080 frontend

# For image rollback, preserve and verify the current browser routing setting.
if [[ "${DEPLOY_OPERATION:-deploy}" == "rollback" ]]; then
  frontend_api_base="$(az containerapp show \
    --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
    --output json --only-show-errors | jq -er --arg container "$FRONTEND_CONTAINER" '
      .properties.template.containers[] | select(.name == $container)
      | .env[] | select(.name == "API_BASE")
      | .value | select(type == "string" and length > 0
          and (contains("\r") | not) and (contains("\n") | not))
    ')"
  printf 'frontend_api_base=%s\n' "$frontend_api_base" >> "$GITHUB_OUTPUT"
fi
