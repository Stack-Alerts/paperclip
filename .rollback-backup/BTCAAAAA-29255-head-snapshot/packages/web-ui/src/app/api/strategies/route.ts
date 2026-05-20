import { NextRequest, NextResponse } from 'next/server';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { randomUUID } from 'crypto';

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

export async function GET() {
  const strategies = loadStrategies();
  return NextResponse.json(strategies);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const strategies = loadStrategies();

  const now = new Date().toISOString();
  const id = randomUUID();
  const newStrategy = {
    name: body.name || 'New Strategy',
    description: body.description || '',
    status: 'DRAFT',
    strategyType: body.strategyType || 'Bullish',
    blocks: [],
    settings: {
      timeframe: '1h',
      targetMarket: 'BTC/USDT',
      riskParameters: null,
      strategyExits: [],
    },
    validationStatus: null,
    ...body,
    id,
    createdAt: now,
    updatedAt: now,
  };

  strategies.push(newStrategy);
  saveStrategies(strategies);
  return NextResponse.json(newStrategy, { status: 201 });
}
