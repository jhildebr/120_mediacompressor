import { BlobServiceClient, BlobSASPermissions } from '@azure/storage-blob';

// Initialize Azure Blob Storage client
const getBlobServiceClient = () => {
  const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
  if (!connectionString) {
    throw new Error('AZURE_STORAGE_CONNECTION_STRING environment variable is not set');
  }
  return BlobServiceClient.fromConnectionString(connectionString);
};

// Generate SAS token for secure access
export const generateSasToken = async (blobName: string, containerName: string = 'uploads') => {
  const blobServiceClient = getBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);
  const blobClient = containerClient.getBlobClient(blobName);
  
  // Generate SAS token valid for 1 hour
  const expiresOn = new Date(Date.now() + 60 * 60 * 1000);
  const permissions = BlobSASPermissions.parse('r'); // Read permission only
  
  const sasToken = await blobClient.generateSasUrl({
    permissions,
    expiresOn,
  });
  
  return sasToken;
};

// Upload file to Azure Blob Storage
export const uploadFile = async (file: File, containerName: string = 'uploads'): Promise<string> => {
  const blobServiceClient = getBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);
  
  // Create container if it doesn't exist
  await containerClient.createIfNotExists();
  
  // Generate unique blob name
  const timestamp = Date.now();
  const fileExtension = file.name.split('.').pop();
  const blobName = `upload-${timestamp}.${fileExtension}`;
  
  const blockBlobClient = containerClient.getBlockBlobClient(blobName);
  
  // Upload file
  const arrayBuffer = await file.arrayBuffer();
  await blockBlobClient.uploadData(arrayBuffer);
  
  return blobName;
};

// Get file metadata from Azure Blob Storage
export const getFileMetadata = async (blobName: string, containerName: string = 'uploads') => {
  const blobServiceClient = getBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);
  const blobClient = containerClient.getBlobClient(blobName);

  try {
    console.log(`[getFileMetadata] Attempting to get metadata for: ${blobName} in container: ${containerName}`);
    const properties = await blobClient.getProperties();
    console.log(`[getFileMetadata] Successfully retrieved metadata for: ${blobName}`);
    return {
      name: blobName,
      size: properties.contentLength,
      contentType: properties.contentType,
      lastModified: properties.lastModified,
      etag: properties.etag,
      url: await generateSasToken(blobName, containerName),
    };
  } catch (error) {
    console.error(`[getFileMetadata] Error getting metadata for blob: ${blobName} in container: ${containerName}`, error);
    if (error instanceof Error) {
      console.error(`[getFileMetadata] Error name: ${error.name}, message: ${error.message}`);
    }
    return null;
  }
};

// List files in container
export const listFiles = async (containerName: string = 'uploads') => {
  const blobServiceClient = getBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);
  
  const files = [];
  for await (const blob of containerClient.listBlobsFlat()) {
    files.push({
      name: blob.name,
      size: blob.properties.contentLength,
      contentType: blob.properties.contentType,
      lastModified: blob.properties.lastModified,
      etag: blob.properties.etag,
    });
  }
  
  return files;
};

// Check if processed file exists
export const checkProcessedFile = async (originalBlobName: string) => {
  // 1) Preferred pattern: "processed-<timestamp>.<ext>"
  const processedName = originalBlobName.replace(/^upload-/, 'processed-');
  // Also try a WebP variant in case the image was converted (e.g., GIF -> WebP)
  const processedWebp = processedName.replace(/\.[^/.]+$/, '.webp');
  const originalWebp = originalBlobName.replace(/\.[^/.]+$/, '.webp');
  const tryNames = [processedName, processedWebp, originalBlobName, originalWebp];

  // TEMP DEBUG: log which names we are checking
  // Remove after verifying end-to-end
  try {
    // eslint-disable-next-line no-console
    console.debug('[checkProcessedFile] variants', { originalBlobName, tryNames });
  } catch {}

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  // Retry a few times to absorb transient 404 right after completion
  for (let attempt = 0; attempt < 4; attempt++) {
    console.log(`[checkProcessedFile] Attempt ${attempt + 1}/4 for originalBlobName: ${originalBlobName}`);
    // Try both naming patterns per attempt
    for (const name of tryNames) {
      console.log(`[checkProcessedFile] Trying blob name: ${name} in 'processed' container`);
      const meta = await getFileMetadata(name, 'processed');
      if (meta) {
        console.log(`[checkProcessedFile] SUCCESS: Found processed file: ${name}`);
        return meta;
      } else {
        console.log(`[checkProcessedFile] Not found: ${name}`);
      }
    }
    // Backoff: 0.5s, 1s, 2s
    if (attempt < 3) {
      const waitTime = 500 * Math.pow(2, attempt);
      console.log(`[checkProcessedFile] Waiting ${waitTime}ms before next attempt...`);
      await sleep(waitTime);
    }
  }

  return null;
};
