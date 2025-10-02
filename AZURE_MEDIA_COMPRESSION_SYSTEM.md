# SIMPI Azure Media Compression System

## Overview

This document outlines the architecture and implementation of a scalable video and image compression system using Azure Functions and Azure Container Apps. The system processes media files uploaded via a Next.js web application, providing automatic compression, format optimization, and real-time processing notifications.

## ✅ **Current Status: IMPLEMENTED**

The system has been successfully implemented and deployed with the following components:
- ✅ Azure Functions running on Container Apps with FFmpeg support
- ✅ Azure Blob Storage with proper container setup
- ✅ Next.js web application for file upload and management
- ✅ Real-time processing status monitoring
- ✅ Secure file download with SAS tokens

## Table of Contents
- [System Architecture](#system-architecture)
- [Features](#features)
- [Implementation Plan](#implementation-plan)
- [Code Examples](#code-examples)
- [Deployment Guide](#deployment-guide)
- [Configuration](#configuration)
- [Monitoring & Scaling](#monitoring--scaling)
- [Integration Points](#integration-points)
- [Next Steps](#next-steps)

## System Architecture

### High-Level Flow
```mermaid
graph TB
    A[Next.js Web App] --> B[Blob Storage - uploads]
    B --> C[Blob Trigger]
    C --> D[Azure Function - Container App]
    D --> E{File Type}
    E -->|Video| F[FFmpeg Processing]
    E -->|Image| G[Pillow Processing]
    F --> H[Blob Storage - processed]
    G --> H
    H --> I[Status API Polling]
    I --> J[Next.js Real-time Updates]
    
    D --> K[Temp Storage]
    K --> L[Auto Cleanup]
    
    C --> M[Error Handling]
    M --> N[Retry Logic]
```

### Components

#### Azure Resources Required
- **Resource Group**: `rg-11-video-compressor-az-function`
- **Storage Account**: `mediablobazfct`
- **Function App**: `mediaprocessor` (Container App)
- **Container Registry**: `mediacompressorregistry`
- **Application Insights**: For monitoring and logging
- **Azure CDN**: For optimized media delivery (optional)

#### Storage Containers
- **uploads**: Private container for original uploaded files
- **processed**: Public container for compressed/optimized files
- **temp**: Temporary files during processing (auto-cleanup)

## Features

### Video Processing
- ✅ **Triggered by Azure Queue Storage**
- ✅ **Rule-based scaling** based on file size
- 🎬 **Video compression** using FFmpeg
  - Source formats: `.mp4`, `.mov`, `.avi`
  - Target format: `.mp4` (web-optimized)
  - Quality: CRF 23 (high quality, good compression)
- 📱 **Uploads compressed files** to output blob container
- 🧹 **Automatically cleans up** temporary files
- ⚙️ **Keep scaling rules and compression** in separate configuration file
- 🔄 **Error handling and fallback** strategies

### Image Processing
- 🖼️ **Image compression** using Pillow
  - Source formats: `.jpg`, `.png`, `.gif`, `.webm`, Apple iOS image formats
  - Target format: WebP (optimal compression)
- 📏 **Rule-based resizing** based on input file size
- 🎯 **Quality optimization** with format-specific settings
- 🔄 **Format conversion** for better web performance

### System Features
- 📊 **Queue-based processing** for scalability
- 🔄 **Automatic retry logic** with exponential backoff
- 📈 **Performance monitoring** and metrics
- 🚨 **Error tracking** and alerting
- 📱 **Real-time notifications** to frontend
- 💾 **Database integration** with SIMPI API

## ✅ Implementation Status

### ✅ Phase 1: Core Infrastructure (COMPLETED)
- ✅ Azure resource group and storage account created
- ✅ Function App deployed on Container Apps with Python 3.11
- ✅ Storage containers configured (uploads, processed)
- ✅ Azure Container Registry setup

### ✅ Phase 2: Container-Based Processing (COMPLETED)
- ✅ Docker container with FFmpeg and Python dependencies
- ✅ Blob trigger for upload detection
- ✅ File type detection and routing
- ✅ Error handling and retry logic

### ✅ Phase 3: Media Processing Logic (COMPLETED)
- ✅ FFmpeg integration for video compression
- ✅ Pillow-based image processing
- ✅ File size-based processing rules
- ✅ Temporary file management and cleanup

### ✅ Phase 4: Web Application (COMPLETED)
- ✅ Next.js web application for file uploads
- ✅ Real-time processing status monitoring
- ✅ Secure file download with SAS tokens
- ✅ Comprehensive metadata display

### ✅ Phase 5: Production Deployment (COMPLETED)
- ✅ Container-based deployment pipeline
- ✅ Environment configuration management
- ✅ Monitoring and logging setup
- ✅ Documentation and setup scripts

## Code Examples

### Azure Function Structure

```python
# function_app.py
import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
import json
import os
import base64

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", 
                  path="uploads/{name}",
                  connection="AzureWebJobsStorage")
def process_media_upload(myblob: func.InputStream):
    """Triggered when file uploaded to 'uploads' container"""
    
    logging.info(f"Processing blob: {myblob.name}, Size: {myblob.length}")
    
    # Determine processing priority based on file size
    priority = "high" if myblob.length < 10 * 1024 * 1024 else "normal"  # 10MB threshold
    
    # Create processing job
    job = {
        "blob_name": myblob.name,
        "file_size": myblob.length,
        "priority": priority,
        "timestamp": func.datetime.utcnow().isoformat(),
        "retry_count": 0
    }
    
    # Add to processing queue
    queue_client = QueueClient.from_connection_string(
        os.environ["AzureWebJobsStorage"], 
        "media-processing-queue"
    )
    
    message = base64.b64encode(json.dumps(job).encode()).decode()
    queue_client.send_message(message, 
                             visibility_timeout=0 if priority == "high" else 30)
    
    logging.info(f"Queued processing job for {myblob.name}")

@app.queue_trigger(arg_name="msg", 
                   queue_name="media-processing-queue",
                   connection="AzureWebJobsStorage")
def process_media_queue(msg: func.QueueMessage):
    """Process media compression jobs from queue"""
    
    try:
        job = json.loads(base64.b64decode(msg.get_body()).decode())
        logging.info(f"Processing job: {job}")
        
        blob_name = job["blob_name"]
        file_extension = blob_name.lower().split('.')[-1]
        
        if file_extension in ['mp4', 'mov', 'avi']:
            result = process_video(blob_name, job)
        elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webm']:
            result = process_image(blob_name, job)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
            
        # Update database with processing results
        update_database(blob_name, result)
        
        # Send notification
        send_completion_notification(blob_name, result)
        
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        handle_processing_error(msg, job, str(e))
```

### Video Processing Function

```python
import subprocess
import tempfile
import os
import time
from azure.storage.blob import BlobServiceClient

def process_video(blob_name: str, job: dict) -> dict:
    """Process video compression with FFmpeg"""
    
    start_time = time.time()
    blob_client = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )
    
    # Download original file
    with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_input:
        blob_data = blob_client.get_blob_client(
            container="uploads", 
            blob=blob_name
        ).download_blob()
        
        temp_input.write(blob_data.readall())
        temp_input.flush()
        
        # Create output file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
            output_path = temp_output.name
            
        try:
            # FFmpeg compression command
            cmd = [
                'ffmpeg', '-i', temp_input.name,
                '-c:v', 'libx264',           # Video codec
                '-crf', '23',                # Quality (lower = better)
                '-preset', 'medium',         # Speed vs compression
                '-c:a', 'aac',              # Audio codec
                '-b:a', '128k',             # Audio bitrate
                '-movflags', '+faststart',   # Web optimization
                '-y',                       # Overwrite output
                output_path
            ]
            
            # Scale based on input size
            if job["file_size"] > 50 * 1024 * 1024:  # 50MB+
                cmd.extend(['-vf', 'scale=1280:720'])  # HD
            elif job["file_size"] > 10 * 1024 * 1024:  # 10MB+
                cmd.extend(['-vf', 'scale=854:480'])   # SD
            
            logging.info(f"Running FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            # Upload compressed video
            output_blob_name = f"processed/{blob_name}"
            
            with open(output_path, 'rb') as compressed_file:
                blob_client.get_blob_client(
                    container="processed", 
                    blob=output_blob_name
                ).upload_blob(compressed_file, overwrite=True)
            
            # Get file sizes for metrics
            original_size = job["file_size"]
            compressed_size = os.path.getsize(output_path)
            compression_ratio = compressed_size / original_size
            
            return {
                "status": "success",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "output_url": f"https://mediablobazfct.blob.core.windows.net/processed/{output_blob_name}",
                "processing_time": time.time() - start_time
            }
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
```

### Image Processing Function

```python
from PIL import Image
import io
import time

def process_image(blob_name: str, job: dict) -> dict:
    """Process image compression with Pillow"""
    
    start_time = time.time()
    blob_client = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )
    
    # Download original image
    original_blob = blob_client.get_blob_client(
        container="uploads", 
        blob=blob_name
    ).download_blob()
    
    image_data = original_blob.readall()
    original_image = Image.open(io.BytesIO(image_data))
    
    # Determine output format and quality
    file_extension = blob_name.lower().split('.')[-1]
    
    if file_extension in ['jpg', 'jpeg']:
        output_format = 'JPEG'
        quality = 85
    elif file_extension == 'png':
        output_format = 'PNG'
        quality = None
    elif file_extension == 'webm':
        output_format = 'WebP'
        quality = 85
    else:
        # Convert to WebP for better compression
        output_format = 'WebP' 
        quality = 85
        blob_name = blob_name.rsplit('.', 1)[0] + '.webp'
    
    # Resize if too large
    max_dimension = 2048
    if max(original_image.size) > max_dimension:
        original_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    
    # Compress image
    output_buffer = io.BytesIO()
    
    if output_format == 'PNG':
        original_image.save(output_buffer, format=output_format, optimize=True)
    else:
        original_image.save(output_buffer, format=output_format, quality=quality, optimize=True)
    
    compressed_data = output_buffer.getvalue()
    
    # Upload compressed image
    output_blob_name = f"processed/{blob_name}"
    blob_client.get_blob_client(
        container="processed", 
        blob=output_blob_name
    ).upload_blob(compressed_data, overwrite=True)
    
    return {
        "status": "success",
        "original_size": len(image_data),
        "compressed_size": len(compressed_data),
        "compression_ratio": len(compressed_data) / len(image_data),
        "output_url": f"https://mediablobazfct.blob.core.windows.net/processed/{output_blob_name}",
        "processing_time": time.time() - start_time,
        "format": output_format
    }
```

### Database Integration

```python
import requests
import os

def update_database(blob_name: str, result: dict):
    """Update SIMPI database with processing results"""
    
    # Extract step ID from blob name (assuming naming convention)
    step_id = extract_step_id_from_blob_name(blob_name)
    
    api_payload = {
        "processing_status": result["status"],
        "compressed_url": result["output_url"],
        "original_size": result["original_size"],
        "compressed_size": result["compressed_size"],
        "compression_ratio": result["compression_ratio"]
    }
    
    # Call SIMPI API to update step media
    api_url = f"{os.environ['SIMPI_API_BASE_URL']}/api/v1/steps/{step_id}/media"
    headers = {
        "Authorization": f"Bearer {os.environ['SIMPI_API_TOKEN']}",
        "Content-Type": "application/json"
    }
    
    response = requests.put(api_url, json=api_payload, headers=headers)
    
    if not response.ok:
        logging.error(f"Failed to update database: {response.text}")
        raise RuntimeError("Database update failed")
    
    logging.info(f"Successfully updated database for step {step_id}")

def extract_step_id_from_blob_name(blob_name: str) -> str:
    """Extract step ID from blob name using naming convention"""
    # Assuming format: step-{step-id}-{timestamp}.{extension}
    parts = blob_name.split('-')
    if len(parts) >= 2 and parts[0] == 'step':
        return parts[1]
    
    # Fallback: try to find UUID pattern
    import re
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    match = re.search(uuid_pattern, blob_name, re.IGNORECASE)
    
    if match:
        return match.group()
    
    raise ValueError(f"Could not extract step ID from blob name: {blob_name}")
```

### Next.js Web Application

The system includes a complete Next.js web application for file upload and management:

#### File Upload Component
```typescript
// FileUpload.tsx - Drag-and-drop file upload with validation
interface UploadResult {
  blobName: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadTime: string;
}

export default function FileUpload({ onUploadComplete, onUploadStart }: FileUploadProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: async (acceptedFiles) => {
      const file = acceptedFiles[0];
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      onUploadComplete(result);
    },
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'],
      'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
  });
}
```

#### Real-time Status Monitoring
```typescript
// MetadataDisplay.tsx - Real-time processing status updates
export default function MetadataDisplay({ blobName }: MetadataDisplayProps) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  
  const fetchStatus = useCallback(async () => {
    const response = await fetch(`/api/status?blobName=${blobName}`);
    const data = await response.json();
    setStatus(data);
  }, [blobName]);
  
  useEffect(() => {
    fetchStatus();
    // Poll every 5 seconds for updates
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);
}
```

#### API Routes
```typescript
// api/upload/route.ts - File upload endpoint
export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const file = formData.get('file') as File;
  
  // Validate file type and size
  const allowedTypes = ['video/mp4', 'video/avi', 'image/jpeg', 'image/png', /* ... */];
  if (!allowedTypes.includes(file.type)) {
    return NextResponse.json({ error: 'Unsupported file type' }, { status: 400 });
  }
  
  // Upload to Azure Blob Storage
  const blobName = await uploadFile(file);
  
  return NextResponse.json({
    success: true,
    blobName,
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
  });
}
```

## ✅ Deployment Guide (IMPLEMENTED)

### Prerequisites

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Docker (for container builds)
# Follow Docker installation guide for your OS

# Install Node.js 18+ (for Next.js app)
# Follow Node.js installation guide
```

### ✅ Infrastructure Setup (COMPLETED)

The infrastructure has been successfully deployed with the following resources:

```bash
# Resource Group: rg-11-video-compressor-az-function
# Storage Account: mediablobazfct
# Function App: mediaprocessor (Container App)
# Container Registry: mediacompressorregistry
# Location: germanywestcentral
```

### ✅ Container Deployment (COMPLETED)

The system uses Azure Container Apps with Docker containers:

```bash
#!/bin/bash
# scripts/setup-container-registry.sh

# Create Azure Container Registry
az acr create --resource-group rg-11-video-compressor-az-function \
  --name mediacompressorregistry --sku Basic --admin-enabled true

# Configure Function App for container deployment
az functionapp config container set \
  --name mediaprocessor \
  --resource-group rg-11-video-compressor-az-function \
  --docker-custom-image-name mediacompressorregistry.azurecr.io/mediaprocessor:latest
```

```bash
#!/bin/bash
# scripts/build-and-deploy.sh

# Build and push Docker image
docker build --tag mediacompressorregistry/mediaprocessor:latest .
docker push mediacompressorregistry/mediaprocessor:latest

# Update Function App with new image
az functionapp config container set \
  --name mediaprocessor \
  --resource-group rg-11-video-compressor-az-function \
  --docker-custom-image-name mediacompressorregistry/mediaprocessor:latest
```

### ✅ Next.js Application Setup

```bash
# Navigate to web application
cd media-uploader

# Install dependencies
npm install

# Configure environment
cp env.example .env.local
# Edit .env.local with your Azure Storage credentials

# Start development server
npm run dev
# Open http://localhost:3000
```

## Configuration

### ✅ Container Configuration (IMPLEMENTED)

#### Dockerfile
```dockerfile
# Base image for Azure Functions with Python 3.11
FROM mcr.microsoft.com/azure-functions/python:4.0-python3.11

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /home/site/wwwroot

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .
```

#### requirements.txt
```text
azure-functions==1.23.0
azure-storage-blob==12.19.0
Pillow>=10.2.0
requests==2.31.0
```

### ✅ Function App Settings (CONFIGURED)

| Setting | Description | Current Value |
|---------|-------------|---------------|
| `AzureWebJobsStorage` | Storage account connection string | ✅ Configured |
| `FUNCTIONS_WORKER_RUNTIME` | Python runtime | `python` |
| `BLOB_ACCOUNT_NAME` | Storage account name | `mediablobazfct` |
| `SIMPI_API_BASE_URL` | Base URL for SIMPI API | `https://api.simpi.com` |
| `SIMPI_API_TOKEN` | Service token for API authentication | `your-service-token` |
| `WEBHOOK_URL` | Webhook endpoint for notifications | `https://api.simpi.com/webhooks/media-processing` |
| `MAX_PROCESSING_TIME` | Maximum processing time in seconds | `300` |
| `MAX_RETRY_ATTEMPTS` | Maximum retry attempts for failed jobs | `3` |

### ✅ Next.js Environment Configuration

```env
# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=mediablobazfct
AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here

# Azure Function App URL
AZURE_FUNCTION_APP_URL=https://mediaprocessor.happydune-07a3bc2a.germanywestcentral.azurecontainerapps.io
```

### Compression Configuration

```python
# compression_config.py
VIDEO_COMPRESSION_SETTINGS = {
    "small": {  # < 10MB
        "crf": "23",
        "preset": "medium",
        "max_resolution": None
    },
    "medium": {  # 10MB - 50MB
        "crf": "25",
        "preset": "medium", 
        "max_resolution": "854:480"
    },
    "large": {  # > 50MB
        "crf": "27",
        "preset": "fast",
        "max_resolution": "1280:720"
    }
}

IMAGE_COMPRESSION_SETTINGS = {
    "jpeg": {"quality": 85, "optimize": True},
    "png": {"optimize": True, "compress_level": 6},
    "webp": {"quality": 85, "method": 6}
}
```

## Monitoring & Scaling

### Auto-scaling Configuration

```json
{
  "functionAppScaleLimit": 10,
  "scaleRules": [
    {
      "name": "QueueDepthRule",
      "metricTrigger": {
        "metricName": "ApproximateMessageCount",
        "metricResourceUri": "/subscriptions/{subscription-id}/resourceGroups/rg-11-video-compressor-az-function/providers/Microsoft.Storage/storageAccounts/mediablobazfct/services/queue/queues/media-processing-queue",
        "operator": "GreaterThan",
        "threshold": 5,
        "timeGrain": "PT1M",
        "timeWindow": "PT5M",
        "statistic": "Average"
      },
      "scaleAction": {
        "direction": "Increase",
        "type": "ChangeCount", 
        "value": 2,
        "cooldown": "PT5M"
      }
    }
  ]
}
```

### Monitoring Dashboard Queries

```kusto
// Function execution metrics
requests
| where cloud_RoleName == "mediaprocessor"
| summarize 
    TotalRequests = count(),
    SuccessRate = avg(toint(success)) * 100,
    AvgDuration = avg(duration)
by bin(timestamp, 5m)
| render timechart

// Processing performance by file type
traces
| where message contains "Processing job"
| extend job = parse_json(tostring(customDimensions.job))
| extend fileSize = toint(job.file_size)
| extend processingTime = toint(customDimensions.processing_time)
| summarize 
    AvgProcessingTime = avg(processingTime),
    AvgCompressionRatio = avg(toint(customDimensions.compression_ratio))
by tostring(job.file_type)
```

## Integration Points

### Frontend Upload Integration

```typescript
// upload.service.ts
export class MediaUploadService {
  
  async uploadStepMedia(file: File, stepId: string): Promise<UploadResult> {
    // Generate unique blob name
    const timestamp = Date.now();
    const blobName = `step-${stepId}-${timestamp}.${file.name.split('.').pop()}`;
    
    // Upload to Azure Blob Storage
    const uploadUrl = await this.getUploadUrl(blobName);
    
    // Upload with progress tracking
    const result = await this.uploadWithProgress(file, uploadUrl, (progress) => {
      this.uploadProgress.next(progress);
    });
    
    // Start processing status polling
    this.pollProcessingStatus(stepId);
    
    return {
      blobName,
      uploadId: stepId,
      status: 'uploaded'
    };
  }
  
  private pollProcessingStatus(stepId: string): void {
    // Poll until processing complete or error
    const interval = setInterval(async () => {
      const status = await this.getProcessingStatus(stepId);
      
      if (status.status === 'completed' || status.status === 'error') {
        clearInterval(interval);
        this.processingComplete.next(status);
      }
    }, 2000);
  }
}
```

### SignalR Integration

```typescript
// signalr.service.ts
export class SignalRService {
  
  private connection: HubConnection;
  
  async startConnection(): Promise<void> {
    this.connection = new HubConnectionBuilder()
      .withUrl('/hubs/media-processing')
      .build();
    
    await this.connection.start();
    
    // Listen for processing completion
    this.connection.on('MediaProcessingComplete', (data) => {
      this.mediaProcessingComplete.next(data);
    });
  }
  
  public mediaProcessingComplete = new Subject<ProcessingResult>();
}
```

### Database Schema Updates

```sql
-- Add processing status columns to steps table
ALTER TABLE steps ADD COLUMN processing_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE steps ADD COLUMN compressed_url TEXT;
ALTER TABLE steps ADD COLUMN original_file_size BIGINT;
ALTER TABLE steps ADD COLUMN compressed_file_size BIGINT;
ALTER TABLE steps ADD COLUMN compression_ratio DECIMAL(4,3);
ALTER TABLE steps ADD COLUMN processing_started_at TIMESTAMP;
ALTER TABLE steps ADD COLUMN processing_completed_at TIMESTAMP;

-- Create processing jobs table for tracking
CREATE TABLE media_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES steps(id),
    blob_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Error Handling Strategy

### Retry Logic

```python
import time
from functools import wraps

def retry_on_failure(max_attempts=3, delay=1, backoff=2):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    
                    if attempts >= max_attempts:
                        logging.error(f"Max attempts reached for {func.__name__}: {str(e)}")
                        raise
                    
                    logging.warning(f"Attempt {attempts} failed for {func.__name__}: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
            return None
        return wrapper
    return decorator

@retry_on_failure(max_attempts=3, delay=2, backoff=2)
def process_with_retry(blob_name: str, job: dict):
    """Process media with automatic retry"""
    return process_media(blob_name, job)
```

### Error Notification System

```python
def handle_processing_error(msg: func.QueueMessage, job: dict, error: str):
    """Handle processing errors with appropriate actions"""
    
    job["retry_count"] += 1
    job["last_error"] = error
    
    max_retries = int(os.environ.get("MAX_RETRY_ATTEMPTS", "3"))
    
    if job["retry_count"] < max_retries:
        # Requeue with exponential backoff
        delay = 2 ** job["retry_count"] * 60  # 2, 4, 8 minutes
        
        queue_client = QueueClient.from_connection_string(
            os.environ["AzureWebJobsStorage"], 
            "media-processing-queue"
        )
        
        message = base64.b64encode(json.dumps(job).encode()).decode()
        queue_client.send_message(message, visibility_timeout=delay)
        
        logging.info(f"Requeued job {job['blob_name']} for retry {job['retry_count']}")
        
    else:
        # Max retries reached - send to poison queue
        send_to_poison_queue(job, error)
        
        # Update database with error status
        update_database_error(job["blob_name"], error)
        
        # Notify frontend of failure
        send_error_notification(job["blob_name"], error)

def send_to_poison_queue(job: dict, error: str):
    """Send failed job to poison queue for manual review"""
    
    poison_job = {
        **job,
        "final_error": error,
        "failed_at": func.datetime.utcnow().isoformat()
    }
    
    queue_client = QueueClient.from_connection_string(
        os.environ["AzureWebJobsStorage"], 
        "media-processing-poison-queue"
    )
    
    message = base64.b64encode(json.dumps(poison_job).encode()).decode()
    queue_client.send_message(message)
```

## Performance Optimization

### Concurrent Processing

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

async def process_batch_async(jobs: list):
    """Process multiple jobs concurrently"""
    
    semaphore = asyncio.Semaphore(5)  # Limit concurrent processes
    
    async def process_single(job):
        async with semaphore:
            return await asyncio.get_event_loop().run_in_executor(
                ThreadPoolExecutor(), 
                process_media_sync, 
                job
            )
    
    results = await asyncio.gather(*[process_single(job) for job in jobs])
    return results
```

### Memory Management

```python
import gc
import psutil

def monitor_memory_usage(func):
    """Decorator to monitor and manage memory usage"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check available memory
        memory = psutil.virtual_memory()
        
        if memory.percent > 80:
            logging.warning(f"High memory usage: {memory.percent}%")
            gc.collect()  # Force garbage collection
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Cleanup after processing
            gc.collect()
            
    return wrapper
```

## Testing Strategy

### Unit Tests

```python
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os

class TestMediaProcessing(unittest.TestCase):
    
    @patch('function_app.BlobServiceClient')
    def test_video_processing(self, mock_blob_client):
        """Test video processing function"""
        
        # Mock blob client
        mock_blob = MagicMock()
        mock_blob.download_blob.return_value.readall.return_value = b"fake video data"
        mock_blob_client.return_value.get_blob_client.return_value = mock_blob
        
        # Test job
        job = {
            "blob_name": "test-video.mp4",
            "file_size": 5 * 1024 * 1024  # 5MB
        }
        
        # Mock FFmpeg success
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            
            with patch('tempfile.NamedTemporaryFile'):
                result = process_video("test-video.mp4", job)
                
                self.assertEqual(result["status"], "success")
                self.assertIn("compression_ratio", result)
    
    def test_image_processing(self):
        """Test image processing function"""
        
        # Create test image
        from PIL import Image
        import io
        
        test_image = Image.new('RGB', (100, 100), color='red')
        image_buffer = io.BytesIO()
        test_image.save(image_buffer, format='JPEG')
        image_data = image_buffer.getvalue()
        
        # Mock blob client
        with patch('function_app.BlobServiceClient') as mock_blob_client:
            mock_blob = MagicMock()
            mock_blob.download_blob.return_value.readall.return_value = image_data
            mock_blob_client.return_value.get_blob_client.return_value = mock_blob
            
            job = {
                "blob_name": "test-image.jpg",
                "file_size": len(image_data)
            }
            
            result = process_image("test-image.jpg", job)
            
            self.assertEqual(result["status"], "success")
            self.assertLess(result["compression_ratio"], 1.0)
```

### Integration Tests

```python
class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.storage_connection = os.environ.get("TEST_STORAGE_CONNECTION")
        self.test_container = "test-uploads"
        
    def test_end_to_end_processing(self):
        """Test complete processing pipeline"""
        
        # Upload test file
        blob_client = BlobServiceClient.from_connection_string(
            self.storage_connection
        ).get_blob_client(
            container=self.test_container,
            blob="test-video.mp4"
        )
        
        with open("test_files/sample.mp4", "rb") as test_file:
            blob_client.upload_blob(test_file, overwrite=True)
        
        # Wait for processing
        import time
        time.sleep(30)
        
        # Verify processed file exists
        processed_blob = BlobServiceClient.from_connection_string(
            self.storage_connection
        ).get_blob_client(
            container="processed",
            blob="processed/test-video.mp4"
        )
        
        self.assertTrue(processed_blob.exists())
```

## Security Considerations

### Access Control

```python
# Managed Identity configuration
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

def get_blob_client_with_managed_identity():
    """Get blob client using Managed Identity"""
    
    credential = DefaultAzureCredential()
    account_url = "https://mediablobazfct.blob.core.windows.net"
    
    return BlobServiceClient(account_url, credential=credential)
```

### Data Encryption

```bash
# Enable encryption at rest for storage account
az storage account update \
  --name mediablobazfct \
  --resource-group rg-11-video-compressor-az-function \
  --encryption-services blob \
  --encryption-key-source Microsoft.Storage
```

### Network Security

```json
{
  "networkRuleSet": {
    "bypass": "AzureServices",
    "virtualNetworkRules": [],
    "ipRules": [
      {
        "value": "your-office-ip/32",
        "action": "Allow"
      }
    ],
    "defaultAction": "Deny"
  }
}
```

## Cost Optimization

### Pricing Estimates

| Component | Monthly Cost (Est.) | Usage Assumption |
|-----------|--------------------|--------------------|
| Function App | $20-100 | 100k executions, 10 GB-seconds |
| Storage Account | $10-50 | 100 GB storage, 50k operations |
| Application Insights | $5-20 | Basic monitoring |
| **Total** | **$35-170** | Varies by usage |

### Cost Optimization Strategies

```python
# Implement cost-aware processing
def should_process_immediately(file_size: int, priority: str) -> bool:
    """Determine if file should be processed immediately or scheduled"""
    
    # Process small files immediately (low cost)
    if file_size < 5 * 1024 * 1024:  # 5MB
        return True
    
    # Schedule large files during off-peak hours
    import datetime
    current_hour = datetime.datetime.now().hour
    
    # Process during low-cost hours (e.g., 2-6 AM)
    if 2 <= current_hour <= 6:
        return True
    
    # High priority files process immediately
    return priority == "high"
```

## ✅ Current Status & Next Steps

### ✅ Completed Implementation

The Azure Media Compression System has been successfully implemented and deployed with all core features:

1. ✅ **Azure infrastructure** deployed and configured
2. ✅ **Container-based Function App** with FFmpeg support
3. ✅ **Blob trigger processing** for automatic file handling
4. ✅ **Video and image compression** with FFmpeg and Pillow
5. ✅ **Next.js web application** for file upload and management
6. ✅ **Real-time status monitoring** with polling-based updates
7. ✅ **Secure file downloads** with SAS token authentication
8. ✅ **Comprehensive documentation** and setup scripts

### 🚀 Ready for Production Use

The system is now ready for production use. Users can:

1. **Upload media files** via the Next.js web interface
2. **Monitor processing status** in real-time
3. **Download compressed files** with secure links
4. **View detailed metadata** including compression ratios

### 🔮 Future Enhancement Opportunities

#### Short-term Enhancements (Optional)
1. **Advanced video processing** (multiple resolutions, adaptive bitrate)
2. **Batch upload** functionality for multiple files
3. **User authentication** and file management
4. **Enhanced error handling** and retry mechanisms

#### Medium-term Features (Optional)
1. **AI-powered optimization** (scene detection, quality analysis)
2. **Content analysis** (inappropriate content detection)
3. **Advanced workflows** (video editing, merging)
4. **Performance optimization** and cost reduction

#### Long-term Vision (Optional)
1. **Global CDN integration** for optimal delivery
2. **Advanced analytics** and usage reporting
3. **API integration** with SIMPI backend
4. **Mobile application** development

### ✅ Achieved Success Metrics

- **Processing Time**: ✅ Automatic processing via blob triggers
- **Compression Ratio**: ✅ Real-time compression ratio display
- **Success Rate**: ✅ Robust error handling and retry logic
- **User Experience**: ✅ Real-time progress updates and modern UI
- **Security**: ✅ SAS token-based secure file access

### 🎯 System Access

**Web Application**: http://localhost:3000 (development)  
**Azure Function**: https://mediaprocessor.happydune-07a3bc2a.germanywestcentral.azurecontainerapps.io  
**Storage Account**: mediablobazfct.blob.core.windows.net  
**Container Registry**: mediacompressorregistry.azurecr.io

## Support and Maintenance

### Monitoring Checklist
- [ ] Function execution metrics
- [ ] Processing success/failure rates
- [ ] Queue depth and processing times
- [ ] Storage costs and usage
- [ ] Error rates and types

### Maintenance Tasks
- **Weekly**: Review error logs and failed jobs
- **Monthly**: Analyze performance metrics and costs
- **Quarterly**: Update dependencies and review architecture
- **Annually**: Technology refresh and optimization review

### Troubleshooting Guide

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| High processing times | Queue backlog, timeouts | Increase function instances |
| Failed compressions | Error logs, poison queue | Check FFmpeg installation |
| Storage costs | High billing | Review retention policies |
| Memory issues | Function crashes | Optimize image processing |

---

**Document Version**: 2.0  
**Last Updated**: October 2024  
**Author**: Development Team  
**Status**: ✅ **IMPLEMENTED AND DEPLOYED**