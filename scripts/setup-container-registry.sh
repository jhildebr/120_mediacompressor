#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
LOCATION="germanywestcentral"
REGISTRY_NAME="mediacompressorregistry"
FUNCTION_APP="mediaprocessor"

echo "Setting up Azure Container Registry for media compression function..."

# Create Azure Container Registry
echo "Creating Azure Container Registry: $REGISTRY_NAME"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REGISTRY_NAME" \
  --sku Basic \
  --admin-enabled true

# Get registry login server
REGISTRY_LOGIN_SERVER=$(az acr show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer \
  --output tsv)

echo "Registry login server: $REGISTRY_LOGIN_SERVER"

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

echo "Registry username: $REGISTRY_USERNAME"
echo "Registry password: $REGISTRY_PASSWORD"

# Configure function app to use the registry
echo "Configuring function app to use container registry..."
az functionapp config container set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$REGISTRY_LOGIN_SERVER/mediaprocessor:latest" \
  --registry-server "$REGISTRY_LOGIN_SERVER" \
  --registry-username "$REGISTRY_USERNAME" \
  --registry-password "$REGISTRY_PASSWORD"

echo "Container registry setup complete!"
echo ""
echo "Registry details saved. Next steps:"
echo "1. Build and push the container image:"
echo "   ./scripts/build-and-deploy.sh"
echo ""
echo "2. The function app will be configured automatically during deployment."
echo ""
echo "3. Set environment variables:"
echo "   ./scripts/set-env-vars.sh"
