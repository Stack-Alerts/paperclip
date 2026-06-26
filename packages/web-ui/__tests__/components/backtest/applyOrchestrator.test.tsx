// Unit tests for the AI-recommendations apply orchestrator
// (BTCAAAAA-38462, Stream 1). Covers the 5 acceptance criteria:
//
//   AC1: Toggle ON visibly changes strategy params.
//   AC2: Toggle OFF restores pre-apply snapshot.
//   AC3: History panel shows Applied/Dismissed badge within 1s.
//   AC4: No 404s in dev server console (orchestrator posts to
//        /api/ai/auto-apply with the expected shape; the panel wires the
//        fetch result so a 404 would surface here).
//   AC5: `pnpm test applyOrchestrator` passes — i.e. these tests pass
//        under the project's jest config.

import {
  buildApplyRequest,
  executeApply,
  parseApplyResponse,
  rollbackTransitions,
  type ParsedRecLike,
} from '@/components/backtest/ai-recommendations/applyOrchestrator';
import type { Strategy } from '@/lib/strategy-builder/types';

function makeRec(overrides: Partial<ParsedRecLike> = {}): ParsedRecLike {
  return {
    id: 'rec-1',
    type: 'ADJUST_PARAM',
    raw: 'raw text',
    block: 'block-x',
    signal: 'sig-y',
    parameter: 'riskParameters.maxLossPerTrade',
    suggestedValue: '3',
    ...overrides,
  };
}

function makeStrategy(overrides: Partial<Strategy> = {}): Strategy {
  return {
    id: 's1',
    name: 'Test Strategy',
    description: 'desc',
    status: 'draft',
    strategyType: 'Bullish',
    blocks: [],
    settings: {
      timeframe: '1h',
      targetMarket: 'BTC/USD',
      riskParameters: { maxLossPerTrade: 2, maxDrawdown: 10, maxAllocation: 25 },
    },
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  } as Strategy;
}

function makeResponse(
  body: unknown,
  init: { status?: number; ok?: boolean } = {},
): Response {
  const status = init.status ?? 200;
  const ok = init.ok ?? (status >= 200 && status < 300);
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ─── Pure helpers ───────────────────────────────────────────────────────

describe('buildApplyRequest', () => {
  it('POSTs to /api/ai/auto-apply with the strategy and rec payload', () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const { url, init } = buildApplyRequest(rec, strategy, undefined);
    expect(url).toBe('/api/ai/auto-apply');
    expect(init.method).toBe('POST');
    const headers = init.headers as Record<string, string>;
    expect(headers['content-type']).toBe('application/json');
    expect(headers['authorization']).toBeUndefined();

    const body = JSON.parse(init.body as string);
    expect(body.strategyId).toBe('s1');
    expect(body.strategy).toEqual(strategy);
    expect(body.recs).toHaveLength(1);
    expect(body.recs[0]).toEqual({
      rec_id: 'rec-1',
      type: 'ADJUST_PARAM',
      raw: 'raw text',
      block: 'block-x',
      signal: 'sig-y',
      parameter: 'riskParameters.maxLossPerTrade',
      suggestedValue: '3',
    });
    expect(body.optInDestructiveIds).toBeNull();
  });

  it('attaches the Bearer token when present', () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const { init } = buildApplyRequest(rec, strategy, 'tok-123');
    const headers = init.headers as Record<string, string>;
    expect(headers['authorization']).toBe('Bearer tok-123');
  });

  it('omits optional rec fields when not set', () => {
    const rec: ParsedRecLike = { id: 'rec-min', type: 'ADD_SIGNAL' };
    const strategy = makeStrategy();
    const { init } = buildApplyRequest(rec, strategy, undefined);
    const body = JSON.parse(init.body as string);
    expect(body.recs[0]).toEqual({ rec_id: 'rec-min', type: 'ADD_SIGNAL' });
  });
});

describe('parseApplyResponse', () => {
  it('returns ok=true when both response.ok and data.ok are true', () => {
    const strategy = makeStrategy();
    const res = makeResponse({ ok: true, strategy }, { status: 200 });
    const parsed = parseApplyResponse(res, { ok: true, strategy });
    expect(parsed.ok).toBe(true);
    expect(parsed.status).toBe(200);
    expect(parsed.strategy).toBeDefined();
  });

  it('returns ok=false and surfaces the server error when present', () => {
    const res = makeResponse({}, { status: 422, ok: false });
    const parsed = parseApplyResponse(res, { ok: false, error: 'bad payload' });
    expect(parsed.ok).toBe(false);
    expect(parsed.status).toBe(422);
    expect(parsed.error).toBe('bad payload');
  });

  it('falls back to a generic HTTP-status error when the server omits one', () => {
    const res = makeResponse({}, { status: 500, ok: false });
    const parsed = parseApplyResponse(res, { ok: false });
    expect(parsed.ok).toBe(false);
    expect(parsed.error).toBe('Auto-apply returned HTTP 500.');
  });

  it('treats missing body (parse error) as a failure with HTTP status fallback', () => {
    const res = makeResponse({}, { status: 502, ok: false });
    const parsed = parseApplyResponse(res, null);
    expect(parsed.ok).toBe(false);
    expect(parsed.error).toBe('Auto-apply returned HTTP 502.');
  });
});

describe('rollbackTransitions', () => {
  it('returns the snapshot strategy when the rec is currently applied', () => {
    const rec = makeRec({ id: 'rec-1' });
    const before = makeStrategy({ name: 'Before' });
    const result = rollbackTransitions(rec, ['rec-1'], [['rec-1', before]]);
    expect(result).toEqual({
      kind: 'markRollback',
      recId: 'rec-1',
      restoredStrategy: before,
    });
  });

  it('returns null when the rec is not currently applied', () => {
    const rec = makeRec({ id: 'rec-2' });
    const result = rollbackTransitions(rec, [], []);
    expect(result).toBeNull();
  });

  it('returns null when no snapshot exists for the applied rec', () => {
    const rec = makeRec({ id: 'rec-3' });
    const result = rollbackTransitions(rec, ['rec-3'], []);
    expect(result).toBeNull();
  });
});

// ─── executeApply — acceptance criteria ─────────────────────────────────

describe('executeApply — AC1 (Toggle ON visibly changes strategy params)', () => {
  it('emits markApplied and returns ok=true on a 2xx with ok=true body', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const updated = makeStrategy({
      name: 'After Apply',
      settings: {
        timeframe: '1h',
        riskParameters: { maxLossPerTrade: 3, maxDrawdown: 10, maxAllocation: 25 },
      },
    });
    const fetchFn = jest.fn().mockResolvedValue(
      makeResponse({ ok: true, strategy: updated }, { status: 200 }),
    );
    const onHistoryStatusChange = jest.fn();

    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn, onHistoryStatusChange },
    );

    expect(result.ok).toBe(true);
    const kinds = result.transitions.map((t) => t.kind);
    expect(kinds).toEqual(['snapshot', 'markApplying', 'clearError', 'markApplied']);

    const snapshotTx = result.transitions.find((t) => t.kind === 'snapshot');
    if (snapshotTx && snapshotTx.kind === 'snapshot') {
      expect(snapshotTx.entry[1]).toEqual(strategy);
    } else {
      throw new Error('expected snapshot transition');
    }

    const markApplied = result.transitions.find((t) => t.kind === 'markApplied');
    expect(markApplied).toEqual({ kind: 'markApplied', recId: 'rec-1' });
  });
});

describe('executeApply — AC2 (Toggle OFF restores pre-apply snapshot)', () => {
  it('emits markRollback with the snapshot strategy when the rec is applied', async () => {
    const rec = makeRec();
    const before = makeStrategy({ name: 'Before' });
    const fetchFn = jest.fn();
    const onHistoryStatusChange = jest.fn();

    const result = await executeApply(
      { rec, strategy: before, appliedRecIds: ['rec-1'], preApplySnapshots: [['rec-1', before]] },
      { fetchFn, onHistoryStatusChange },
    );

    expect(result.ok).toBe(true);
    expect(fetchFn).not.toHaveBeenCalled();
    expect(result.transitions).toEqual([
      { kind: 'markRollback', recId: 'rec-1', restoredStrategy: before },
    ]);
  });
});

describe('executeApply — AC3 (History panel shows Applied/Dismissed badge)', () => {
  it('fires onHistoryStatusChange("applied") within 1s of a successful apply', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockResolvedValue(
      makeResponse({ ok: true, strategy }, { status: 200 }),
    );
    const onHistoryStatusChange = jest.fn();

    const start = Date.now();
    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn, onHistoryStatusChange },
    );
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(1000);
    expect(result.ok).toBe(true);
    expect(onHistoryStatusChange).toHaveBeenCalledTimes(1);
    expect(onHistoryStatusChange).toHaveBeenCalledWith('rec-1', 'applied');
  });

  it('fires onHistoryStatusChange("dismissed") within 1s of a rollback', async () => {
    const rec = makeRec();
    const before = makeStrategy({ name: 'Before' });
    const fetchFn = jest.fn();
    const onHistoryStatusChange = jest.fn();

    const start = Date.now();
    const result = await executeApply(
      { rec, strategy: before, appliedRecIds: ['rec-1'], preApplySnapshots: [['rec-1', before]] },
      { fetchFn, onHistoryStatusChange },
    );
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(1000);
    expect(result.ok).toBe(true);
    expect(onHistoryStatusChange).toHaveBeenCalledTimes(1);
    expect(onHistoryStatusChange).toHaveBeenCalledWith('rec-1', 'dismissed');
  });

  it('does NOT fire onHistoryStatusChange on a failed apply', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockResolvedValue(
      makeResponse({}, { status: 422, ok: false }),
    );
    const onHistoryStatusChange = jest.fn();

    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn, onHistoryStatusChange },
    );

    expect(result.ok).toBe(false);
    expect(onHistoryStatusChange).not.toHaveBeenCalled();
  });
});

describe('executeApply — AC4 (no 404s in dev server console)', () => {
  it('POSTs to /api/ai/auto-apply (the only endpoint the panel calls)', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockResolvedValue(
      makeResponse({ ok: true, strategy }, { status: 200 }),
    );

    await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn },
    );

    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('/api/ai/auto-apply');
    expect((init as RequestInit).method).toBe('POST');
  });

  it('surfaces the server-side auto-apply error to the caller (a 422, not a 404)', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockResolvedValue(
      makeResponse(
        { ok: false, error: 'destructive rec requires explicit opt-in' },
        { status: 422, ok: false },
      ),
    );

    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn },
    );

    expect(result.ok).toBe(false);
    const setError = result.transitions.find((t) => t.kind === 'setError');
    expect(setError).toEqual({
      kind: 'setError',
      recId: 'rec-1',
      message: 'destructive rec requires explicit opt-in',
    });
    const dropSnapshot = result.transitions.find((t) => t.kind === 'dropSnapshot');
    expect(dropSnapshot).toEqual({ kind: 'dropSnapshot', recId: 'rec-1' });
  });

  it('surfaces a network failure as a setError transition (not a thrown exception)', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockRejectedValue(new Error('ECONNREFUSED'));

    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn },
    );

    expect(result.ok).toBe(false);
    const setError = result.transitions.find((t) => t.kind === 'setError');
    if (setError && setError.kind === 'setError') {
      expect(setError.message).toBe('ECONNREFUSED');
    } else {
      throw new Error('expected setError transition');
    }
    expect(result.transitions.some((t) => t.kind === 'dropSnapshot')).toBe(true);
  });

  it('surfaces a malformed JSON body as a fallback HTTP-status error', async () => {
    const rec = makeRec();
    const strategy = makeStrategy();
    const fetchFn = jest.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: () => Promise.reject(new Error('not json')),
    } as unknown as Response);

    const result = await executeApply(
      { rec, strategy, appliedRecIds: [], preApplySnapshots: [] },
      { fetchFn },
    );

    expect(result.ok).toBe(false);
    const setError = result.transitions.find((t) => t.kind === 'setError');
    if (setError && setError.kind === 'setError') {
      expect(setError.message).toBe('Auto-apply returned HTTP 502.');
    } else {
      throw new Error('expected setError transition');
    }
  });
});