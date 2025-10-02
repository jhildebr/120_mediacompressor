# Media Compressor Web App

A Next.js application for uploading and compressing media files using Azure Functions with FFmpeg.

## Features

- 🎬 **Video & Image Upload**: Support for MP4, AVI, MOV, WMV, FLV, WebM, JPG, PNG, GIF, BMP, WebP
- ⚡ **Automatic Processing**: Files are automatically queued and processed using Azure Functions
- 📊 **Real-time Status**: Monitor processing status with live updates
- 📋 **Detailed Metadata**: View comprehensive file information including dimensions, codecs, and compression ratios
- 🔗 **Download Links**: Secure SAS token-based download links for both original and processed files
- 🎨 **Modern UI**: Built with Tailwind CSS and responsive design

## Prerequisites

- Node.js 18+ 
- Azure Storage Account with Blob Storage
- Azure Function App with media compression functions deployed
- Azure Storage connection string and account key

## Setup

1. **Clone and Install Dependencies**
   ```bash
   cd media-uploader
   npm install
   ```

2. **Environment Configuration**
   
   Copy `env.example` to `.env.local` and configure:
   ```bash
   cp env.example .env.local
   ```
   
   Update the following variables in `.env.local`:
   ```env
   # Azure Storage Configuration
   AZURE_STORAGE_ACCOUNT_NAME=mediablobazfct
   AZURE_STORAGE_ACCOUNT_KEY=your_storage_account_key_here
   AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here
   
   # Azure Function App URL
   AZURE_FUNCTION_APP_URL=https://mediaprocessor.happydune-07a3bc2a.germanywestcentral.azurecontainerapps.io
   ```

3. **Get Azure Storage Credentials**
   
   Run this command to get your storage connection string:
   ```bash
   az storage account show-connection-string \
     --name mediablobazfct \
     --resource-group rg-11-video-compressor-az-function \
     --query connectionString --output tsv
   ```

4. **Development Server**
   ```bash
   npm run dev
   ```
   
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## Architecture

### Frontend (Next.js)
- **Upload Component**: Drag-and-drop file upload with validation
- **Metadata Display**: Real-time processing status and file information
- **API Routes**: Server-side endpoints for file operations

### Backend Integration
- **Azure Blob Storage**: File storage and SAS token generation
- **Azure Functions**: Automatic media processing with FFmpeg
- **Real-time Updates**: Polling-based status updates

### File Flow
1. User uploads file via web interface
2. File is stored in Azure Blob Storage `uploads` container
3. Azure Function is triggered via blob trigger
4. File is processed using FFmpeg
5. Compressed file is stored in `processed` container
6. Web app polls for completion and displays results

## API Endpoints

### `POST /api/upload`
Uploads a file to Azure Blob Storage.

**Request**: FormData with `file` field
**Response**: Upload result with blob name and metadata

### `GET /api/metadata?blobName=<name>`
Retrieves metadata for original and processed files.

**Response**: File metadata including URLs and properties

### `GET /api/status?blobName=<name>`
Checks processing status of a file.

**Response**: Current processing status and completion info

## File Validation

- **Supported Formats**: MP4, AVI, MOV, WMV, FLV, WebM, JPG, PNG, GIF, BMP, WebP
- **Maximum Size**: 100MB per file
- **Content Validation**: File type verification based on MIME type

## Security Features

- **SAS Tokens**: Time-limited access tokens for file downloads
- **File Validation**: Server-side file type and size validation
- **Secure Storage**: Azure Blob Storage with private containers

## Deployment

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm start
```

### Environment Variables for Production
Ensure all environment variables are set in your production environment:
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_FUNCTION_APP_URL`

## Troubleshooting

### Common Issues

1. **Upload Fails**: Check Azure Storage connection string and permissions
2. **Processing Stuck**: Verify Azure Function App is running and has proper blob triggers
3. **Download Links Expire**: SAS tokens expire after 1 hour, refresh the page

### Debug Mode
Enable debug logging by setting:
```env
NODE_ENV=development
```

## Technologies Used

- **Frontend**: Next.js 15, React 18, TypeScript, Tailwind CSS
- **Backend**: Azure Functions, Azure Blob Storage
- **Media Processing**: FFmpeg
- **UI Components**: Lucide React icons
- **File Upload**: React Dropzone

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details.