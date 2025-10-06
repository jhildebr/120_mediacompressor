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

    // Trigger processing directly via App Service B2
    const processorUrl = process.env.PROCESSOR_URL || 'https://mediaprocessor-b2.azurewebsites.net';
    console.log(`[upload] Triggering processing for: ${blobName} at ${processorUrl}`);

    const processResponse = await fetch(`${processorUrl}/api/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blob_name: blobName }),
    });

    const processResult = await processResponse.json();
    console.log(`[upload] Processing result:`, processResult);

    if (processResult.status !== 'success') {
      throw new Error(processResult.error || 'Processing failed');
    }

    return NextResponse.json({
      success: true,
      blobName,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      uploadTime: new Date().toISOString(),
      // Include processing result for immediate download
      processingResult: processResult.result,
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
