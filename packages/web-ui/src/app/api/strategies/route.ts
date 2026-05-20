import { NextRequest, NextResponse } from 'next/server';

// This route proxies /api/strategies to the Python backend.
// The real strategy data lives in the strategy builder ORM DB at
// GET /strategy-builder/strategies on the Python API server.
// This proxy exists only for tooling that hits the Next.js origin directly.

const BACKEND = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';

async function proxy(req: NextRequest, path: string) {
  const backendUrl = `${BACKEND}${path}`;
  const headers: Record<string, string> = {};
  const auth = req.headers.get('authorization');
  if (auth) headers['Authorization'] = auth;
  headers['Content-Type'] = 'application/json';

  const body = req.method !== 'GET' && req.method !== 'HEAD'
    ? await req.text()
    : undefined;

  const res = await fetch(backendUrl, {
    method: req.method,
    headers,
    body,
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function GET(req: NextRequest) {
  return proxy(req, '/strategy-builder/strategies');
}

export async function POST(req: NextRequest) {
  return proxy(req, '/strategy-builder/strategies');
}
