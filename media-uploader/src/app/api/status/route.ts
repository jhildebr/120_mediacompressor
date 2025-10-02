import { NextRequest, NextResponse } from 'next/server';
import { getFileMetadata, checkProcessedFile } from '@/lib/azure-storage';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const blobName = searchParams.get('blobName');
    
    if (!blobName) {
      return NextResponse.json(
        { error: 'Blob name is required' },
        { status: 400 }
      );
    }
    
    // Check if processed file exists
    const processedMetadata = await checkProcessedFile(blobName);
    
    if (processedMetadata) {
      return NextResponse.json({
        status: 'completed',
        message: 'File has been processed successfully',
        processedAt: processedMetadata.lastModified,
        downloadUrl: processedMetadata.url,
      });
    }
    
    // Check if original file still exists (processing might have failed)
    const originalMetadata = await getFileMetadata(blobName, 'uploads');
    
    if (originalMetadata) {
      return NextResponse.json({
        status: 'processing',
        message: 'File is being processed',
        uploadedAt: originalMetadata.lastModified,
      });
    }
    
    return NextResponse.json({
      status: 'failed',
      message: 'File not found or processing failed',
    });
    
  } catch (error) {
    console.error('Status check error:', error);
    return NextResponse.json(
      { error: 'Failed to check status' },
      { status: 500 }
    );
  }
}
