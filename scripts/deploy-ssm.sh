#!/usr/bin/env bash
set -euo pipefail

ASG_NAME="${1:-}"
ALB_NAME="${2:-}"
ALB_SCHEME="${3:-https}"
AWS_DEPLOY_REGION="${4:-}"
PROD_ENV_PARAMETER="${5:-}"
IMAGE_TAG="${6:-}"

for value_name in ASG_NAME ALB_NAME AWS_DEPLOY_REGION PROD_ENV_PARAMETER IMAGE_TAG; do
  if [ -z "${!value_name}" ]; then
    echo "$value_name is required" >&2
    exit 1
  fi
done

for required_command in aws jq base64; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "$required_command is required on the Jenkins agent" >&2
    exit 1
  fi
done

ALB_DNS_NAME="$(
  aws elbv2 describe-load-balancers \
    --names "$ALB_NAME" \
    --region "$AWS_DEPLOY_REGION" \
    --query 'LoadBalancers[0].DNSName' \
    --output text
)"

if [ -z "$ALB_DNS_NAME" ] || [ "$ALB_DNS_NAME" = "None" ]; then
  echo "Could not resolve DNS name for ALB: $ALB_NAME" >&2
  exit 1
fi

MANAGED_INSTANCE_COUNT="$(
  aws ssm describe-instance-information \
    --region "$AWS_DEPLOY_REGION" \
    --filters "Key=tag:aws:autoscaling:groupName,Values=${ASG_NAME}" \
    --query 'length(InstanceInformationList)' \
    --output text
)"

if [ "$MANAGED_INSTANCE_COUNT" -eq 0 ]; then
  echo "No SSM-managed instances found in ASG: $ASG_NAME" >&2
  exit 1
fi

echo "Deploying to $MANAGED_INSTANCE_COUNT SSM-managed ASG instance(s)"

COMPOSE_BASE64="$(base64 -w 0 docker-compose.prod.yml)"
NGINX_BASE64="$(base64 -w 0 nginx/nginx.conf)"
API_BASE="${ALB_SCHEME}://${ALB_DNS_NAME}/api"

COMMAND_PARAMETERS="$(
  jq -n \
    --arg compose "$COMPOSE_BASE64" \
    --arg nginx "$NGINX_BASE64" \
    --arg region "$AWS_DEPLOY_REGION" \
    --arg env_parameter "$PROD_ENV_PARAMETER" \
    --arg api_base "$API_BASE" \
    --arg image_tag "$IMAGE_TAG" \
    '{
      commands: [
        "set -eu",
        "install -d -m 755 /opt/my-app/nginx",
        ("printf %s " + ($compose | @sh) + " | base64 -d > /opt/my-app/docker-compose.prod.yml"),
        ("printf %s " + ($nginx | @sh) + " | base64 -d > /opt/my-app/nginx/nginx.conf"),
        ("aws ssm get-parameter --name " + ($env_parameter | @sh) + " --with-decryption --region " + ($region | @sh) + " --query Parameter.Value --output text > /opt/my-app/.env"),
        "chmod 600 /opt/my-app/.env",
        "sed -i '\''/^API_BASE=/d'\'' /opt/my-app/.env",
        ("printf '\''API_BASE=%s\\\\n'\'' " + ($api_base | @sh) + " >> /opt/my-app/.env"),
        "cd /opt/my-app",
        ("export IMAGE_TAG=" + ($image_tag | @sh)),
        "docker compose --env-file .env -f docker-compose.prod.yml config --quiet",
        "docker compose --env-file .env -f docker-compose.prod.yml pull",
        "docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans",
        "docker compose --env-file .env -f docker-compose.prod.yml ps"
      ],
      executionTimeout: ["900"]
    }'
)"

COMMAND_ID="$(
  aws ssm send-command \
    --region "$AWS_DEPLOY_REGION" \
    --document-name AWS-RunShellScript \
    --comment "Deploy my-app image ${IMAGE_TAG}" \
    --targets "Key=tag:aws:autoscaling:groupName,Values=${ASG_NAME}" \
    --parameters "$COMMAND_PARAMETERS" \
    --timeout-seconds 900 \
    --max-concurrency 100% \
    --max-errors 0 \
    --query 'Command.CommandId' \
    --output text
)"

echo "SSM deployment command: $COMMAND_ID"

while :; do
  COMMAND_STATUS="$(
    aws ssm list-commands \
      --region "$AWS_DEPLOY_REGION" \
      --command-id "$COMMAND_ID" \
      --query 'Commands[0].Status' \
      --output text
  )"

  case "$COMMAND_STATUS" in
    Success)
      aws ssm list-command-invocations \
        --region "$AWS_DEPLOY_REGION" \
        --command-id "$COMMAND_ID" \
        --details \
        --query 'CommandInvocations[].{InstanceId:InstanceId,Status:Status}' \
        --output table
      exit 0
      ;;
    Failed|Cancelled|TimedOut|Cancelling)
      aws ssm list-command-invocations \
        --region "$AWS_DEPLOY_REGION" \
        --command-id "$COMMAND_ID" \
        --details \
        --query 'CommandInvocations[].{InstanceId:InstanceId,Status:Status,Output:CommandPlugins[0].Output}' \
        --output table
      exit 1
      ;;
    Pending|InProgress|Delayed)
      sleep 10
      ;;
    *)
      echo "Unexpected SSM command status: $COMMAND_STATUS" >&2
      exit 1
      ;;
  esac
done
