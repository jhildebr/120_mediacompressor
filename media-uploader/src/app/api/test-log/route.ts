import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  console.log('[test-log] This is a test log message from console.log');
  console.error('[test-log] This is a test error message from console.error');
  console.warn('[test-log] This is a test warning message from console.warn');
  console.info('[test-log] This is a test info message from console.info');

  return NextResponse.json({ message: 'Test logging complete' });
}