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
    
    // Get original file metadata
    const originalMetadata = await getFileMetadata(blobName, 'uploads');
    
    if (!originalMetadata) {
      return NextResponse.json(
        { error: 'Original file not found' },
        { status: 404 }
      );
    }
    
    // Check if processed file exists
    const processedMetadata = await checkProcessedFile(blobName);
    
    return NextResponse.json({
      original: originalMetadata,
      processed: processedMetadata,
      isProcessed: !!processedMetadata,
    });
    
  } catch (error) {
    console.error('Metadata error:', error);
    return NextResponse.json(
      { error: 'Failed to get metadata' },
      { status: 500 }
    );
  }
}
