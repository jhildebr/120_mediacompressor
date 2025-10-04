import { NextRequest, NextResponse } from 'next/server';
import { BlobServiceClient } from '@azure/storage-blob';
import { listFiles, checkProcessedFile } from '@/lib/azure-storage';

export async function POST(request: NextRequest) {
  try {
    console.log('[cleanup] Starting cleanup of processed files from uploads container');

    const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
    if (!connectionString) {
      throw new Error('AZURE_STORAGE_CONNECTION_STRING is not set');
    }

    const blobServiceClient = BlobServiceClient.fromConnectionString(connectionString);
    const uploadsContainer = blobServiceClient.getContainerClient('uploads');

    // Get all files in uploads container
    const uploadedFiles = await listFiles('uploads');
    console.log(`[cleanup] Found ${uploadedFiles.length} files in uploads container`);

    let cleanedCount = 0;
    let skippedCount = 0;

    for (const file of uploadedFiles) {
      console.log(`[cleanup] Checking if ${file.name} has been processed...`);

      // Check if this file has been processed
      const processedFile = await checkProcessedFile(file.name);

      if (processedFile) {
        console.log(`[cleanup] ✅ ${file.name} found in processed container, removing from uploads...`);

        try {
          const blobClient = uploadsContainer.getBlobClient(file.name);
          await blobClient.delete();
          cleanedCount++;
          console.log(`[cleanup] ✅ Deleted ${file.name} from uploads container`);
        } catch (deleteError) {
          console.error(`[cleanup] ❌ Failed to delete ${file.name}:`, deleteError);
        }
      } else {
        console.log(`[cleanup] ⏳ ${file.name} not yet processed, keeping in uploads`);
        skippedCount++;
      }
    }

    console.log(`[cleanup] Cleanup complete: ${cleanedCount} files removed, ${skippedCount} files kept`);

    return NextResponse.json({
      success: true,
      message: `Cleanup complete`,
      stats: {
        totalFiles: uploadedFiles.length,
        cleanedFiles: cleanedCount,
        skippedFiles: skippedCount
      }
    });

  } catch (error) {
    console.error('[cleanup] Error during cleanup:', error);
    return NextResponse.json(
      { error: 'Failed to perform cleanup' },
      { status: 500 }
    );
  }
}