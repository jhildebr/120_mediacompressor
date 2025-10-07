#!/bin/bash
# Test script for /api/upload endpoint

set -e

ENDPOINT="https://mediaprocessor-b2.azurewebsites.net/api/upload"
TEST_FILE="${1:-media-uploader/test.png}"

if [ ! -f "$TEST_FILE" ]; then
    echo "❌ Test file not found: $TEST_FILE"
    echo "Usage: ./test-upload-endpoint.sh <path-to-file>"
    exit 1
fi

echo "📤 Testing /api/upload endpoint"
echo "File: $TEST_FILE"
echo "Endpoint: $ENDPOINT"
echo ""

# Get original file size
ORIGINAL_SIZE=$(stat -f%z "$TEST_FILE" 2>/dev/null || stat -c%s "$TEST_FILE" 2>/dev/null)
echo "Original size: $(numfmt --to=iec-i --suffix=B $ORIGINAL_SIZE 2>/dev/null || echo $ORIGINAL_SIZE bytes)"

# Upload and compress
echo ""
echo "⏳ Uploading and compressing..."
RESPONSE=$(curl -s -w "\n%{http_code}\n%{size_download}" -X POST \
  "$ENDPOINT" \
  -F "file=@$TEST_FILE" \
  -o /tmp/compressed-output.tmp)

HTTP_CODE=$(echo "$RESPONSE" | tail -n 2 | head -n 1)
DOWNLOAD_SIZE=$(echo "$RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success!"
    echo ""
    echo "📊 Results:"
    echo "  HTTP Status: $HTTP_CODE"
    echo "  Compressed size: $(numfmt --to=iec-i --suffix=B $DOWNLOAD_SIZE 2>/dev/null || echo $DOWNLOAD_SIZE bytes)"

    # Calculate savings
    if [ "$ORIGINAL_SIZE" -gt 0 ]; then
        SAVINGS=$((100 - (DOWNLOAD_SIZE * 100 / ORIGINAL_SIZE)))
        echo "  Size reduction: ${SAVINGS}%"
    fi

    echo ""
    echo "📁 Compressed file saved to: /tmp/compressed-output.tmp"

    # Try to get file type
    FILE_TYPE=$(file -b /tmp/compressed-output.tmp 2>/dev/null || echo "unknown")
    echo "  File type: $FILE_TYPE"

else
    echo "❌ Failed!"
    echo "  HTTP Status: $HTTP_CODE"
    echo "  Response:"
    cat /tmp/compressed-output.tmp
    exit 1
fi
