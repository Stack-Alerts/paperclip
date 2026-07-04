import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  readRecords,
  writeRecords,
  coerceEntry,
  SCHEMA_VERSION,
  type AiRecsHistoryEntry,
} from '../historyStore';

const ENV_KEY = 'BTC_AI_RECS_HISTORY_WEBUI_PATH';

function sample(overrides: Partial<AiRecsHistoryEntry> = {}): AiRecsHistoryEntry {
  return {
    id: 'rec-1',
    createdAt: '2026-07-04T12:00:00.000Z',
    prompt: 'p',
    summary: 's',
    diagnosis: 'd',
    recommendations: 'r',
    raw: 'raw',
    status: 'new',
    notes: '',
    ...overrides,
  };
}

describe('ai-recs historyStore', () => {
  let dir: string;
  const prevEnv = process.env[ENV_KEY];

  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ai-recs-store-'));
    process.env[ENV_KEY] = join(dir, 'history.json');
  });

  afterEach(async () => {
    if (prevEnv === undefined) delete process.env[ENV_KEY];
    else process.env[ENV_KEY] = prevEnv;
    await rm(dir, { recursive: true, force: true });
  });

  it('returns [] when the store file does not exist', async () => {
    expect(await readRecords()).toEqual([]);
  });

  it('round-trips records through write then read', async () => {
    const written = await writeRecords([sample({ id: 'a' }), sample({ id: 'b' })]);
    expect(written).toHaveLength(2);
    const read = await readRecords();
    expect(read.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('persists the { schema_version, records } envelope', async () => {
    await writeRecords([sample()]);
    const raw = JSON.parse(await readFile(process.env[ENV_KEY] as string, 'utf-8'));
    expect(raw.schema_version).toBe(SCHEMA_VERSION);
    expect(Array.isArray(raw.records)).toBe(true);
    expect(raw.records[0].id).toBe('rec-1');
  });

  it('drops malformed records on write', async () => {
    const written = await writeRecords([
      sample({ id: 'ok' }),
      { id: 'bad' } as unknown as AiRecsHistoryEntry,
      sample({ status: 'bogus' as AiRecsHistoryEntry['status'] }),
    ]);
    expect(written.map((r) => r.id)).toEqual(['ok']);
  });

  it('serializes concurrent writes without clobbering the file', async () => {
    await Promise.all([
      writeRecords([sample({ id: 'x' })]),
      writeRecords([sample({ id: 'y' })]),
      writeRecords([sample({ id: 'z' })]),
    ]);
    const read = await readRecords();
    expect(read).toHaveLength(1);
    expect(['x', 'y', 'z']).toContain(read[0].id);
  });

  it('coerceEntry rejects entries missing required fields', () => {
    expect(coerceEntry({ id: 'x' })).toBeNull();
    expect(coerceEntry(null)).toBeNull();
    expect(coerceEntry(sample())).not.toBeNull();
  });
});
