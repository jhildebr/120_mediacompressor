# Deployment Guide - Production-Ready Setup

## Overview

This guide covers deploying the enhanced media compression system with:
- ✅ Azure Table Storage job tracking
- ✅ API key authentication
- ✅ Automatic file cleanup (uploads deleted after processing, processed files deleted after 10 minutes)
- ✅ Enhanced status endpoint
- ✅ Multi-tenant parallel processing support

## Prerequisites

1. Azure CLI installed and authenticated
2. Azure subscription with appropriate permissions
3. Existing resources:
   - Resource Group: `rg-11-video-compressor-az-function`
   - Storage Account: `mediablobazfct`
   - Function App: `mediaprocessor2`
   - Container Registry: `mediacompressorregistry`

## Step 1: Generate API Key

Generate a secure API key for authentication:

```bash
# Generate a 32-character random hex string
openssl rand -hex 32
```

Save this key securely - you'll need it for configuration.

## Step 2: Configure Environment Variables

Set the required environment variables in your Function App:

```bash
# Set API key (use the key you generated above)
az functionapp config appsettings set \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function \
  --settings "API_KEY=your-generated-api-key-here"

# Verify all required settings are present
az functionapp config appsettings list \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function \
  --query "[].{name:name, value:value}" \
  --output table
```

Required environment variables:
- `AzureWebJobsStorage` - Already configured
- `API_KEY` - Your generated API key
- `BLOB_ACCOUNT_NAME` - Already configured (mediablobazfct)

Optional environment variables:
- `SIMPI_API_BASE_URL` - SIMPI API endpoint
- `SIMPI_API_TOKEN` - SIMPI API token
- `MAX_PROCESSING_TIME` - Max processing time in seconds (default: 300)
- `MAX_RETRY_ATTEMPTS` - Max retry attempts (default: 3)

## Step 3: Deploy Updated Function App

Deploy the updated code with all new features:

```bash
# Build and deploy in Azure
./scripts/build-in-azure.sh
```

This will:
1. Build the container in Azure Container Registry
2. Update the Function App with the new image
3. Restart the Function App

## Step 4: Verify Deployment

Check that all functions are running:

```bash
# Health check (no auth required)
curl https://mediaprocessor2.azurewebsites.net/api/health

# Expected response:
{
  "status": "ok",
  "functions": ["process_media_upload", "process_media_queue", "test_process", "cleanup_old_files"]
}
```

## Step 5: Test Authentication

Test the authenticated status endpoint:

```bash
# Without API key (should fail with 401)
curl https://mediaprocessor2.azurewebsites.net/api/status?blob_name=test.mp4

# With API key (should work)
curl -H "X-API-Key: your-api-key-here" \
  https://mediaprocessor2.azurewebsites.net/api/status?blob_name=test.mp4
```

## Step 6: Test Complete Flow

1. **Upload a file** (via your application):

```bash
# Upload to blob storage
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file test.mp4 \
  --name "upload-$(date +%s).mp4"
```

2. **Check status** (with API key):

```bash
# Replace with your actual blob name
curl -H "X-API-Key: your-api-key-here" \
  https://mediaprocessor2.azurewebsites.net/api/status?blob_name=upload-1234567890.mp4

# Status will be:
# - "queued" - File uploaded, waiting for processing
# - "processing" - Currently being processed
# - "completed" - Processing finished, download URL available
# - "failed" - Processing failed, error message available
```

3. **Download processed file** (from status response):

```bash
# The status endpoint returns output_url when completed
# Use that URL to download the processed file
curl -o processed.mp4 "https://mediablobazfct.blob.core.windows.net/processed/processed-1234567890.mp4?<sas-token>"
```

4. **Wait for cleanup**:
   - Upload blob is deleted immediately after successful processing
   - Processed blob is deleted 10 minutes after completion
   - Job tracking record is deleted with the processed blob

## Architecture Flow

```
1. Upload File
   └─> Blob Storage (uploads container)
       └─> Blob Trigger
           └─> Create Job Record (Table Storage)
           └─> Queue Message

2. Process File
   └─> Queue Trigger
       └─> Update Status: "processing"
       └─> Process with FFmpeg/Pillow
       └─> Upload to Blob Storage (processed container)
       └─> Update Status: "completed"
       └─> Delete Upload Blob (immediate cleanup)

3. Status Check (with API key)
   └─> Query Table Storage
       └─> Return status + download URL (if completed)

4. Cleanup (every 5 minutes)
   └─> Find completed jobs > 10 minutes old
       └─> Delete Processed Blob
       └─> Delete Job Record
```

## API Endpoints

### Health Check (No Auth)
```
GET /api/health
```

### Status Check (Auth Required)
```
GET /api/status?blob_name={blob_name}
Headers: X-API-Key: {your-api-key}

Response:
{
  "blob_name": "upload-1234567890.mp4",
  "status": "completed",
  "file_size": 10485760,
  "file_type": "mp4",
  "created_at": "2025-10-04T08:00:00Z",
  "processing_started_at": "2025-10-04T08:00:05Z",
  "completed_at": "2025-10-04T08:00:20Z",
  "processed_blob_name": "processed-1234567890.mp4",
  "original_size": 10485760,
  "compressed_size": 5242880,
  "compression_ratio": 0.5,
  "processing_time": 15.2,
  "output_url": "https://mediablobazfct.blob.core.windows.net/processed/..."
}
```

### Test Process (No Auth, for testing only)
```
POST /api/test-process
Content-Type: application/json

{
  "blob_name": "upload-1234567890.mp4"
}
```

## Monitoring

### View Logs
```bash
az functionapp logs tail \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function
```

### Check Table Storage
```bash
# List processing jobs
az storage entity query \
  --account-name mediablobazfct \
  --table-name processingjobs
```

### Monitor Cleanup Timer
Look for cleanup logs every 5 minutes:
```
=== CLEANUP TIMER STARTED ===
Found X old completed jobs to clean up
Deleted processed blob: processed-xxx.mp4
=== CLEANUP COMPLETED: X jobs cleaned, 0 errors ===
```

## File Retention Policy

| File Type | Location | Retention |
|-----------|----------|-----------|
| **Upload** | `uploads` container | Deleted immediately after successful processing |
| **Processed** | `processed` container | Deleted 10 minutes after completion |
| **Job Record** | Table Storage | Deleted with processed file (10 minutes) |

## Security Best Practices

1. **API Key Storage**:
   - Never commit API keys to git
   - Use Azure Key Vault for production
   - Rotate keys regularly

2. **API Key Usage**:
   ```bash
   # Option 1: X-API-Key header
   curl -H "X-API-Key: your-key" ...

   # Option 2: Authorization Bearer
   curl -H "Authorization: Bearer your-key" ...
   ```

3. **Network Security**:
   - Consider adding IP restrictions in Azure
   - Use VNet integration for production
   - Enable HTTPS only (already enforced)

## Troubleshooting

### Issue: Status endpoint returns 401
**Solution**: Ensure API_KEY is set and you're sending the correct header

### Issue: Files not being cleaned up
**Solution**:
- Check cleanup timer logs
- Verify timer trigger is running (every 5 minutes)
- Check Azure Portal > Function App > Functions > cleanup_old_files

### Issue: Job record not found
**Solution**:
- Verify blob name is correct
- Check if job was created (look for CREATE_JOB logs)
- Verify Table Storage is accessible

### Issue: Upload blob not deleted after processing
**Solution**:
- Check processing logs for delete errors
- Verify Function App has write permissions to uploads container

## Next Steps

1. **Integrate with your application (app.simpi.com)**:
   - Store the API key securely in your app
   - Upload files to the uploads container
   - Poll the status endpoint to check progress
   - Download from output_url when status is "completed"

2. **Monitor in production**:
   - Set up Application Insights alerts
   - Monitor cleanup timer execution
   - Track processing success rates

3. **Optional enhancements**:
   - Add webhooks for completion notifications
   - Implement rate limiting
   - Add detailed analytics

## Cost Optimization

With the new cleanup policy:
- **Storage costs**: Minimal (files deleted after 10 min)
- **Table Storage**: Minimal (small records, auto-deleted)
- **Function executions**: Same as before + cleanup timer (every 5 min)

Estimated additional cost: **< $5/month**

## Support

For issues or questions:
1. Check logs: `az functionapp logs tail ...`
2. Check Table Storage for job records
3. Review this deployment guide
4. Check Azure Portal for Function App status
