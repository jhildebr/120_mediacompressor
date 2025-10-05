# Testing Guide

## Quick Test (Automated)

Run the automated test script:

```bash
./test-flow.sh
```

This will:
1. Upload a test file to blob storage
2. Wait for processing to complete
3. Display the results with compression metrics
4. Show the download URL

---

## Manual Testing

### 1. Upload a File

```bash
# Generate unique blob name
BLOB_NAME="upload-$(date +%s).png"

# Upload test file
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file media-uploader/test.png \
  --name "$BLOB_NAME" \
  --auth-mode login

echo "Uploaded: $BLOB_NAME"
```

### 2. Check Status (with API Key)

```bash
API_KEY="c94f3b36eda2333960602f81be1709c918327d758d19033afe7a7c3375b9bceb"

curl -H "X-API-Key: $API_KEY" \
  "https://mediaprocessor2.azurewebsites.net/api/status?blob_name=$BLOB_NAME" | jq
```

**Expected Statuses:**
- `queued` - File uploaded, waiting for processing
- `processing` - Currently being processed
- `completed` - Processing finished ✓
- `failed` - Processing failed ✗

### 3. Download Processed File

When status is `completed`, the response includes `output_url`:

```bash
# Extract download URL from status response
OUTPUT_URL=$(curl -s -H "X-API-Key: $API_KEY" \
  "https://mediaprocessor2.azurewebsites.net/api/status?blob_name=$BLOB_NAME" \
  | jq -r '.output_url')

# Download the processed file
curl -o processed.png "$OUTPUT_URL"
```

---

## Test Without Authentication (Public Endpoints)

### Health Check
```bash
curl https://mediaprocessor2.azurewebsites.net/api/health | jq
```

### Direct Test Processing (bypasses queue)
```bash
curl -X POST https://mediaprocessor2.azurewebsites.net/api/test-process \
  -H "Content-Type: application/json" \
  -d '{"blob_name": "upload-1234567890.mp4"}' | jq
```

---

## Verify Cleanup

### Check that upload blob is deleted after processing
```bash
# Should return 404 after processing completes
az storage blob show \
  --account-name mediablobazfct \
  --container-name uploads \
  --name "$BLOB_NAME" \
  --auth-mode login
```

### Check that processed blob exists
```bash
PROCESSED_NAME="${BLOB_NAME/upload-/processed-}"

az storage blob show \
  --account-name mediablobazfct \
  --container-name processed \
  --name "$PROCESSED_NAME" \
  --auth-mode login
```

### Wait 10 minutes, then verify cleanup
```bash
# After 10 minutes, processed blob should be deleted
az storage blob show \
  --account-name mediablobazfct \
  --container-name processed \
  --name "$PROCESSED_NAME" \
  --auth-mode login
# Should return: BlobNotFound
```

---

## Monitor Logs

### Watch function app logs in real-time
```bash
az functionapp logs tail \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function
```

### Look for specific events
```bash
# Job tracking
az functionapp logs tail ... | grep "job"

# Cleanup timer
az functionapp logs tail ... | grep "CLEANUP"

# Processing
az functionapp logs tail ... | grep "Processing"
```

---

## Check Table Storage

### View all jobs
```bash
az storage entity query \
  --account-name mediablobazfct \
  --table-name processingjobs \
  --auth-mode login
```

### Count jobs by status
```bash
# Queued jobs
az storage entity query \
  --account-name mediablobazfct \
  --table-name processingjobs \
  --filter "status eq 'queued'" \
  --auth-mode login

# Completed jobs
az storage entity query \
  --account-name mediablobazfct \
  --table-name processingjobs \
  --filter "status eq 'completed'" \
  --auth-mode login
```

---

## Test Parallel Processing

### Upload multiple files simultaneously
```bash
for i in {1..3}; do
  BLOB_NAME="upload-$(date +%s)-${i}.png"

  az storage blob upload \
    --account-name mediablobazfct \
    --container-name uploads \
    --file media-uploader/test.png \
    --name "$BLOB_NAME" \
    --auth-mode login &
done

wait
echo "All uploads complete"
```

### Check all job statuses
```bash
az storage entity query \
  --account-name mediablobazfct \
  --table-name processingjobs \
  --auth-mode login
```

---

## Troubleshooting

### Status endpoint returns 401
**Issue**: Missing or invalid API key

**Solution**:
```bash
# Verify API key is set
az functionapp config appsettings list \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function \
  --query "[?name=='API_KEY']"

# Set API key if missing
az functionapp config appsettings set \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function \
  --settings "API_KEY=c94f3b36eda2333960602f81be1709c918327d758d19033afe7a7c3375b9bceb"
```

### No job found for blob
**Issue**: Job record not created or blob trigger didn't fire

**Solutions**:
1. Check function app logs for errors
2. Verify blob trigger is enabled
3. Check that file was uploaded to `uploads` container
4. Wait a few seconds and try again

### Processing stuck in "queued" status
**Issue**: Queue trigger not processing messages

**Solutions**:
1. Check function app logs
2. Verify queue exists and has messages:
   ```bash
   az storage queue show \
     --name media-processing-queue \
     --account-name mediablobazfct
   ```
3. Restart function app:
   ```bash
   az functionapp restart \
     --name mediaprocessor2 \
     --resource-group rg-11-video-compressor-az-function
   ```

### Cleanup not working
**Issue**: Timer function not running or files not being deleted

**Solutions**:
1. Check timer logs: `az functionapp logs tail ... | grep CLEANUP`
2. Verify timer is enabled in Azure Portal
3. Check that jobs are older than 10 minutes
4. Manually trigger cleanup:
   ```bash
   # Find old jobs
   az storage entity query \
     --account-name mediablobazfct \
     --table-name processingjobs \
     --filter "status eq 'completed'" \
     --auth-mode login
   ```

---

## Expected Results

### Successful Image Processing
```json
{
  "blob_name": "upload-1234567890.png",
  "status": "completed",
  "file_size": 70,
  "file_type": "png",
  "created_at": "2025-10-04T22:45:00Z",
  "processing_started_at": "2025-10-04T22:45:05Z",
  "completed_at": "2025-10-04T22:45:08Z",
  "processed_blob_name": "processed-1234567890.png",
  "original_size": 70,
  "compressed_size": 35,
  "compression_ratio": 0.5,
  "processing_time": 3.2,
  "output_url": "https://mediablobazfct.blob.core.windows.net/processed/processed-1234567890.png?<sas-token>"
}
```

### Timeline
- **T+0s**: Upload file
- **T+1-3s**: Blob trigger creates job record (status: queued)
- **T+3-5s**: Queue trigger picks up job (status: processing)
- **T+5-15s**: Processing completes (status: completed)
- **T+15s**: Upload blob deleted
- **T+10min**: Processed blob + job record deleted

---

## Performance Benchmarks

### Image Processing (test.png, 70 bytes)
- Upload to completed: ~5-10 seconds
- Compression ratio: ~0.5 (50% reduction)

### Video Processing (small MP4)
- Upload to completed: ~15-30 seconds
- Compression ratio: varies by content

### Cleanup
- Timer runs: Every 5 minutes
- Cleanup latency: < 5 seconds per file
- Old job threshold: 10 minutes after completion
