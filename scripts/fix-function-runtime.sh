#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
FUNCTION_APP="mediaprocessor"

echo "Fixing Azure Functions runtime configuration..."

# Remove container configuration to switch back to Python runtime
echo "Removing container configuration..."
az functionapp config container delete \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP"

# Set the correct Python runtime
echo "Setting Python runtime..."
az functionapp config set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --linux-fx-version "Python|3.11"

# Restart the function app
echo "Restarting function app..."
az functionapp restart \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP"

echo "Runtime configuration fixed!"
echo "The function app should now use Python runtime instead of Docker."
echo ""
echo "You can monitor the function app logs with:"
echo "az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
