#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
REGISTRY_NAME="mediacompressorregistry"
APP_SERVICE_PLAN="mediaprocessor-b2-plan"
WEB_APP="mediaprocessor-b2"
IMAGE_NAME="mediaprocessor2"

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
echo "🚀 App Service B2 Deployment"
echo "==============================================="
echo "Image tag: $IMAGE_TAG"
echo "Commit SHA: $COMMIT_SHA"
echo "Target: $WEB_APP"
echo "==============================================="
echo ""

# Get registry login server
REGISTRY_LOGIN_SERVER=$(az acr show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer \
  --output tsv)

echo "Registry login server: $REGISTRY_LOGIN_SERVER"

# Build the image in Azure Container Registry
echo "📦 Building container image in Azure..."
az acr build \
  --registry "$REGISTRY_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  --file Dockerfile \
  .

echo "✅ Image built successfully!"
echo ""

# Get the IMAGE DIGEST for digest pinning
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

# Check if App Service Plan exists, create if not
echo "🔍 Checking App Service Plan..."
if ! az appservice plan show --name "$APP_SERVICE_PLAN" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "📝 Creating App Service Plan B2..."
    az appservice plan create \
      --name "$APP_SERVICE_PLAN" \
      --resource-group "$RESOURCE_GROUP" \
      --is-linux \
      --sku B2 \
      --location germanywestcentral
    echo "✅ App Service Plan created"
else
    echo "✅ App Service Plan exists"
fi
echo ""

# Check if Web App exists, create if not
echo "🔍 Checking Web App..."
if ! az webapp show --name "$WEB_APP" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "📝 Creating Web App..."
    az webapp create \
      --name "$WEB_APP" \
      --resource-group "$RESOURCE_GROUP" \
      --plan "$APP_SERVICE_PLAN" \
      --deployment-container-image-name "$IMAGE_WITH_DIGEST"
    echo "✅ Web App created"
else
    echo "✅ Web App exists"
fi
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

echo "🔧 Configuring Web App..."
echo "   Using DIGEST pinning (not tag)"
echo ""

# Configure container settings
az webapp config container set \
  --name "$WEB_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --docker-custom-image-name "$IMAGE_WITH_DIGEST" \
  --docker-registry-server-url "https://$REGISTRY_LOGIN_SERVER" \
  --docker-registry-server-user "$REGISTRY_USERNAME" \
  --docker-registry-server-password "$REGISTRY_PASSWORD"

# Configure app settings
echo "📝 Setting environment variables..."
az webapp config appsettings set \
  --name "$WEB_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    "COMMIT_SHA=$COMMIT_SHA" \
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE=false" \
    "WEBSITES_PORT=80" \
  --output none

echo "✅ Configuration updated"
echo ""

# CRITICAL: Use STOP/START for proper deployment
echo "⏸️  STOPPING web app (forces container refresh)..."
az webapp stop \
  --name "$WEB_APP" \
  --resource-group "$RESOURCE_GROUP"

echo "⏳ Waiting 10 seconds for full shutdown..."
sleep 10

echo "▶️  STARTING web app..."
az webapp start \
  --name "$WEB_APP" \
  --resource-group "$RESOURCE_GROUP"

echo ""
echo "==============================================="
echo "✅ Deployment Complete!"
echo "==============================================="
echo "Image tag:    $IMAGE_TAG"
echo "Image digest: $IMAGE_DIGEST"
echo "Commit SHA:   $COMMIT_SHA"
echo ""

# Wait for startup
echo "⏳ Waiting 30 seconds for container startup..."
sleep 30
echo ""

# Verify deployment
PROD_URL="https://${WEB_APP}.azurewebsites.net"

echo "🔍 Verifying deployment..."
echo ""

for i in {1..3}; do
    echo "Request $i:"
    VERSION_RESPONSE=$(curl -sf "$PROD_URL/api/version" 2>/dev/null || echo '{"error":"timeout"}')
    WORKER_VERSION=$(echo "$VERSION_RESPONSE" | jq -r '.version // "unknown"')

    echo "  Version:  $WORKER_VERSION"
    sleep 2
done

echo ""
if [ "$WORKER_VERSION" = "$COMMIT_SHA" ]; then
    echo "✅ Deployment verified: $COMMIT_SHA"
else
    echo "⚠️  Version mismatch. Expected: $COMMIT_SHA, Got: $WORKER_VERSION"
fi

echo ""
echo "📊 Deployment Summary:"
echo "  Production URL: $PROD_URL"
echo "  Health:         $PROD_URL/api/health"
echo "  Version:        $PROD_URL/api/version"
echo "  Process:        $PROD_URL/api/process"
echo "  Status:         $PROD_URL/api/status"
echo ""
echo "💰 Cost: ~$55/month (App Service B2)"
echo "⚡ Performance: 2 cores, 3.5GB RAM"
echo "📈 Capacity: 2-3 concurrent uploads"
echo ""
