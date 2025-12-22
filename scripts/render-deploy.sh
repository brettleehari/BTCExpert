#!/usr/bin/env bash
# Trigger a Render deployment using a pre-built Docker image.
#
# Usage:
#   RENDER_API_KEY=... RENDER_SERVICE_IDS="srv-123 srv-456" \
#   DOCKER_IMAGE_REPO="docker.io/brettleehari/cial" \
#   IMAGE_TAG=$(git rev-parse --short HEAD) \
#   ./scripts/render-deploy.sh
#
# Required environment variables:
#   RENDER_API_KEY      - Render API token with deploy access
#   RENDER_SERVICE_IDS  - Space separated list of Render service IDs
#                         (find under "Deploys" -> "Manual Deploy" in the Render UI)
# Optional environment variables:
#   DOCKER_IMAGE_REPO   - Fully qualified image repository (default: docker.io/brettleehari/cial)
#   IMAGE_TAG           - Image tag to deploy (default: latest)
#
# The script calls the Render Deploy API directly and instructs each service
# to pull the specified image from Docker Hub. No build occurs on Render's side.

set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed" >&2
  exit 1
fi

RENDER_API_KEY=${RENDER_API_KEY:-}
if [[ -z "$RENDER_API_KEY" ]]; then
  echo "RENDER_API_KEY environment variable is required" >&2
  exit 1
fi

RENDER_SERVICE_IDS=${RENDER_SERVICE_IDS:-${RENDER_SERVICE_ID:-}}
if [[ -z "$RENDER_SERVICE_IDS" ]]; then
  echo "Set RENDER_SERVICE_IDS (space separated IDs) or RENDER_SERVICE_ID" >&2
  exit 1
fi

DOCKER_IMAGE_REPO=${DOCKER_IMAGE_REPO:-docker.io/brettleehari/cial}
IMAGE_TAG=${IMAGE_TAG:-latest}
IMAGE_PATH="${DOCKER_IMAGE_REPO}:${IMAGE_TAG}"

echo "📦 Deploying image ${IMAGE_PATH} to Render services: ${RENDER_SERVICE_IDS}" >&2

for service_id in $RENDER_SERVICE_IDS; do
  payload=$(cat <<JSON
{
  "clearCache": false,
  "image": {
    "imagePath": "${IMAGE_PATH}"
  }
}
JSON
  )

  echo "🚀 Triggering deployment for service ${service_id}" >&2
  response=$(curl -fsS -X POST \
    -H "Authorization: Bearer ${RENDER_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    "https://api.render.com/v1/services/${service_id}/deploys")

  echo "✅ Render response for ${service_id}: ${response}" >&2
  echo
  sleep 1
done

echo "✨ All deployment requests submitted. Monitor progress in the Render dashboard." >&2
