#!/bin/bash

# Media Compressor Web App Setup Script
set -e

echo "🎬 Media Compressor Web App Setup"
echo "=================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create .env.local from example
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from template..."
    cp env.example .env.local
    echo "✅ Created .env.local"
    echo ""
    echo "🔧 Please update .env.local with your Azure Storage credentials:"
    echo "   - AZURE_STORAGE_CONNECTION_STRING"
    echo "   - AZURE_STORAGE_ACCOUNT_KEY"
    echo ""
    echo "💡 To get your connection string, run:"
    echo "   az storage account show-connection-string \\"
    echo "     --name mediablobazfct \\"
    echo "     --resource-group rg-11-video-compressor-az-function \\"
    echo "     --query connectionString --output tsv"
    echo ""
else
    echo "✅ .env.local already exists"
fi

# Build the application
echo "🔨 Building the application..."
npm run build

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the development server:"
echo "   npm run dev"
echo ""
echo "🌐 Then open http://localhost:3000 in your browser"
echo ""
echo "📚 For more information, see README.md"
