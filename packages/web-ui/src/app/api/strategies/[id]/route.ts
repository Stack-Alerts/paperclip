import { NextRequest, NextResponse } from 'next/server';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const DATA_DIR = join(process.cwd(), '.strategy-data');
const DATA_FILE = join(DATA_DIR, 'strategies.json');

function ensureDir() {
  if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true });
  }
}

function loadStrategies(): Record<string, unknown>[] {
  ensureDir();
  if (!existsSync(DATA_FILE)) return [];
  try {
    return JSON.parse(readFileSync(DATA_FILE, 'utf-8'));
  } catch {
    return [];
  }
}

function saveStrategies(strategies: Record<string, unknown>[]) {
  ensureDir();
  writeFileSync(DATA_FILE, JSON.stringify(strategies, null, 2));
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const strategies = loadStrategies();
  const strategy = strategies.find((s) => s.id === id);
  if (!strategy) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  return NextResponse.json(strategy);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.json();
  const strategies = loadStrategies();
  const index = strategies.findIndex((s) => s.id === id);

  if (index === -1) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const updated = {
    ...strategies[index],
    ...body,
    id,
    updatedAt: new Date().toISOString(),
  };

  strategies[index] = updated;
  saveStrategies(strategies);
  return NextResponse.json(updated);
}

export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const strategies = loadStrategies();
  const filtered = strategies.filter((s) => s.id !== id);
  saveStrategies(filtered);
  return NextResponse.json({ deleted: true });
}
