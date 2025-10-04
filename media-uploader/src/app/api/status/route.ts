import { NextRequest, NextResponse } from 'next/server';
import { getFileMetadata, checkProcessedFile } from '@/lib/azure-storage';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const blobName = searchParams.get('blobName');
    const includeHealth = searchParams.get('includeHealth');
    
    if (!blobName) {
      return NextResponse.json(
        { error: 'Blob name is required' },
        { status: 400 }
      );
    }
    
    // Check if processed file exists
    const processedMetadata = await checkProcessedFile(blobName);
    
    if (processedMetadata) {
      // Optional: include function health for debugging
      let health: any = undefined;
      if (includeHealth === '1') {
        try {
          const url = process.env.AZURE_FUNCTION_APP_URL || '';
          console.log(`[status] Checking function health at: ${url}`);
          if (url) {
            const res = await fetch(`${url}/api/health`, { cache: 'no-store' });
            console.log(`[status] Health check response status: ${res.status}`);
            if (res.ok) {
              health = await res.json();
              console.log(`[status] Health check response:`, health);
            } else {
              console.log(`[status] Health check failed with status: ${res.status}`);
            }
          } else {
            console.log(`[status] AZURE_FUNCTION_APP_URL not configured`);
          }
        } catch (error) {
          console.error(`[status] Health check error:`, error);
        }
      }

      return NextResponse.json({
        status: 'completed',
        message: 'File has been processed successfully',
        processedAt: processedMetadata.lastModified,
        downloadUrl: processedMetadata.url,
        health,
      });
    }
    
    // Check if original file still exists (processing might have failed)
    const originalMetadata = await getFileMetadata(blobName, 'uploads');

    if (originalMetadata) {
      console.log(`[status] File ${blobName} is still being processed. Upload time: ${originalMetadata.lastModified}`);
      return NextResponse.json({
        status: 'processing',
        message: 'File is being processed',
        uploadedAt: originalMetadata.lastModified,
      });
    }
    
    let health: any = undefined;
    if (includeHealth === '1') {
      try {
        const url = process.env.AZURE_FUNCTION_APP_URL || '';
        if (url) {
          const res = await fetch(`${url}/api/health`, { cache: 'no-store' });
          if (res.ok) health = await res.json();
        }
      } catch {}
    }

    return NextResponse.json({
      status: 'failed',
      message: 'File not found or processing failed',
      health,
    });
    
  } catch (error) {
    console.error('Status check error:', error);
    return NextResponse.json(
      { error: 'Failed to check status' },
      { status: 500 }
    );
  }
}
