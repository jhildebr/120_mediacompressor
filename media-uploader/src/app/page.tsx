'use client';

import { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import MetadataDisplay from '@/components/MetadataDisplay';
import { Upload, Zap } from 'lucide-react';

interface UploadResult {
  blobName: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadTime: string;
}

export default function Home() {
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  const handleUploadStart = () => {
    setUploadResult(null);
  };

  const handleUploadComplete = (result: UploadResult) => {
    setUploadResult(result);
  };

  const handleNewUpload = () => {
    setUploadResult(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Zap className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">
                Media Compressor
              </h1>
            </div>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
              Azure Functions
            </span>
          </div>
          <p className="mt-2 text-gray-600">
            Upload videos and images to automatically compress them using Azure Functions with FFmpeg
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!uploadResult ? (
          <div className="space-y-8">
            {/* Upload Section */}
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-4">
                <Upload className="h-6 w-6 text-gray-600" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Upload Media File
                </h2>
              </div>
              <FileUpload 
                onUploadStart={handleUploadStart}
                onUploadComplete={handleUploadComplete}
              />
            </div>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Zap className="h-5 w-5 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">Automatic Processing</h3>
                </div>
                <p className="text-gray-600 text-sm">
                  Files are automatically queued and processed using Azure Functions with FFmpeg for optimal compression.
                </p>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-900">Real-time Updates</h3>
                </div>
                <p className="text-gray-600 text-sm">
                  Monitor processing status in real-time and get notified when your compressed file is ready.
                </p>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <svg className="h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-900">Detailed Metadata</h3>
                </div>
                <p className="text-gray-600 text-sm">
                  View comprehensive file comparison including compression ratios, and download the optimized compressed file.
                </p>
              </div>
            </div>

            {/* Supported Formats */}
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Supported Formats</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Video Formats</h4>
                  <div className="flex flex-wrap gap-2">
                    {['MP4', 'AVI', 'MOV', 'WMV', 'FLV', 'WebM'].map(format => (
                      <span key={format} className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                        {format}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Image Formats</h4>
                  <div className="flex flex-wrap gap-2">
                    {['JPG', 'PNG', 'GIF', 'BMP', 'WebP'].map(format => (
                      <span key={format} className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
                        {format}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Success Message */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                  <span className="text-green-700 font-medium">
                    File uploaded successfully! Processing will begin automatically.
                  </span>
                </div>
                <button
                  onClick={handleNewUpload}
                  className="text-green-600 hover:text-green-800 text-sm font-medium"
                >
                  Upload Another File
                </button>
              </div>
            </div>

            {/* Metadata Display */}
            <MetadataDisplay
              blobName={uploadResult.blobName}
              fileName={uploadResult.fileName}
              fileSize={uploadResult.fileSize}
              fileType={uploadResult.fileType}
              uploadTime={uploadResult.uploadTime}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>Powered by Azure Functions, Azure Blob Storage, and FFmpeg</p>
            <p className="mt-1">Built with Next.js and TypeScript</p>
          </div>
        </div>
      </footer>
    </div>
  );
}