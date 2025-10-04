import { NextRequest, NextResponse } from 'next/server';
import { listFiles } from '@/lib/azure-storage';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const container = searchParams.get('container') || 'uploads';

    console.log(`[list-files] Listing files in ${container} container`);

    const files = await listFiles(container);

    console.log(`[list-files] Found ${files.length} files in ${container} container`);

    return NextResponse.json({
      success: true,
      container,
      count: files.length,
      files: files.map(file => ({
        name: file.name,
        size: file.size,
        contentType: file.contentType,
        lastModified: file.lastModified,
        ageMinutes: file.lastModified ? Math.round((Date.now() - new Date(file.lastModified).getTime()) / (1000 * 60)) : null
      }))
    });

  } catch (error) {
    console.error('[list-files] Error listing files:', error);
    return NextResponse.json(
      { error: 'Failed to list files' },
      { status: 500 }
    );
  }
}