# SIMPI Azure Media Compression System

Azure Function App (container-based) for video and image compression using FFmpeg and Pillow.

**Note**: This is a **Function App running a container** (not Azure Container Apps service).

## Architecture

- **Azure Function App**: Container-based Function App running Python 3.11 with FFmpeg
- **Azure Blob Storage**: File uploads and processed outputs
- **Azure Queue Storage**: Job processing queue
- **Azure Container Registry**: Container image storage

## Quick Start

### 1. Build and Deploy Container (in Azure)
```bash
./scripts/build-in-azure.sh
```

This builds the container in Azure Container Registry (no local Docker required) and deploys to the Function App.

### 2. Generate and Set API Key
```bash
# Generate a secure API key
openssl rand -hex 32

# Set it in Function App
az functionapp config appsettings set \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function \
  --settings "API_KEY=your-generated-api-key"
```

### 3. Verify Deployment
```bash
curl https://mediaprocessor2.azurewebsites.net/api/health
```

**📖 For complete deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

## File Structure

```
├── Dockerfile                    # Container with Python + FFmpeg
├── .dockerignore                 # Docker ignore patterns
├── function_app.py              # Azure Functions entry point
├── processing/                  # Media processing modules
│   ├── video.py                # FFmpeg video compression
│   └── image.py                # Pillow image compression
├── integrations/                # External service integrations
│   ├── database.py             # SIMPI API database updates
│   ├── notifications.py        # Real-time notifications
│   └── errors.py               # Error handling and retries
├── config/                     # Configuration files
│   └── compression_config.py   # Compression settings
├── scripts/                    # Deployment scripts
│   ├── setup-container-registry.sh
│   ├── build-in-azure.sh      # Build & deploy (no Docker required)
│   └── set-env-vars.sh
└── requirements.txt            # Python dependencies
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SIMPI_API_BASE_URL` | SIMPI API base URL | `https://api.simpi.com` |
| `SIMPI_API_TOKEN` | API authentication token | `your-service-token` |
| `WEBHOOK_URL` | Webhook for notifications | `https://api.simpi.com/webhooks/media-processing` |
| `MAX_PROCESSING_TIME` | Max processing time (seconds) | `300` |
| `MAX_RETRY_ATTEMPTS` | Max retry attempts | `3` |
| `BLOB_ACCOUNT_NAME` | Storage account name | `mediablobazfct` |

## Local Development

### Prerequisites
- Docker
- Azure CLI
- Python 3.11

### Test Processing Without Queue

Upload a test file and trigger processing directly (bypasses queue):

```bash
# Upload a test file to the uploads container
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file test-video.mp4 \
  --name "test-video.mp4"

# Trigger processing directly (bypasses queue)
curl -X POST https://mediaprocessor2.azurewebsites.net/api/test-process \
  -H "Content-Type: application/json" \
  -d '{"blob_name": "test-video.mp4"}'
```

## Monitoring

### View Logs
```bash
az functionapp logs tail \
  --name mediaprocessor2 \
  --resource-group rg-11-video-compressor-az-function
```

### Health Check
```bash
curl https://mediaprocessor2.azurewebsites.net/api/health
```

### Check Queue Status
```bash
az storage queue show \
  --name media-processing-queue \
  --account-name mediablobazfct \
  --query "approximateMessageCount"
```

## Features

### Production-Ready Multi-Tenant Processing
- ✅ **Job Tracking**: Azure Table Storage tracks all processing jobs
- ✅ **API Authentication**: Secure API key authentication
- ✅ **Status Queries**: Query processing status by blob name
- ✅ **Automatic Cleanup**:
  - Upload blobs deleted immediately after processing
  - Processed blobs deleted 10 minutes after completion
- ✅ **Parallel Processing**: Multiple jobs processed simultaneously without conflicts
- ✅ **Error Tracking**: Failed jobs tracked with error messages

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | No | Health check and function list |
| `/api/status` | GET | **Yes** | Get processing status (query: `?blob_name=file.mp4`) |
| `/api/test-process` | POST | No | Test processing without queue (JSON: `{"blob_name": "file.mp4"}`) |

**Authentication**: Include `X-API-Key: your-api-key` header for authenticated endpoints.

## Troubleshooting

### Function App Issues
- Check logs in Azure Portal or via `az functionapp logs tail`
- Verify container image is deployed: `az functionapp config container show`
- Check environment variables in Azure Portal

### Storage Issues
- Verify blob containers exist (`uploads`, `processed`)
- Check queue permissions
- Validate connection strings

### Processing Issues
- Check file format support
- Use `/api/test-process` endpoint to bypass queue for testing
- Monitor memory usage for large files in Azure Portal