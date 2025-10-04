import { NextRequest, NextResponse } from 'next/server';
import { uploadFile } from '@/lib/azure-storage';
import { QueueServiceClient } from '@azure/storage-queue';

// Add CORS headers
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    console.log('Upload API called');
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }
    
    // Validate file type
    const allowedTypes = [
      'video/mp4',
      'video/avi',
      'video/mov',
      'video/wmv',
      'video/flv',
      'video/webm',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/bmp',
      'image/webp'
    ];
    
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: 'Unsupported file type' },
        { status: 400 }
      );
    }
    
    // Check file size (max 100MB)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: 'File size too large. Maximum size is 100MB.' },
        { status: 400 }
      );
    }
    
    // Upload file to Azure Blob Storage
    console.log(`[upload] Starting upload for file: ${file.name} (${file.size} bytes, ${file.type})`);
    const blobName = await uploadFile(file);
    console.log(`[upload] File uploaded successfully with blob name: ${blobName}`);

    // Enqueue processing job to ensure processing starts
    const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
    if (!connectionString) {
      throw new Error('AZURE_STORAGE_CONNECTION_STRING is not set');
    }

    console.log(`[upload] Creating queue service and sending message for: ${blobName}`);
    const queueService = QueueServiceClient.fromConnectionString(connectionString);
    const queueClient = queueService.getQueueClient('media-processing-queue');
    await queueClient.createIfNotExists();

    const queueMessage = {
      blob_name: blobName,
      file_size: file.size,
      priority: 'normal',
      timestamp: new Date().toISOString(),
      retry_count: 0,
    };

    console.log(`[upload] Sending queue message:`, queueMessage);
    await queueClient.sendMessage(JSON.stringify(queueMessage));
    console.log(`[upload] Queue message sent successfully for: ${blobName}`);
    
    return NextResponse.json({
      success: true,
      blobName,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      uploadTime: new Date().toISOString(),
    }, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
    
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Failed to upload file' },
      { 
        status: 500,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      }
    );
  }
}
