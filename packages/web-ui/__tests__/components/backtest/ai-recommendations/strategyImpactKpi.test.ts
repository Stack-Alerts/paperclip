// BTCAAAAA-37772 Sprint B/B6 — unit tests for strategyImpactKpi helpers
// including the new reProjectFromServer function.

import {
  deriveBaselineKpis,
  sumDeltas,
  applyDelta,
  rebacktestStub,
  reProjectFromServer,
  deltaDirection,
  formatPercent,
  formatCurrency,
  formatRatio,
  formatInteger,
} from '@/components/backtest/ai-recommendations/strategyImpactKpi';
import type { BacktestResult } from '@/lib/strategy-builder/types';

const MOCK_RESULT: BacktestResult = {
  id: 'r1',
  runId: 'run1',
  strategyId: 's1',
  status: 'completed',
  startDate: '2025-01-01',
  endDate: '2025-12-31',
  totalTrades: 50,
  winningTrades: 30,
  losingTrades: 20,
  winRate: 0.6,
  profitFactor: 1.8,
  maxDrawdown: 0.12,
  initialCapital: 10000,
  finalCapital: 12500,
  totalReturn: 2500,
  returnPercentage: 25,
  sharpeRatio: 1.2,
  sortino_ratio: 1.5,
  averageWin: 150,
  averageLoss: -80,
  createdAt: '2026-06-01T00:00:00Z',
  completedAt: '2026-06-01T00:01:00Z',
  trades: [],
};

describe('deriveBaselineKpis', () => {
  it('returns zeros for null result', () => {
    const kpis = deriveBaselineKpis(null);
    expect(kpis.winRate).toBe(0);
    expect(kpis.profitFactor).toBe(0);
    expect(kpis.entries).toBe(0);
  });

  it('maps result fields to KpiSet', () => {
    const kpis = deriveBaselineKpis(MOCK_RESULT);
    expect(kpis.winRate).toBeCloseTo(0.6);
    expect(kpis.profitFactor).toBeCloseTo(1.8);
    expect(kpis.maxDrawdown).toBeCloseTo(0.12);
    expect(kpis.entries).toBe(50);
    expect(kpis.netLiquidity).toBe(2500);
  });

  it('clamps winRate to [0,1]', () => {
    const r = { ...MOCK_RESULT, winRate: 1.5 };
    expect(deriveBaselineKpis(r).winRate).toBe(1);
    const r2 = { ...MOCK_RESULT, winRate: -0.1 };
    expect(deriveBaselineKpis(r2).winRate).toBe(0);
  });
});

describe('sumDeltas', () => {
  it('returns empty delta object for empty array', () => {
    const d = sumDeltas([]);
    // The reducer starts from {} so fields are undefined when no deltas present.
    expect(d.winRate).toBeUndefined();
    expect(d.profitFactor).toBeUndefined();
  });

  it('sums multiple deltas', () => {
    const d = sumDeltas([
      { winRate: 0.05, profitFactor: 0.2 },
      { winRate: 0.03, profitFactor: 0.1 },
    ]);
    expect(d.winRate).toBeCloseTo(0.08);
    expect(d.profitFactor).toBeCloseTo(0.3);
  });
});

describe('applyDelta', () => {
  const base = deriveBaselineKpis(MOCK_RESULT);

  it('adds delta to baseline', () => {
    const after = applyDelta(base, { winRate: 0.05, profitFactor: 0.1 });
    expect(after.winRate).toBeCloseTo(0.65);
    expect(after.profitFactor).toBeCloseTo(1.9);
  });

  it('clamps winRate at 1', () => {
    const after = applyDelta(base, { winRate: 0.5 });
    expect(after.winRate).toBe(1);
  });

  it('floors profitFactor at 0', () => {
    const after = applyDelta(base, { profitFactor: -99 });
    expect(after.profitFactor).toBe(0);
  });
});

describe('rebacktestStub', () => {
  it('resolves with local sum-delta result', async () => {
    const base = deriveBaselineKpis(MOCK_RESULT);
    const deltas = [{ winRate: 0.05 }];
    const result = await rebacktestStub(base, deltas);
    expect(result.winRate).toBeCloseTo(0.65);
  });

  it('rejects when signal is aborted', async () => {
    const base = deriveBaselineKpis(MOCK_RESULT);
    const controller = new AbortController();
    const promise = rebacktestStub(base, [], controller.signal);
    controller.abort();
    await expect(promise).rejects.toThrow();
  });
});

describe('reProjectFromServer — Sprint B/B4', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('returns kpis from a successful server response', async () => {
    const mockKpis = {
      winRate: 0.7,
      netLiquidity: 3000,
      maxDrawdown: 0.1,
      profitFactor: 2.0,
      entries: 55,
    };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, kpis: mockKpis }),
    } as Response);

    const result = await reProjectFromServer('s1', {});
    expect(result).toEqual(mockKpis);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/backtest/re-project',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('returns null when server returns ok:false', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: false, error: 'Backtest failed.' }),
    } as Response);

    const result = await reProjectFromServer('s1', {});
    expect(result).toBeNull();
  });

  it('returns null on HTTP error', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({}),
    } as Response);

    const result = await reProjectFromServer('s1', {});
    expect(result).toBeNull();
  });

  it('returns null on network error', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

    const result = await reProjectFromServer('s1', {});
    expect(result).toBeNull();
  });

  it('returns null when aborted', async () => {
    global.fetch = jest.fn().mockRejectedValue(
      new DOMException('aborted', 'AbortError'),
    );
    const controller = new AbortController();
    controller.abort();
    const result = await reProjectFromServer('s1', {}, controller.signal);
    expect(result).toBeNull();
  });

  it('passes backtestConfig in the request body', async () => {
    const config = { timeframe: '1h', startDate: '2025-01-01' };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ok: true,
        kpis: { winRate: 0.5, netLiquidity: 0, maxDrawdown: 0, profitFactor: 1, entries: 10 },
      }),
    } as Response);

    await reProjectFromServer('s1', config);
    const [, init] = (global.fetch as jest.Mock).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string) as unknown;
    expect(body).toMatchObject({ strategyId: 's1', backtestConfig: config });
  });
});

describe('deltaDirection', () => {
  it('up for positive delta on higher-is-better metric', () => {
    expect(deltaDirection(0.05, true)).toBe('up');
  });

  it('down for negative delta on higher-is-better metric', () => {
    expect(deltaDirection(-0.05, true)).toBe('down');
  });

  it('down for positive delta on lower-is-better metric', () => {
    expect(deltaDirection(0.05, false)).toBe('down');
  });

  it('flat for zero delta', () => {
    expect(deltaDirection(0, true)).toBe('flat');
  });
});

describe('formatters', () => {
  it('formatPercent formats to XX.X%', () => {
    expect(formatPercent(0.6)).toBe('60.0%');
  });

  it('formatPercent returns – for non-finite', () => {
    expect(formatPercent(NaN)).toBe('–');
  });

  it('formatCurrency formats thousands with comma grouping', () => {
    expect(formatCurrency(1500)).toBe('$1,500');
    expect(formatCurrency(8824)).toBe('$8,824');
  });

  it('formatRatio rounds to 2dp by default', () => {
    expect(formatRatio(1.789)).toBe('1.79');
  });

  it('formatInteger truncates', () => {
    expect(formatInteger(42.9)).toBe('42');
  });
});
