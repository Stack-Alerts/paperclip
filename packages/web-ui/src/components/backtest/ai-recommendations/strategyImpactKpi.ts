// BTCAAAAA-37774 Sprint A2 — Strategy Impact KPI bar helpers.
//
// Computes "before" KPIs from the live BacktestResult and "after" KPIs by
// summing the projected deltas of every currently-applied recommendation.
// The 250ms-debounced re-backtest is stubbed (Sprint B/B4 ships the real
// server endpoint); the stub resolves with the locally-summed deltas so the
// Preview → Confirmed transition can land in this card and be gated behind a
// runtime flag for forward compatibility.

import { BacktestResult } from '@/lib/strategy-builder/types';

export interface KpiSet {
  winRate: number;          // 0..1
  netLiquidity: number;     // currency
  maxDrawdown: number;      // 0..1 (positive number, larger is worse)
  profitFactor: number;     // ratio
  entries: number;          // count
}

export interface ProjectedDelta {
  winRate?: number;
  netLiquidity?: number;
  maxDrawdown?: number;
  profitFactor?: number;
  entries?: number;
}

export type AppliedRecImpact = {
  recId: string;
  delta: ProjectedDelta;
};

const EMPTY_KPI: KpiSet = {
  winRate: 0,
  netLiquidity: 0,
  maxDrawdown: 0,
  profitFactor: 0,
  entries: 0,
};

export function deriveBaselineKpis(result: BacktestResult | null | undefined): KpiSet {
  if (!result) return { ...EMPTY_KPI };
  const initial = Number(result.initialCapital ?? 0);
  const final = Number(result.finalCapital ?? 0);
  return {
    winRate: clampUnit(numberOr(result.winRate, 0)),
    netLiquidity: Number.isFinite(final - initial) ? final - initial : 0,
    maxDrawdown: clampUnit(numberOr(result.maxDrawdown, 0)),
    profitFactor: Math.max(0, numberOr(result.profitFactor, 0)),
    entries: Math.max(0, Math.trunc(numberOr(result.totalTrades, 0))),
  };
}

export function sumDeltas(deltas: ProjectedDelta[]): ProjectedDelta {
  return deltas.reduce<ProjectedDelta>((acc, d) => ({
    winRate: (acc.winRate ?? 0) + (d.winRate ?? 0),
    netLiquidity: (acc.netLiquidity ?? 0) + (d.netLiquidity ?? 0),
    maxDrawdown: (acc.maxDrawdown ?? 0) + (d.maxDrawdown ?? 0),
    profitFactor: (acc.profitFactor ?? 0) + (d.profitFactor ?? 0),
    entries: (acc.entries ?? 0) + (d.entries ?? 0),
  }), {});
}

export function applyDelta(base: KpiSet, delta: ProjectedDelta): KpiSet {
  return {
    winRate: clampUnit(base.winRate + (delta.winRate ?? 0)),
    netLiquidity: base.netLiquidity + (delta.netLiquidity ?? 0),
    maxDrawdown: clampUnit(base.maxDrawdown + (delta.maxDrawdown ?? 0)),
    profitFactor: Math.max(0, base.profitFactor + (delta.profitFactor ?? 0)),
    entries: Math.max(0, Math.trunc(base.entries + (delta.entries ?? 0))),
  };
}

// Re-backtest stub used while the real Sprint B/B4 endpoint is in flight.
// Resolves with the locally-summed projected deltas.
export async function rebacktestStub(
  base: KpiSet,
  deltas: ProjectedDelta[],
  signal?: AbortSignal,
): Promise<KpiSet> {
  await new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, 0);
    if (signal) {
      signal.addEventListener('abort', () => {
        clearTimeout(t);
        reject(new DOMException('aborted', 'AbortError'));
      });
    }
  });
  return applyDelta(base, sumDeltas(deltas));
}

function numberOr(v: unknown, fallback: number): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function clampUnit(n: number): number {
  if (!Number.isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return '–';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatCurrency(value: number): string {
  if (!Number.isFinite(value)) return '–';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(2)}k`;
  return `${sign}$${abs.toFixed(2)}`;
}

export function formatRatio(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return '–';
  return value.toFixed(digits);
}

export function formatInteger(value: number): string {
  if (!Number.isFinite(value)) return '–';
  return Math.trunc(value).toString();
}

export type DeltaDirection = 'up' | 'down' | 'flat';

// Higher-is-better tiles (WR, Net Liquidity, PF, Entries): positive delta
// means up. Drawdown is inverted — positive delta is bad.
export function deltaDirection(
  delta: number,
  higherIsBetter: boolean,
): DeltaDirection {
  if (!Number.isFinite(delta) || delta === 0) return 'flat';
  const positive = delta > 0;
  if (higherIsBetter) return positive ? 'up' : 'down';
  return positive ? 'down' : 'up';
}
