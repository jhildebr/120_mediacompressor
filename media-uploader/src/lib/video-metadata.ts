// Video metadata types
export interface VideoMetadata {
  duration: number;
  width: number;
  height: number;
  frameRate: number;
  bitrate: number;
  codec: string;
  format: string;
  fileSize: number;
  aspectRatio: string;
}

export interface ProcessingStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
  progress?: number;
  startTime?: Date;
  endTime?: Date;
}

export interface FileInfo {
  name: string;
  size: number;
  type: string;
  uploadTime: Date;
  originalUrl: string;
  processedUrl?: string;
  originalMetadata?: VideoMetadata;
  processedMetadata?: VideoMetadata;
  processingStatus: ProcessingStatus;
}

// Extract video metadata from file
export const extractVideoMetadata = (file: File): Promise<VideoMetadata> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    video.onloadedmetadata = () => {
      window.URL.revokeObjectURL(video.src);
      
      const metadata: VideoMetadata = {
        duration: video.duration,
        width: video.videoWidth,
        height: video.videoHeight,
        frameRate: 0, // Not available in browser
        bitrate: 0, // Not available in browser
        codec: 'Unknown', // Not available in browser
        format: file.type,
        fileSize: file.size,
        aspectRatio: `${video.videoWidth}:${video.videoHeight}`,
      };
      
      resolve(metadata);
    };
    
    video.onerror = () => {
      window.URL.revokeObjectURL(video.src);
      reject(new Error('Failed to load video metadata'));
    };
    
    video.src = URL.createObjectURL(file);
  });
};

// Format file size
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Format duration
export const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

// Get file extension
export const getFileExtension = (filename: string): string => {
  return filename.split('.').pop()?.toLowerCase() || '';
};

// Check if file is video
export const isVideoFile = (file: File): boolean => {
  return file.type.startsWith('video/');
};

// Check if file is image
export const isImageFile = (file: File): boolean => {
  return file.type.startsWith('image/');
};

// Generate compression ratio
export const getCompressionRatio = (originalSize: number, compressedSize: number): number => {
  return ((originalSize - compressedSize) / originalSize) * 100;
};
