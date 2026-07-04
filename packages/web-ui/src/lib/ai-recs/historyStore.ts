import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

// Server-side durable store for AI Recs history. Web-ui counterpart of the
// PyQt `AiRecsHistoryStore` (src/optimizer_v3/state/ai_recs_history/store.py):
// same `{ schema_version, records[] }` on-disk shape, but the record shape is
// the web-ui `AiRecsHistoryEntry` (camelCase) since the two stores are
// independent — the web-ui replicates the local-store behavior for its own UI.

export const SCHEMA_VERSION = 1;
const MAX_ENTRIES = 100;

export type AiRecsHistoryStatus = 'new' | 'applied' | 'dismissed';

export interface HistorySnapshotKpis {
  winRate: number;
  netLiquidity: number;
  maxDrawdown: number;
  profitFactor: number;
  entries: number;
}

export interface AiRecsHistoryEntry {
  id: string;
  createdAt: string;
  prompt: string;
  summary: string;
  diagnosis: string;
  recommendations: string;
  raw: string;
  strategyName?: string;
  status: AiRecsHistoryStatus;
  notes: string;
  snapshotKpis?: HistorySnapshotKpis;
}

export interface HistoryPayload {
  schema_version: number;
  records: AiRecsHistoryEntry[];
}

const VALID_STATUSES: AiRecsHistoryStatus[] = ['new', 'applied', 'dismissed'];

function isStatus(value: unknown): value is AiRecsHistoryStatus {
  return typeof value === 'string' && (VALID_STATUSES as string[]).includes(value);
}

function isSnapshotKpis(v: unknown): v is HistorySnapshotKpis {
  if (!v || typeof v !== 'object') return false;
  const k = v as Record<string, unknown>;
  return (
    typeof k.winRate === 'number' &&
    typeof k.netLiquidity === 'number' &&
    typeof k.maxDrawdown === 'number' &&
    typeof k.profitFactor === 'number' &&
    typeof k.entries === 'number'
  );
}

export function coerceEntry(raw: unknown): AiRecsHistoryEntry | null {
  if (!raw || typeof raw !== 'object') return null;
  const e = raw as Record<string, unknown>;
  if (typeof e.id !== 'string' || typeof e.createdAt !== 'string') return null;
  if (typeof e.prompt !== 'string') return null;
  if (typeof e.summary !== 'string') return null;
  if (typeof e.diagnosis !== 'string') return null;
  if (typeof e.recommendations !== 'string') return null;
  if (typeof e.raw !== 'string') return null;
  if (typeof e.notes !== 'string') return null;
  if (!isStatus(e.status)) return null;
  return {
    id: e.id,
    createdAt: e.createdAt,
    prompt: e.prompt,
    summary: e.summary,
    diagnosis: e.diagnosis,
    recommendations: e.recommendations,
    raw: e.raw,
    status: e.status,
    notes: e.notes,
    ...(typeof e.strategyName === 'string' ? { strategyName: e.strategyName } : {}),
    ...(isSnapshotKpis(e.snapshotKpis) ? { snapshotKpis: e.snapshotKpis } : {}),
  };
}

function storePath(): string {
  const override = process.env.BTC_AI_RECS_HISTORY_WEBUI_PATH;
  if (override && override.length > 0) return override;
  return join(homedir(), '.btc_trade_engine', 'ai_recs_history_webui.json');
}

let writeChain: Promise<void> = Promise.resolve();

export async function readRecords(): Promise<AiRecsHistoryEntry[]> {
  let text: string;
  try {
    text = await readFile(storePath(), 'utf-8');
  } catch {
    return [];
  }
  try {
    const parsed = JSON.parse(text) as unknown;
    const records = (parsed as HistoryPayload)?.records;
    if (!Array.isArray(records)) return [];
    return records
      .map(coerceEntry)
      .filter((e): e is AiRecsHistoryEntry => e !== null)
      .slice(0, MAX_ENTRIES);
  } catch {
    return [];
  }
}

// Serialize writes so concurrent requests can't interleave read-modify-write
// and clobber each other. Each write is a full atomic replace via temp+rename.
export function writeRecords(
  records: AiRecsHistoryEntry[],
): Promise<AiRecsHistoryEntry[]> {
  const clean = records
    .map(coerceEntry)
    .filter((e): e is AiRecsHistoryEntry => e !== null)
    .slice(0, MAX_ENTRIES);

  const task = writeChain.then(async () => {
    const path = storePath();
    await mkdir(dirname(path), { recursive: true, mode: 0o700 });
    const payload: HistoryPayload = {
      schema_version: SCHEMA_VERSION,
      records: clean,
    };
    const tmp = `${path}.${process.pid}.tmp`;
    await writeFile(tmp, JSON.stringify(payload, null, 2), { mode: 0o600 });
    await rename(tmp, path);
  });

  // Keep the chain alive even if this write throws.
  writeChain = task.catch(() => undefined);
  return task.then(() => clean);
}
