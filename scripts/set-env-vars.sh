#!/usr/bin/env bash
set -euo pipefail

# Configuration
RESOURCE_GROUP="rg-11-video-compressor-az-function"
FUNCTION_APP="mediaprocessor"

echo "Setting environment variables for media processor function app..."

# Set all required environment variables
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    "SIMPI_API_BASE_URL=https://api.simpi.com" \
    "SIMPI_API_TOKEN=your-service-token" \
    "WEBHOOK_URL=https://api.simpi.com/webhooks/media-processing" \
    "MAX_PROCESSING_TIME=300" \
    "MAX_RETRY_ATTEMPTS=3" \
    "BLOB_ACCOUNT_NAME=mediablobazfct"

echo "Environment variables set successfully!"
echo ""
echo "IMPORTANT: Update the following variables with your actual values:"
echo "- SIMPI_API_TOKEN: Replace 'your-service-token' with your actual token"
echo "- SIMPI_API_BASE_URL: Update if your API URL is different"
echo "- WEBHOOK_URL: Update if your webhook URL is different"
echo ""
echo "You can update them individually with:"
echo "az functionapp config appsettings set --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --settings \"SIMPI_API_TOKEN=your-actual-token\""
