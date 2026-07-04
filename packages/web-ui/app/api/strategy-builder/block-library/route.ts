// BTCAAAAA-38726 — real block-library catalog endpoint.
//
// The AI Recommendations "AI Request" tab renders an "AVAILABLE BUILDING
// BLOCKS" section that fetches `/api/strategy-builder/block-library`. The
// route never existed, so the fetch 404'd and the section spun forever on
// "Loading block catalog…". This serves the same canonical catalog the
// Strategy Builder already loads from `public/block-library.json`
// (`{ blocks: BlockDefinition[] }`), so both surfaces stay in sync from one
// source of truth.

import { readFile } from 'node:fs/promises';
import path from 'node:path';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface BlockCatalog {
  blocks: unknown[];
}

let cache: BlockCatalog | null = null;

async function loadCatalog(): Promise<BlockCatalog> {
  if (cache) return cache;
  const file = path.join(process.cwd(), 'public', 'block-library.json');
  const raw = await readFile(file, 'utf8');
  const parsed = JSON.parse(raw) as unknown;
  const blocks =
    parsed && typeof parsed === 'object' && Array.isArray((parsed as { blocks?: unknown }).blocks)
      ? (parsed as { blocks: unknown[] }).blocks
      : [];
  cache = { blocks };
  return cache;
}

export async function GET(): Promise<Response> {
  try {
    const catalog = await loadCatalog();
    return Response.json(catalog);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load block library.';
    return Response.json({ blocks: [], error: message }, { status: 500 });
  }
}
