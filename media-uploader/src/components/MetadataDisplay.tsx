'use client';

import { useState, useEffect, useCallback } from 'react';
import { Download, RefreshCw, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { formatFileSize, getCompressionRatio } from '@/lib/video-metadata';

interface MetadataDisplayProps {
  blobName: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadTime: string;
}

interface FileMetadata {
  name: string;
  size: number;
  contentType: string;
  lastModified: string;
  url: string;
}

interface StatusResponse {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  processedAt?: string;
  downloadUrl?: string;
  health?: {
    bundle_version?: string;
    build_time?: string;
    host_uptime_seconds?: number;
  };
}

export default function MetadataDisplay({ 
  blobName, 
  fileName, 
  fileSize, 
  fileType, 
  uploadTime 
}: MetadataDisplayProps) {
  const [metadata, setMetadata] = useState<{
    original?: FileMetadata;
    processed?: FileMetadata;
  } | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetadata = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/metadata?blobName=${encodeURIComponent(blobName)}`);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch metadata');
      }
      
      setMetadata(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metadata');
    } finally {
      setLoading(false);
    }
  }, [blobName]);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/status?blobName=${encodeURIComponent(blobName)}&includeHealth=1`, { cache: 'no-store' });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch status');
      }
      
      setStatus(data);
      // If processing just completed and we don't yet have processed metadata,
      // fetch metadata so the table and download link appear immediately.
      if (data?.status === 'completed' && !metadata?.processed) {
        await fetchMetadata();
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }, [blobName, metadata?.processed, fetchMetadata]);

  useEffect(() => {
    fetchMetadata();
    fetchStatus();
    
    // Poll for status updates every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [blobName, fetchMetadata, fetchStatus]);

  const getStatusIcon = () => {
    switch (status?.status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'processing':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusColor = () => {
    switch (status?.status) {
      case 'completed':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'processing':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'failed':
        return 'text-red-700 bg-red-50 border-red-200';
      default:
        return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    }
  };

  if (loading) {
    return (
      <div className="w-full max-w-4xl mx-auto mt-8">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-4xl mx-auto mt-8 p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
          <button 
            onClick={fetchMetadata}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  const compressionRatio = metadata?.original && metadata?.processed 
    ? getCompressionRatio(metadata.original.size, metadata.processed.size)
    : 0;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 space-y-6">
      {/* Status */}
      <div className={`p-4 rounded-lg border ${getStatusColor()}`}>
        <div className="flex items-center space-x-2">
          {getStatusIcon()}
          <span className="font-medium">{status?.message || 'Processing...'}</span>
          <button 
            onClick={fetchStatus}
            className="ml-auto hover:opacity-75"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        {status?.health && (
          <div className="mt-3 text-xs text-gray-600 grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
              <span className="font-medium">Bundle:</span> {status.health.bundle_version}
            </div>
            <div>
              <span className="font-medium">Build:</span> {status.health.build_time}
            </div>
            <div>
              <span className="font-medium">Uptime:</span> {status.health.host_uptime_seconds}s
            </div>
          </div>
        )}
      </div>

      {/* File Information */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">File Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="text-sm text-gray-500">Original Name:</span>
            <p className="font-medium">{fileName}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">File Type:</span>
            <p className="font-medium">{fileType}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">Upload Time:</span>
            <p className="font-medium">{new Date(uploadTime).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">Original Size:</span>
            <p className="font-medium">{formatFileSize(fileSize)}</p>
          </div>
        </div>
      </div>

      {/* Original File Details */}
      {metadata?.original && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Original File Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500">Size:</span>
              <p className="font-medium">{formatFileSize(metadata.original.size)}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Content Type:</span>
              <p className="font-medium">{metadata.original.contentType}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Last Modified:</span>
              <p className="font-medium">{new Date(metadata.original.lastModified).toLocaleString()}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Format:</span>
              <p className="font-medium">{metadata.original.contentType.split('/')[1]?.toUpperCase()}</p>
            </div>
          </div>
          <div className="mt-4">
            <span className="text-sm text-gray-500">Original file preserved for reference</span>
          </div>
        </div>
      )}

      {/* Processed File Details */}
      {metadata?.processed && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">✅ Compressed File Ready</h3>
            <a
              href={metadata.processed.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Download className="h-4 w-4 mr-2" />
              Download Compressed File
            </a>
          </div>
          
          {compressionRatio > 0 && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-green-700 font-medium">Compression Ratio:</span>
                <span className="text-green-700 font-bold">{compressionRatio.toFixed(1)}% smaller</span>
              </div>
              <div className="mt-2 w-full bg-green-200 rounded-full h-2">
                <div 
                  className="bg-green-600 h-2 rounded-full" 
                  style={{ width: `${compressionRatio}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Metadata Comparison Table */}
      {metadata?.original && metadata?.processed && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">📊 File Comparison</h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Metadata</th>
                  <th className="text-left py-3 px-4 font-medium text-blue-700">Original File</th>
                  <th className="text-left py-3 px-4 font-medium text-green-700">Compressed File</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">File Size</td>
                  <td className="py-3 px-4 text-blue-600">{formatFileSize(metadata.original.size)}</td>
                  <td className="py-3 px-4 text-green-600">{formatFileSize(metadata.processed.size)}</td>
                </tr>
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Format</td>
                  <td className="py-3 px-4 text-blue-600">{metadata.original.contentType.split('/')[1]?.toUpperCase()}</td>
                  <td className="py-3 px-4 text-green-600">{metadata.processed.contentType.split('/')[1]?.toUpperCase()}</td>
                </tr>
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Content Type</td>
                  <td className="py-3 px-4 text-blue-600">{metadata.original.contentType}</td>
                  <td className="py-3 px-4 text-green-600">{metadata.processed.contentType}</td>
                </tr>
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Last Modified</td>
                  <td className="py-3 px-4 text-blue-600">{new Date(metadata.original.lastModified).toLocaleString()}</td>
                  <td className="py-3 px-4 text-green-600">{new Date(metadata.processed.lastModified).toLocaleString()}</td>
                </tr>
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">File Name</td>
                  <td className="py-3 px-4 text-blue-600">{metadata.original.name}</td>
                  <td className="py-3 px-4 text-green-600">{metadata.processed.name}</td>
                </tr>
                {compressionRatio > 0 && (
                  <tr className="border-b bg-green-50">
                    <td className="py-3 px-4 font-medium">Compression Ratio</td>
                    <td className="py-3 px-4 text-blue-600">-</td>
                    <td className="py-3 px-4 text-green-600 font-bold">{compressionRatio.toFixed(1)}% smaller</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Processing Instructions */}
      {status?.status === 'pending' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Processing Status</h4>
          <p className="text-blue-700 text-sm">
            Your file has been uploaded successfully and is queued for processing. 
            The Azure Function will automatically compress your media file. 
            This page will update automatically when processing is complete.
          </p>
        </div>
      )}
    </div>
  );
}
