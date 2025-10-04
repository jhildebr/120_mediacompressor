import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const functionUrl = process.env.AZURE_FUNCTION_APP_URL;

    if (!functionUrl) {
      return NextResponse.json({
        error: 'AZURE_FUNCTION_APP_URL not configured',
        configured: false
      });
    }

    console.log(`[check-function] Testing Azure Function at: ${functionUrl}`);

    // Test health endpoint
    let healthStatus = null;
    try {
      console.log(`[check-function] Checking health endpoint...`);
      const healthRes = await fetch(`${functionUrl}/api/health`, {
        cache: 'no-store',
        headers: {
          'User-Agent': 'MediaUploader/1.0'
        }
      });
      console.log(`[check-function] Health endpoint status: ${healthRes.status}`);

      if (healthRes.ok) {
        healthStatus = await healthRes.json();
        console.log(`[check-function] Health response:`, healthStatus);
      } else {
        const errorText = await healthRes.text();
        console.log(`[check-function] Health endpoint error: ${errorText}`);
        healthStatus = { error: `HTTP ${healthRes.status}: ${errorText}` };
      }
    } catch (error) {
      console.error(`[check-function] Health check failed:`, error);
      healthStatus = { error: error instanceof Error ? error.message : 'Unknown error' };
    }

    // Test if ffmpeg endpoint exists
    let ffmpegStatus = null;
    try {
      console.log(`[check-function] Checking ffmpeg capabilities...`);
      const ffmpegRes = await fetch(`${functionUrl}/api/ffmpeg-info`, {
        cache: 'no-store',
        headers: {
          'User-Agent': 'MediaUploader/1.0'
        }
      });
      console.log(`[check-function] FFmpeg endpoint status: ${ffmpegRes.status}`);

      if (ffmpegRes.ok) {
        ffmpegStatus = await ffmpegRes.json();
        console.log(`[check-function] FFmpeg response:`, ffmpegStatus);
      } else {
        const errorText = await ffmpegRes.text();
        console.log(`[check-function] FFmpeg endpoint error: ${errorText}`);
        ffmpegStatus = { error: `HTTP ${ffmpegRes.status}: ${errorText}` };
      }
    } catch (error) {
      console.error(`[check-function] FFmpeg check failed:`, error);
      ffmpegStatus = { error: error instanceof Error ? error.message : 'Unknown error' };
    }

    return NextResponse.json({
      functionUrl,
      configured: true,
      health: healthStatus,
      ffmpeg: ffmpegStatus,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[check-function] Error:', error);
    return NextResponse.json(
      { error: 'Failed to check Azure Function' },
      { status: 500 }
    );
  }
}