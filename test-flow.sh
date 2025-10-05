#!/bin/bash
set -e

# Configuration
API_KEY="c94f3b36eda2333960602f81be1709c918327d758d19033afe7a7c3375b9bceb"
STORAGE_ACCOUNT="mediablobazfct"
FUNCTION_URL="https://mediaprocessor-b2.azurewebsites.net/api"  # App Service B2 (current)
# FUNCTION_URL="https://mediaprocessor2.azurewebsites.net/api"  # Functions EP1 (legacy)
RESOURCE_GROUP="rg-11-video-compressor-az-function"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Media Compression Flow Test ===${NC}\n"

# Step 1: Check if test file exists
if [ ! -f "media-uploader/test.png" ]; then
    echo -e "${RED}Error: test.png not found in media-uploader directory${NC}"
    exit 1
fi

# Step 2: Generate unique blob name
TIMESTAMP=$(date +%s)
BLOB_NAME="upload-${TIMESTAMP}.png"

echo -e "${BLUE}Step 1: Uploading test file${NC}"
echo "Blob name: ${BLOB_NAME}"

az storage blob upload \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name uploads \
  --file media-uploader/test.png \
  --name "$BLOB_NAME" \
  --auth-mode key \
  --output none 2>&1 | grep -v "WARNING" || true

echo -e "${GREEN}✓ Upload complete${NC}\n"

# Step 2: Trigger processing via API
echo -e "${BLUE}Step 2: Calling /api/process${NC}"
PROCESS_RESPONSE=$(curl -s -X POST "${FUNCTION_URL}/process" \
  -H "Content-Type: application/json" \
  -d "{\"blob_name\": \"${BLOB_NAME}\"}")

PROCESS_STATUS=$(echo "$PROCESS_RESPONSE" | jq -r '.status // "error"')

if [ "$PROCESS_STATUS" = "success" ]; then
    echo -e "${GREEN}✓ Processing completed immediately!${NC}\n"
    echo -e "${BLUE}Result:${NC}"
    echo "$PROCESS_RESPONSE" | jq .

    COMPRESSION_RATIO=$(echo "$PROCESS_RESPONSE" | jq -r '.result.compression_ratio')
    PROCESSING_TIME=$(echo "$PROCESS_RESPONSE" | jq -r '.result.processing_time')
    OUTPUT_URL=$(echo "$PROCESS_RESPONSE" | jq -r '.result.output_url')

    echo -e "\n${GREEN}=== Results ===${NC}"
    echo "Compression Ratio: ${COMPRESSION_RATIO}"
    echo "Processing Time: ${PROCESSING_TIME}s"
    echo -e "Download URL: ${BLUE}${OUTPUT_URL}${NC}"
    exit 0
fi

# If not immediate success, poll status
echo -e "${YELLOW}Processing not immediate, polling status...${NC}\n"
echo -e "${BLUE}Step 3: Checking processing status${NC}\n"

check_status() {
    curl -s -H "X-API-Key: $API_KEY" \
        "${FUNCTION_URL}/status?blob_name=${BLOB_NAME}"
}

# Poll for status up to 30 seconds
MAX_ATTEMPTS=15
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))

    echo -e "${YELLOW}Attempt ${ATTEMPT}/${MAX_ATTEMPTS}...${NC}"

    RESPONSE=$(check_status)
    STATUS=$(echo "$RESPONSE" | jq -r '.status // "error"')

    if [ "$STATUS" = "error" ]; then
        echo -e "${RED}Error response:${NC}"
        echo "$RESPONSE" | jq .
        break
    fi

    echo "Status: $STATUS"

    if [ "$STATUS" = "completed" ]; then
        echo -e "\n${GREEN}✓ Processing completed!${NC}\n"
        echo -e "${BLUE}Full Response:${NC}"
        echo "$RESPONSE" | jq .

        # Extract and display key metrics
        COMPRESSION_RATIO=$(echo "$RESPONSE" | jq -r '.compression_ratio')
        PROCESSING_TIME=$(echo "$RESPONSE" | jq -r '.processing_time')
        OUTPUT_URL=$(echo "$RESPONSE" | jq -r '.output_url')

        echo -e "\n${GREEN}=== Results ===${NC}"
        echo "Compression Ratio: ${COMPRESSION_RATIO}"
        echo "Processing Time: ${PROCESSING_TIME}s"
        echo -e "Download URL: ${BLUE}${OUTPUT_URL}${NC}"

        exit 0
    elif [ "$STATUS" = "failed" ]; then
        echo -e "\n${RED}✗ Processing failed!${NC}\n"
        echo "$RESPONSE" | jq .
        exit 1
    fi

    # Wait before next check
    sleep 2
done

echo -e "\n${RED}✗ Timeout: Processing did not complete in time${NC}"
echo "Last status: $STATUS"
echo "You can check manually with:"
echo "curl -H \"X-API-Key: $API_KEY\" \"${FUNCTION_URL}/status?blob_name=${BLOB_NAME}\""
exit 1
