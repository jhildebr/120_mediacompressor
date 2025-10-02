#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="rg-11-video-compressor-az-function"
LOCATION="westeurope"
STORAGE_ACCOUNT="mediablobazfct"
FUNCTION_APP="mediaprocessor"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group "$RESOURCE_GROUP" \
  --name "$STORAGE_ACCOUNT" \
  --query connectionString --output tsv)

az storage container create --name uploads --connection-string "$STORAGE_CONNECTION"
az storage container create --name processed --connection-string "$STORAGE_CONNECTION" --public-access blob
az storage queue create --name media-processing-queue --connection-string "$STORAGE_CONNECTION"
az storage queue create --name media-processing-poison-queue --connection-string "$STORAGE_CONNECTION"

az functionapp create \
  --resource-group "$RESOURCE_GROUP" \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name "$FUNCTION_APP" \
  --storage-account "$STORAGE_ACCOUNT"

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

echo "Infrastructure setup complete!"


