import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const messages = [];

  if (!body.name || body.name.trim() === '') {
    messages.push({
      id: 'val-name',
      level: 'ERROR',
      text: 'Strategy name is required',
      code: 'MISSING_NAME',
      timestamp: new Date().toISOString(),
    });
  }

  if (!body.blocks || body.blocks.length === 0) {
    messages.push({
      id: 'val-blocks',
      level: 'WARNING',
      text: 'Strategy has no building blocks',
      code: 'NO_BLOCKS',
      timestamp: new Date().toISOString(),
    });
  }

  return NextResponse.json({ messages, valid: messages.filter((m) => m.level === 'ERROR').length === 0 });
}
