# API Documentation

Complete API reference for the Azure Media Compression System.

**Base URL:** `https://mediaprocessor-b2.azurewebsites.net`

---

## Table of Contents

- [Compression Specifications](#compression-specifications)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [GET /api/health](#get-apihealth)
  - [GET /api/version](#get-apiversion)
  - [POST /api/process](#post-apiprocess)
  - [GET /api/status](#get-apistatus)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)
- [Examples](#examples)

---

## Compression Specifications

### Image Compression

**Input Formats:** PNG, JPG, JPEG, GIF, BMP, WebP
**Output Format:** WebP (always)

**Settings:**
- **Quality:** 80 (range: 0-100)
- **Compression Method:** 6 (best compression)
- **Max Resolution:** 2048px (larger images are scaled down proportionally)
- **Color Mode:** RGB (preserves RGBA if transparency detected)
- **Resampling:** LANCZOS (high quality)

**Expected Results:**
- 25-35% smaller than original PNG/JPG
- Maintains visual quality
- Web-optimized format with broad browser support

### Video Compression

**Input Formats:** MP4, MOV, AVI, WebM, FLV, WMV
**Output Format:** H.264 MP4 (no audio)

**Settings:**
- **Video Codec:** libx264 (H.264)
- **Bitrate Mode:** VBR (Variable Bitrate)
- **Target Bitrate:** 1.2 Mbps
- **Max Bitrate:** 2 Mbps
- **Buffer Size:** 4 MB (4000k)
- **Encoding Speed:** medium preset (balanced quality/speed)
- **Max Resolution:** 1920x1080 (scales down keeping aspect ratio if larger)
- **Audio:** Removed (no audio track)
- **Streaming:** +faststart enabled (web-optimized)

**Expected Results:**
- Consistent bitrate output (VBR maintains quality while meeting target bitrate)
- Output size depends on video duration (~9MB per minute @ 1.2 Mbps)
- Maintains good visual quality at 1080p
- Balanced encoding speed for synchronous processing
- Web-optimized for streaming

---

## Authentication

### No Authentication Required
- `GET /api/health`
- `GET /api/version`
- `POST /api/process`

### API Key Required
- `GET /api/status`

**Header Format:**
```
X-API-Key: your-api-key-here
```

**Alternative:**
```
Authorization: Bearer your-api-key-here
```

---

## Endpoints

### GET /api/health

Health check endpoint for monitoring.

**Request:**
```bash
curl https://mediaprocessor-b2.azurewebsites.net/api/health
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "build_time": "unknown",
  "bundle_version": "[4.*, 5.0.0)",
  "host_uptime_seconds": 3600,
  "endpoints": [
    "POST /api/process",
    "GET /api/status",
    "GET /api/health",
    "GET /api/version"
  ]
}
```

---

### GET /api/version

Deployment version information for debugging.

**Request:**
```bash
curl https://mediaprocessor-b2.azurewebsites.net/api/version
```

**Response:** `200 OK`
```json
{
  "version": "abc123",
  "instance": "4c49e5ee1c9d26e3d207f81f51be02bb2c4d67839b9f7b25c24fceef7fd9b44e",
  "hostname": "pl0sdlwk00006X",
  "uptime_seconds": 3600,
  "timestamp": "2025-10-05T12:00:00.000000"
}
```

**Fields:**
- `version`: Git commit SHA
- `instance`: Azure instance ID
- `hostname`: Container hostname
- `uptime_seconds`: Time since container start
- `timestamp`: Current UTC timestamp

---

### POST /api/process

Process a media file that's been uploaded to blob storage.

**Request:**
```bash
curl -X POST https://mediaprocessor-b2.azurewebsites.net/api/process \
  -H 'Content-Type: application/json' \
  -d '{"blob_name": "upload-123.png"}'
```

**Request Body:**
```json
{
  "blob_name": "upload-123.png"
}
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `blob_name` | string | Yes | Name of the blob in the `uploads` container |

**Response:** `200 OK`
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
    "output_url": "https://mediablobazfct.blob.core.windows.net/processed/processed-123.png?se=2025-10-05T13:00:00Z&sp=r&sv=2023-11-03&sr=b&sig=...",
    "format": "PNG"
  }
}
```

**Response Fields:**
- `status`: `"success"` or `"error"`
- `blob_name`: Original blob name
- `result.output_url`: Download URL (SAS token, valid for 1 hour)
- `result.compression_ratio`: Compressed size / original size
- `result.processing_time`: Time in seconds
- `result.format`: Output format (PNG, JPG, MP4, etc.)

**Error Response:** `400 Bad Request`
```json
{
  "status": "error",
  "error": "blob_name is required"
}
```

**Error Response:** `500 Internal Server Error`
```json
{
  "status": "error",
  "error": "The specified blob does not exist."
}
```

---

### GET /api/status

Query the processing status of a job.

**Authentication Required:** Yes (X-API-Key header)

**Request:**
```bash
curl -H "X-API-Key: your-api-key" \
  "https://mediaprocessor-b2.azurewebsites.net/api/status?blob_name=upload-123.png"
```

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `blob_name` | string | Yes | Name of the blob to check |

**Response (Queued):** `200 OK`
```json
{
  "blob_name": "upload-123.png",
  "status": "queued",
  "file_size": 1048576,
  "file_type": "png",
  "created_at": "2025-10-05T12:00:00.000000+00:00",
  "updated_at": "2025-10-05T12:00:00.000000+00:00"
}
```

**Response (Processing):** `200 OK`
```json
{
  "blob_name": "upload-123.png",
  "status": "processing",
  "file_size": 1048576,
  "file_type": "png",
  "created_at": "2025-10-05T12:00:00.000000+00:00",
  "updated_at": "2025-10-05T12:00:01.000000+00:00",
  "processing_started_at": "2025-10-05T12:00:01.000000+00:00"
}
```

**Response (Completed):** `200 OK`
```json
{
  "blob_name": "upload-123.png",
  "status": "completed",
  "file_size": 1048576,
  "file_type": "png",
  "created_at": "2025-10-05T12:00:00.000000+00:00",
  "updated_at": "2025-10-05T12:00:02.000000+00:00",
  "processing_started_at": "2025-10-05T12:00:01.000000+00:00",
  "completed_at": "2025-10-05T12:00:02.000000+00:00",
  "processed_blob_name": "processed-123.png",
  "original_size": 1048576,
  "compressed_size": 524288,
  "compression_ratio": 0.5,
  "processing_time": 0.234,
  "output_url": "https://mediablobazfct.blob.core.windows.net/processed/processed-123.png?se=..."
}
```

**Response (Failed):** `200 OK`
```json
{
  "blob_name": "upload-123.png",
  "status": "failed",
  "file_size": 1048576,
  "file_type": "png",
  "created_at": "2025-10-05T12:00:00.000000+00:00",
  "updated_at": "2025-10-05T12:00:02.000000+00:00",
  "failed_at": "2025-10-05T12:00:02.000000+00:00",
  "error_message": "The specified blob does not exist."
}
```

**Status Values:**
- `queued`: Job created, waiting to process
- `processing`: Currently processing
- `completed`: Successfully processed
- `failed`: Processing failed

**Error Response:** `401 Unauthorized`
```json
{
  "error": "Unauthorized: Missing or invalid API key"
}
```

**Error Response:** `400 Bad Request`
```json
{
  "error": "blob_name parameter is required"
}
```

**Error Response:** `404 Not Found`
```json
{
  "error": "No job found for blob: upload-123.png"
}
```

---

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "status": "error",
  "error": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | Request processed successfully |
| `400` | Bad Request | Missing required parameters, invalid format |
| `401` | Unauthorized | Missing or invalid API key |
| `404` | Not Found | Job or blob not found |
| `500` | Internal Server Error | Processing failure, system error |

---

## Rate Limits

**Current Limits:**
- **Concurrent uploads:** 2-3 simultaneous
- **Per-file size:** No explicit limit (recommended <500MB)
- **Requests per minute:** No explicit limit

**Capacity Planning:**
- Designed for ~1,000 uploads/month
- Processing time: ~0.05-0.1s for images, ~2-5s for small videos
- If exceeding limits, consider upgrading to B3 or S1 tier

---

## Examples

### Complete Upload & Process Flow

```javascript
// 1. Generate unique blob name
const blobName = `upload-${Date.now()}.png`;

// 2. Upload to Azure Blob Storage (using Azure SDK)
const sasToken = "your-sas-token";
const containerClient = new ContainerClient(
  `https://mediablobazfct.blob.core.windows.net/uploads?${sasToken}`
);
const blockBlobClient = containerClient.getBlockBlobClient(blobName);
await blockBlobClient.uploadData(fileData);

// 3. Trigger processing
const response = await fetch('https://mediaprocessor-b2.azurewebsites.net/api/process', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ blob_name: blobName })
});

const data = await response.json();

if (data.status === 'success') {
  console.log('Download URL:', data.result.output_url);
  console.log('Compression ratio:', data.result.compression_ratio);
}
```

### Poll for Status

```javascript
async function pollStatus(blobName, apiKey) {
  let status = 'queued';

  while (status === 'queued' || status === 'processing') {
    const response = await fetch(
      `https://mediaprocessor-b2.azurewebsites.net/api/status?blob_name=${blobName}`,
      {
        headers: {'X-API-Key': apiKey}
      }
    );

    const data = await response.json();
    status = data.status;

    if (status === 'completed') {
      return data.output_url;
    } else if (status === 'failed') {
      throw new Error(data.error_message);
    }

    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s
  }
}
```

### Error Handling

```javascript
try {
  const response = await fetch('/api/process', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ blob_name: 'upload-123.png' })
  });

  const data = await response.json();

  if (data.status === 'error') {
    console.error('Processing failed:', data.error);
  } else {
    console.log('Success!', data.result.output_url);
  }
} catch (error) {
  console.error('Network error:', error);
}
```

---

## Support

For issues or questions:
1. Check [README.md](../README.md) troubleshooting section
2. Review [APP_SERVICE_B2_MIGRATION.md](../APP_SERVICE_B2_MIGRATION.md) for migration details
3. Check Azure Portal logs for detailed error messages

---

**Last Updated:** 2025-10-05
**Version:** 1.0 (App Service B2)
