# Azure Media Compression System

**Production-ready media compression service on Azure App Service B2**

Compress images and videos efficiently using FFmpeg and Pillow, deployed as a containerized application on Azure.

**Current Status:** 🟢 **Phase 1 Complete** - Direct upload endpoint (`/api/upload`) deployed and tested
**Next Phase:** Phase 2 - Migrate to SIMPI resource group for unified storage

---

## 🎯 Overview

- **Platform:** Azure App Service B2 (2 cores, 3.5GB RAM)
- **Cost:** ~$55/month (down from $150-200 on Functions EP1)
- **Capacity:** 2-3 concurrent uploads
- **Processing:** Direct HTTP-based (no queuing delays)
- **Runtime:** Python 3.11 + FFmpeg in Docker container

## 🏗️ Architecture

```
┌─────────────────┐
│  Your Frontend  │
│  (app.simpi.com)│
└────────┬────────┘
         │ 1. Upload blob
         ↓
┌─────────────────┐
│ Azure Blob      │
│ Storage         │
│  - uploads/     │ ← Files uploaded here
│  - processed/   │ ← Compressed files here
└────────┬────────┘
         │ 2. Call /api/process
         ↓
┌─────────────────┐
│ App Service B2  │
│ mediaprocessor  │
│  - /api/process │ ← Process file
│  - /api/status  │ ← Check status
│  - /api/health  │ ← Health check
└────────┬────────┘
         │ 3. Return download URL
         ↓
┌─────────────────┐
│ Azure Table     │
│ Storage         │
│  processingjobs │ ← Job tracking
└─────────────────┘
```

**Key Flow:**
1. Upload file to Azure Blob Storage (`uploads` container)
2. Call `POST /api/process` with blob name
3. Receive compressed file download URL immediately
4. Optionally poll `GET /api/status` for job details

## 🚀 Quick Start

### Deploy to Azure

```bash
# Deploy App Service B2 (builds container in Azure, no local Docker needed)
./scripts/deploy-app-service-b2.sh

# Verify deployment
curl https://mediaprocessor-b2.azurewebsites.net/api/health
```

**Production URL:** `https://mediaprocessor-b2.azurewebsites.net`

### Test Processing

```bash
# 1. Upload a test file
az storage blob upload \
  --account-name mediablobazfct \
  --container-name uploads \
  --file test.png \
  --name "upload-test.png"

# 2. Trigger processing
curl -X POST https://mediaprocessor-b2.azurewebsites.net/api/process \
  -H 'Content-Type: application/json' \
  -d '{"blob_name": "upload-test.png"}'

# Response:
# {
#   "status": "success",
#   "result": {
#     "output_url": "https://...blob.core.windows.net/processed/processed-test.png?...",
#     "compression_ratio": 0.75,
#     "processing_time": 0.08
#   }
# }
```

## 📡 API Reference

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | No | Health check and uptime |
| `/api/version` | GET | No | Deployment version info |
| `/api/upload` | POST | No | **[Phase 1]** Direct file upload & compression |
| `/api/process` | POST | No | **[Phase 2]** Process blob from storage |
| `/api/status` | GET | **Yes** | Query job status by blob name |

### POST /api/process

Process a file that's been uploaded to blob storage.

**Request:**
```json
{
  "blob_name": "upload-123.png"
}
```

**Response:**
```json
{
  "status": "success",
  "blob_name": "upload-123.png",
  "result": {
    "status": "success",
    "original_size": 1048576,
    "compressed_size": 524288,
    "compression_ratio": 0.5,
    "processing_time": 0.234,
    "output_url": "https://mediablobazfct.blob.core.windows.net/processed/processed-123.png?se=...",
    "format": "PNG"
  }
}
```

### GET /api/status

Query processing status for a specific blob.

**Headers:**
```
X-API-Key: your-api-key
```

**Query Parameters:**
- `blob_name` (required): Name of the blob to check

**Response:**
```json
{
  "blob_name": "upload-123.png",
  "status": "completed",
  "file_size": 1048576,
  "file_type": "png",
  "created_at": "2025-10-05T12:00:00Z",
  "completed_at": "2025-10-05T12:00:01Z",
  "processing_time": 0.234,
  "output_url": "https://...",
  "compression_ratio": 0.5
}
```

**Status values:** `queued`, `processing`, `completed`, `failed`

## 🔧 Frontend Integration

### React/TypeScript Example

```typescript
async function uploadAndCompress(file: File) {
  // 1. Generate unique blob name
  const blobName = `upload-${Date.now()}.${file.name.split('.').pop()}`;

  // 2. Upload to Azure Blob Storage
  await uploadToBlobStorage(file, blobName);

  // 3. Trigger processing
  const response = await fetch('https://mediaprocessor-b2.azurewebsites.net/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blob_name: blobName }),
  });

  const { result } = await response.json();

  // 4. Download URL ready immediately!
  return result.output_url;
}
```

### JavaScript Example

```javascript
// Complete upload & compress flow
const timestamp = Date.now();
const blobName = `upload-${timestamp}.png`;

// Upload file (using Azure SDK or direct upload)
await uploadFile(file, blobName);

// Process file
const response = await fetch('/api/process', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ blob_name: blobName })
});

const data = await response.json();
console.log('Download:', data.result.output_url);
```

## 🗂️ Project Structure

```
├── function_app.py              # Main application (Azure Functions SDK)
├── Dockerfile                   # Python 3.11 + FFmpeg container
├── requirements.txt             # Python dependencies
│
├── processing/                  # Media processing modules
│   ├── video.py                # FFmpeg video compression
│   └── image.py                # Pillow image compression
│
├── integrations/               # External integrations
│   ├── tracking.py             # Job tracking (Azure Table Storage)
│   ├── auth.py                 # API key authentication
│   ├── database.py             # SIMPI API integration
│   └── notifications.py        # Webhook notifications
│
├── config/                     # Configuration
│   └── compression_config.py   # Compression settings
│
├── scripts/                    # Deployment scripts
│   ├── deploy-app-service-b2.sh        # Deploy to Azure (MAIN)
│   ├── cleanup-unused-resources.sh     # Clean up old resources
│   └── build-in-azure.sh               # Legacy Functions deployment
│
├── media-uploader/             # Next.js web UI (optional)
│   └── src/app/api/            # Upload API routes
│
└── docs/
    ├── APP_SERVICE_B2_MIGRATION.md     # Migration guide
    └── AZURE_STORAGE_AUTH.md           # Authentication setup
```

## ⚙️ Configuration

### Required Environment Variables

Set in Azure Portal → App Service → Configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `AzureWebJobsStorage` | Storage account connection string | `DefaultEndpointsProtocol=https;...` |
| `API_KEY` | Authentication key for /api/status | Generate with `openssl rand -hex 32` |
| `COMMIT_SHA` | Deployment version (auto-set by script) | `abc123` |
| `WEBSITES_PORT` | Container port | `80` |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | Prevent file shadowing | `false` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SIMPI_API_BASE_URL` | External API base URL | - |
| `SIMPI_API_TOKEN` | External API token | - |
| `WEBHOOK_URL` | Completion webhook | - |

## 🎨 Supported Formats

### Images
- **Input:** PNG, JPG, JPEG, GIF, BMP, WebP
- **Output:** WebP (always)
- **Processing:** Pillow with quality optimization

**Compression Settings:**
- **Format:** WebP
- **Quality:** 80 (range: 0-100)
- **Compression Method:** 6 (best compression)
- **Max Resolution:** 2048px (larger images are scaled down)
- **Color Mode:** RGB (preserves RGBA if transparency detected)
- **Resampling:** LANCZOS (high quality)

### Videos
- **Input:** MP4, MOV, AVI, WebM, FLV, WMV
- **Output:** H.264 MP4 (no audio)
- **Processing:** FFmpeg with VBR encoding

**Compression Settings:**
- **Video Codec:** libx264 (H.264)
- **Bitrate Mode:** VBR (Variable Bitrate)
- **Target Bitrate:** 1.2 Mbps
- **Max Bitrate:** 2 Mbps
- **Buffer Size:** 4 MB (4000k)
- **Encoding Speed:** fast preset (faster encoding, minimal quality loss)
- **Max Resolution:** 1280x720 (scales down keeping aspect ratio if larger)
- **Audio:** Removed (no audio track)
- **Streaming:** +faststart enabled (web-optimized)

**Rationale:** 720p @ 1.2 Mbps provides excellent quality for instructional content while minimizing file size for fast loading during step transitions.

## 🧹 Automatic Cleanup

Background worker runs every 5 minutes:
- ✅ Deletes upload blobs immediately after processing
- ✅ Deletes processed blobs 10 minutes after completion
- ✅ Removes associated job records from Table Storage

**Storage costs:** ~$2-5/month (minimal)

## 📊 Monitoring

### Health Check
```bash
curl https://mediaprocessor-b2.azurewebsites.net/api/health
```

### View Logs
```bash
# Azure Portal → App Service → Log stream

# Or via CLI
az webapp log tail \
  --name mediaprocessor-b2 \
  --resource-group rg-11-video-compressor-az-function
```

### Metrics
Monitor in Azure Portal:
- CPU Percentage (expect <50% for 2-3 concurrent)
- Memory Percentage (expect <60%)
- HTTP Response Time (expect <1s for images)
- HTTP 5xx Errors (expect 0)

## 🔐 Security

- ✅ API key authentication for status endpoint
- ✅ SAS tokens for download URLs (1-hour expiry)
- ✅ No public blob access
- ✅ HTTPS only
- ✅ Azure AD RBAC for admin operations

## 💰 Cost Breakdown

| Resource | Monthly Cost |
|----------|--------------|
| App Service B2 | ~$55 |
| Blob Storage | ~$2-5 |
| Table Storage | <$1 |
| Bandwidth | ~$2 |
| **Total** | **~$60/month** |

**Capacity:** 2-3 concurrent uploads, ~1,000 uploads/month

## 🚨 Troubleshooting

### "Blob not found" error
**Cause:** File deleted before processing
**Fix:** Call `/api/process` immediately after upload (< 2 seconds)

### Slow processing (>5s for images)
**Cause:** Instance overloaded
**Fix:** Upgrade to B3 ($110/month, 4 cores) or S1 ($75/month with auto-scale)

### "Permission denied" on scripts
**Cause:** Missing Azure AD roles
**Fix:** See [AZURE_STORAGE_AUTH.md](./AZURE_STORAGE_AUTH.md)

## 📚 Documentation

- **[APP_SERVICE_B2_MIGRATION.md](./APP_SERVICE_B2_MIGRATION.md)** - Migration from Functions EP1
- **[AZURE_STORAGE_AUTH.md](./AZURE_STORAGE_AUTH.md)** - Storage authentication setup
- **[docs/archived/](./docs/archived/)** - Legacy documentation

## 🧪 Testing

Run end-to-end test:
```bash
./test-flow.sh
```

This:
1. Uploads test.png to blob storage
2. Calls /api/process
3. Polls /api/status until completed
4. Displays download URL and metrics

## 🛠️ Development

### Local Testing (with Docker)

```bash
# Build container
docker build -t mediaprocessor .

# Run locally
docker run -p 8080:80 \
  -e AzureWebJobsStorage="<connection-string>" \
  mediaprocessor

# Test
curl http://localhost:8080/api/health
```

### Deploy Changes

```bash
# Deploy updated code to Azure
./scripts/deploy-app-service-b2.sh

# Verify version
curl https://mediaprocessor-b2.azurewebsites.net/api/version
```

## 📝 License

Private - SIMPI Internal Use Only

---

**Status:** ✅ Production Ready
**Version:** 1.0 (App Service B2)
**Last Updated:** 2025-10-05
