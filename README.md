# SIMPI Azure Media Compression System

Container-based Azure Functions for video and image compression using FFmpeg and Pillow.

## Architecture

- **Azure Container Apps**: Runs Python 3.11 with FFmpeg
- **Azure Blob Storage**: File uploads and processed outputs
- **Azure Queue Storage**: Job processing queue
- **Azure Container Registry**: Container image storage

## Quick Start

### 1. Setup Container Registry
```bash
./scripts/setup-container-registry.sh
```

### 2. Build and Deploy Container
```bash
./scripts/build-and-deploy.sh
```

### 3. Set Environment Variables
```bash
./scripts/set-env-vars.sh
```

### 4. Update API Token
```bash
az functionapp config appsettings set \
  --name mediaprocessor \
  --resource-group rg-11-video-compressor-az-function \
  --settings "SIMPI_API_TOKEN=your-actual-token"
```

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
│   ├── build-and-deploy.sh
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

### Test Locally
```bash
# Build container
docker build -t mediaprocessor .

# Run locally
docker run -p 8080:80 \
  -e AzureWebJobsStorage="UseDevelopmentStorage=true" \
  -e BLOB_ACCOUNT_NAME="mediablobazfct" \
  mediaprocessor
```

### Test Processing
```bash
# Upload a test file to the uploads container
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file test-video.mp4 \
  --name "step-123-test.mp4"
```

## Monitoring

### View Logs
```bash
az functionapp logs tail \
  --name mediaprocessor \
  --resource-group rg-11-video-compressor-az-function
```

### Check Queue Status
```bash
az storage queue show \
  --name media-processing-queue \
  --account-name mediablobazfct \
  --query "approximateMessageCount"
```

## Troubleshooting

### Container Issues
- Check container logs in Azure Portal
- Verify FFmpeg installation: `docker exec <container> ffmpeg -version`
- Check Python dependencies: `docker exec <container> pip list`

### Storage Issues
- Verify blob containers exist
- Check queue permissions
- Validate connection strings

### Processing Issues
- Check file format support
- Verify FFmpeg command execution
- Monitor memory usage for large files