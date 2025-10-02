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
  await blockBlobClient.uploadData(file);
  
  return blobName;
};

// Get file metadata from Azure Blob Storage
export const getFileMetadata = async (blobName: string, containerName: string = 'uploads') => {
  const blobServiceClient = getBlobServiceClient();
  const containerClient = blobServiceClient.getContainerClient(containerName);
  const blobClient = containerClient.getBlobClient(blobName);
  
  try {
    const properties = await blobClient.getProperties();
    return {
      name: blobName,
      size: properties.contentLength,
      contentType: properties.contentType,
      lastModified: properties.lastModified,
      etag: properties.etag,
      url: await generateSasToken(blobName, containerName),
    };
  } catch (error) {
    console.error('Error getting file metadata:', error);
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
  const processedName = originalBlobName.replace(/^upload-/, 'processed-');
  const processedMetadata = await getFileMetadata(processedName, 'processed');
  return processedMetadata;
};
