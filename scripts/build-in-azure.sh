#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
REGISTRY_NAME="mediacompressorregistry"
FUNCTION_APP="mediaprocessor"
IMAGE_NAME="mediaprocessor"
IMAGE_TAG="latest"

echo "Building container image in Azure Container Registry..."

# Get registry login server
REGISTRY_LOGIN_SERVER=$(az acr show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer \
  --output tsv)

echo "Registry login server: $REGISTRY_LOGIN_SERVER"

# Build the image in Azure Container Registry
echo "Building container image in Azure..."
az acr build \
  --registry "$REGISTRY_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  --file Dockerfile \
  .

echo "Image built successfully in Azure Container Registry!"

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

# Configure function app to use the new image
echo "Configuring function app to use new container image..."
az functionapp config container set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$REGISTRY_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
  --registry-server "$REGISTRY_LOGIN_SERVER" \
  --registry-username "$REGISTRY_USERNAME" \
  --registry-password "$REGISTRY_PASSWORD"

# Restart the function app to pull the new image
echo "Restarting function app to use new image..."
az functionapp restart \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP"

echo "Deployment complete!"
echo "Container image: $REGISTRY_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
echo ""
echo "You can monitor the function app logs with:"
echo "az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
