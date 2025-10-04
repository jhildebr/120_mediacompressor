import { NextRequest, NextResponse } from 'next/server';
import { BlobServiceClient } from '@azure/storage-blob';
import { listFiles, checkProcessedFile } from '@/lib/azure-storage';

export async function POST(request: NextRequest) {
  try {
    console.log('[clear-stuck] Starting removal of stuck files from uploads container');

    const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
    if (!connectionString) {
      throw new Error('AZURE_STORAGE_CONNECTION_STRING is not set');
    }

    const { searchParams } = new URL(request.url);
    const forceDelete = searchParams.get('force') === 'true';
    const olderThanMinutes = parseInt(searchParams.get('olderThan') || '60'); // Default: 1 hour

    const blobServiceClient = BlobServiceClient.fromConnectionString(connectionString);
    const uploadsContainer = blobServiceClient.getContainerClient('uploads');

    // Get all files in uploads container
    const uploadedFiles = await listFiles('uploads');
    console.log(`[clear-stuck] Found ${uploadedFiles.length} files in uploads container`);

    const cutoffTime = new Date(Date.now() - olderThanMinutes * 60 * 1000);
    console.log(`[clear-stuck] Looking for files older than ${olderThanMinutes} minutes (before ${cutoffTime.toISOString()})`);

    let removedCount = 0;
    let skippedCount = 0;

    for (const file of uploadedFiles) {
      const fileAge = file.lastModified ? new Date(file.lastModified) : new Date(0);
      const isOld = fileAge < cutoffTime;

      console.log(`[clear-stuck] Checking ${file.name} (uploaded: ${fileAge.toISOString()}, age: ${isOld ? 'old' : 'recent'})`);

      if (!isOld && !forceDelete) {
        console.log(`[clear-stuck] ⏭️ ${file.name} is too recent, skipping`);
        skippedCount++;
        continue;
      }

      // Check if this file has been processed
      const processedFile = await checkProcessedFile(file.name);

      if (processedFile) {
        console.log(`[clear-stuck] ✅ ${file.name} is processed, will be handled by cleanup endpoint`);
        skippedCount++;
        continue;
      }

      // This is a stuck file - old and not processed
      console.log(`[clear-stuck] 🗑️ ${file.name} appears stuck (old and unprocessed), removing...`);

      try {
        const blobClient = uploadsContainer.getBlobClient(file.name);
        await blobClient.delete();
        removedCount++;
        console.log(`[clear-stuck] ✅ Deleted stuck file ${file.name} from uploads container`);
      } catch (deleteError) {
        console.error(`[clear-stuck] ❌ Failed to delete ${file.name}:`, deleteError);
      }
    }

    console.log(`[clear-stuck] Clear stuck complete: ${removedCount} stuck files removed, ${skippedCount} files kept`);

    return NextResponse.json({
      success: true,
      message: `Clear stuck files complete`,
      stats: {
        totalFiles: uploadedFiles.length,
        removedFiles: removedCount,
        skippedFiles: skippedCount,
        cutoffTime: cutoffTime.toISOString(),
        olderThanMinutes
      }
    });

  } catch (error) {
    console.error('[clear-stuck] Error during clear stuck:', error);
    return NextResponse.json(
      { error: 'Failed to clear stuck files' },
      { status: 500 }
    );
  }
}