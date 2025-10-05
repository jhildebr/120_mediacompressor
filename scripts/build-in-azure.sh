#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
REGISTRY_NAME="mediacompressorregistry"
FUNCTION_APP="mediaprocessor2"
IMAGE_NAME="mediaprocessor2"
USE_SLOT="${USE_SLOT:-false}"  # Set to "true" to deploy to staging slot
SLOT_NAME="staging"

# CRITICAL: Use IMMUTABLE TAG for build tracking
if git rev-parse --short HEAD &>/dev/null; then
    GIT_SHA=$(git rev-parse --short HEAD)
    IMAGE_TAG="${GIT_SHA}-$(date +%s)"
    COMMIT_SHA="$GIT_SHA"
else
    IMAGE_TAG="build-$(date +%s)"
    COMMIT_SHA="unknown"
fi

echo "==============================================="
echo "🚀 EP1 Premium Functions Deployment"
echo "==============================================="
echo "Image tag: $IMAGE_TAG"
echo "Commit SHA: $COMMIT_SHA"
echo "Target: $FUNCTION_APP"
if [ "$USE_SLOT" = "true" ]; then
    echo "Slot: $SLOT_NAME (will swap to production)"
fi
echo "==============================================="
echo ""

# Get registry login server
REGISTRY_LOGIN_SERVER=$(az acr show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer \
  --output tsv)

echo "Registry login server: $REGISTRY_LOGIN_SERVER"

# Build the image in Azure Container Registry with COMMIT_SHA build arg
echo "📦 Building container image in Azure..."
az acr build \
  --registry "$REGISTRY_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  --file Dockerfile \
  .

echo "✅ Image built successfully!"
echo ""

# CRITICAL: Get the IMAGE DIGEST for digest pinning
echo "🔍 Getting image digest for pinning..."
IMAGE_DIGEST=$(az acr repository show \
  --name "$REGISTRY_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  --query "digest" \
  --output tsv)

IMAGE_WITH_DIGEST="${REGISTRY_LOGIN_SERVER}/${IMAGE_NAME}@${IMAGE_DIGEST}"

echo "✅ Image digest: $IMAGE_DIGEST"
echo "📌 Full image reference: $IMAGE_WITH_DIGEST"
echo ""

# Get registry credentials
REGISTRY_USERNAME=$(az acr credential show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query username \
  --output tsv)

REGISTRY_PASSWORD=$(az acr credential show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query passwords[0].value \
  --output tsv)

# Determine deployment target (production or slot)
if [ "$USE_SLOT" = "true" ]; then
    DEPLOY_TARGET="--slot $SLOT_NAME"
    TARGET_NAME="$FUNCTION_APP (slot: $SLOT_NAME)"
else
    DEPLOY_TARGET=""
    TARGET_NAME="$FUNCTION_APP (production)"
fi

echo "🔧 Configuring function app: $TARGET_NAME"
echo "   Using DIGEST pinning (not tag)"
echo ""

# CRITICAL: Use DIGEST not TAG for deployment
# This ensures every worker gets the exact same artifact
az functionapp config container set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  $DEPLOY_TARGET \
  --image "$IMAGE_WITH_DIGEST" \
  --registry-server "$REGISTRY_LOGIN_SERVER" \
  --registry-username "$REGISTRY_USERNAME" \
  --registry-password "$REGISTRY_PASSWORD"

# Set COMMIT_SHA as app setting for version verification
echo "📝 Setting COMMIT_SHA environment variable..."
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  $DEPLOY_TARGET \
  --settings "COMMIT_SHA=$COMMIT_SHA" \
  --output none

echo "✅ Configuration updated"
echo ""

# CRITICAL: Use STOP/START not RESTART for EP1
# This forces all pre-warmed workers to fully recycle
if [ "$USE_SLOT" = "true" ]; then
    echo "🔄 Restarting slot: $SLOT_NAME"
    az functionapp restart \
      --name "$FUNCTION_APP" \
      --resource-group "$RESOURCE_GROUP" \
      --slot "$SLOT_NAME"
else
    echo "⏸️  STOPPING function app (deallocates ALL workers)..."
    az functionapp stop \
      --name "$FUNCTION_APP" \
      --resource-group "$RESOURCE_GROUP"

    echo "⏳ Waiting 15 seconds for full deallocation..."
    sleep 15

    echo "▶️  STARTING function app (forces fresh pull)..."
    az functionapp start \
      --name "$FUNCTION_APP" \
      --resource-group "$RESOURCE_GROUP"
fi

# Slot swap if deploying to staging
if [ "$USE_SLOT" = "true" ]; then
    echo ""
    echo "🔄 Warming up staging slot..."
    sleep 20

    echo "🔍 Verifying staging slot..."
    SLOT_URL="https://${FUNCTION_APP}-${SLOT_NAME}.azurewebsites.net"
    if curl -sf "$SLOT_URL/api/version" | jq .; then
        echo ""
        echo "✅ Staging slot is healthy!"
        echo ""
        read -p "🔄 Swap staging to production? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🔄 Swapping slots..."
            az functionapp deployment slot swap \
              --name "$FUNCTION_APP" \
              --resource-group "$RESOURCE_GROUP" \
              --slot "$SLOT_NAME" \
              --target-slot production
            echo "✅ Slot swap complete!"
        else
            echo "⏭️  Skipped slot swap. Staging is ready for manual testing."
        fi
    else
        echo "⚠️  Staging slot not responding - check logs before swapping"
    fi
fi

echo ""
echo "==============================================="
echo "✅ Deployment Complete!"
echo "==============================================="
echo "Image tag:    $IMAGE_TAG"
echo "Image digest: $IMAGE_DIGEST"
echo "Commit SHA:   $COMMIT_SHA"
echo ""

# Wait for EP1 cold start (can take 30-60s)
echo "⏳ Waiting 40 seconds for EP1 cold start and worker initialization..."
sleep 40
echo ""

# Verify version across all workers
echo "🔍 Verifying deployment across all EP1 workers..."
echo "   Calling /api/version multiple times to hit different instances..."
echo ""

PROD_URL="https://${FUNCTION_APP}.azurewebsites.net"
VERSIONS_SEEN=()

for i in {1..5}; do
    echo "Request $i:"
    VERSION_RESPONSE=$(curl -sf "$PROD_URL/api/version" 2>/dev/null || echo '{"error":"timeout"}')
    WORKER_VERSION=$(echo "$VERSION_RESPONSE" | jq -r '.version // "unknown"')
    WORKER_INSTANCE=$(echo "$VERSION_RESPONSE" | jq -r '.instance // "unknown"')

    echo "  Instance: $WORKER_INSTANCE"
    echo "  Version:  $WORKER_VERSION"

    if [[ ! " ${VERSIONS_SEEN[@]} " =~ " ${WORKER_VERSION} " ]]; then
        VERSIONS_SEEN+=("$WORKER_VERSION")
    fi

    sleep 2
done

echo ""
if [ ${#VERSIONS_SEEN[@]} -eq 1 ] && [ "${VERSIONS_SEEN[0]}" = "$COMMIT_SHA" ]; then
    echo "✅ All workers running version: $COMMIT_SHA"
else
    echo "⚠️  Multiple versions detected: ${VERSIONS_SEEN[*]}"
    echo "   Expected: $COMMIT_SHA"
    echo "   Wait 60s and try again, or check logs"
fi

echo ""
echo "📊 Deployment Summary:"
echo "  Production URL: $PROD_URL"
echo "  Health:         $PROD_URL/api/health"
echo "  Version:        $PROD_URL/api/version"
echo ""
echo "📝 Monitor logs:"
echo "  az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
echo ""
echo "🐳 Docker logs:"
echo "  https://${FUNCTION_APP}.scm.azurewebsites.net/api/logs/docker"
echo ""
