// BTCAAAAA-37780 / Sprint A6 — helpers for the right-rail Diagnose tab.
//
// The Diagnose tab renders three things:
//   1. the orchestrator-supplied `diagnosis` markdown,
//   2. a metrics table comparing what the backtest *reported* (the
//      portfolio-level summary fields on `BacktestResult`) against the
//      values recomputed *per entry* (walking the `trades` array), and
//   3. a pinned sentence describing what would change if the currently
//      staged recommendations were applied.

import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';

export interface DiagnoseMetricRow {
  /** Display label, e.g. "Profit factor". */
  label: string;
  /** Stable key for tests / React keys. */
  key: 'pf' | 'wr' | 'sharpe' | 'dd' | 'entries';
  /** Value reported by the orchestrator (BacktestResult summary field). */
  reported: string;
  /** Value recomputed from the trades array. */
  perEntry: string;
  /** True when reported and per-entry disagree (after formatting). */
  divergent: boolean;
}

const EMPTY = '—';

function fmtRatio(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMPTY;
  return v.toFixed(digits);
}

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMPTY;
  // BacktestResult.winRate may be reported as a fraction (0–1) or a
  // percentage (0–100); collapse both so the table is consistent.
  const pct = Math.abs(v) <= 1 ? v * 100 : v;
  return `${pct.toFixed(digits)}%`;
}

function fmtInt(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMPTY;
  return Math.round(v).toString();
}

interface PerEntryStats {
  entries: number;
  wins: number;
  winRate: number | null;
  profitFactor: number | null;
  sharpe: number | null;
  maxDrawdown: number | null;
}

export function computePerEntryStats(trades: Trade[] | undefined | null): PerEntryStats {
  const empty: PerEntryStats = {
    entries: 0,
    wins: 0,
    winRate: null,
    profitFactor: null,
    sharpe: null,
    maxDrawdown: null,
  };
  if (!trades || trades.length === 0) return empty;

  let wins = 0;
  let grossWin = 0;
  let grossLoss = 0;
  const returns: number[] = [];
  let cum = 0;
  let peak = 0;
  let maxDd = 0;

  for (const t of trades) {
    const pnl = Number(t.pnl);
    if (!Number.isFinite(pnl)) continue;
    if (pnl > 0) {
      wins += 1;
      grossWin += pnl;
    } else if (pnl < 0) {
      grossLoss += -pnl;
    }
    returns.push(pnl);
    cum += pnl;
    if (cum > peak) peak = cum;
    const dd = peak - cum;
    if (dd > maxDd) maxDd = dd;
  }

  const entries = trades.length;
  const winRate = entries > 0 ? wins / entries : null;
  const profitFactor =
    grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Number.POSITIVE_INFINITY : null;

  let sharpe: number | null = null;
  if (returns.length > 1) {
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance =
      returns.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (returns.length - 1);
    const std = Math.sqrt(variance);
    sharpe = std > 0 ? mean / std : null;
  }

  return {
    entries,
    wins,
    winRate,
    profitFactor:
      profitFactor !== null && Number.isFinite(profitFactor) ? profitFactor : null,
    sharpe,
    // Per-entry max drawdown is in the same units as pnl (currency); the
    // reported maxDrawdown on BacktestResult is typically a percentage, so
    // we surface this as a peak-to-trough currency drop for the table.
    maxDrawdown: maxDd > 0 ? maxDd : null,
  };
}

export function buildDiagnoseRows(
  result: BacktestResult | null | undefined,
  trades: Trade[] | undefined | null,
): DiagnoseMetricRow[] {
  const stats = computePerEntryStats(trades);

  const reportedPf = result?.profitFactor ?? null;
  const reportedWr = result?.winRate ?? null;
  const reportedSharpe = result?.sharpeRatio ?? null;
  const reportedDd = result?.maxDrawdown ?? null;
  const reportedEntries = result?.totalTrades ?? null;

  const rPf = fmtRatio(reportedPf);
  const ePf = fmtRatio(stats.profitFactor);
  const rWr = fmtPct(reportedWr);
  const eWr = fmtPct(stats.winRate);
  const rSh = fmtRatio(reportedSharpe);
  const eSh = fmtRatio(stats.sharpe);
  const rDd = fmtPct(reportedDd);
  // Per-entry DD is a currency value, not a percent. Format with two decimals.
  const eDd = stats.maxDrawdown === null ? EMPTY : stats.maxDrawdown.toFixed(2);
  const rEn = fmtInt(reportedEntries);
  const eEn = fmtInt(stats.entries);

  return [
    { key: 'pf', label: 'Profit factor', reported: rPf, perEntry: ePf, divergent: rPf !== EMPTY && ePf !== EMPTY && rPf !== ePf },
    { key: 'wr', label: 'Win rate', reported: rWr, perEntry: eWr, divergent: rWr !== EMPTY && eWr !== EMPTY && rWr !== eWr },
    { key: 'sharpe', label: 'Sharpe', reported: rSh, perEntry: eSh, divergent: rSh !== EMPTY && eSh !== EMPTY && rSh !== eSh },
    { key: 'dd', label: 'Max drawdown', reported: rDd, perEntry: eDd, divergent: false },
    { key: 'entries', label: 'Entries', reported: rEn, perEntry: eEn, divergent: rEn !== EMPTY && eEn !== EMPTY && rEn !== eEn },
  ];
}

export interface StagedRecSummary {
  /** Rec id the user has toggled on (currently "staged" in the panel). */
  id: string;
  title: string;
  suggestedParams: Array<{ key: string; value: string }>;
}

/**
 * Build the pinned-sentence text that summarises what would change if the
 * currently staged recommendations were applied.
 */
export function buildStagedRecsSentence(
  staged: StagedRecSummary[],
  strategy: Strategy | null | undefined,
): string {
  if (!staged || staged.length === 0) {
    return 'No staged recommendations. Toggle a recommendation on to preview its impact here.';
  }

  const paramCount = staged.reduce((n, r) => n + (r.suggestedParams?.length ?? 0), 0);
  const paramKeys = new Set(
    staged.flatMap((r) => r.suggestedParams?.map((p) => p.key) ?? []),
  );
  const blockCount = strategy?.blocks ? countOwningBlocks(strategy, paramKeys) : 0;

  if (staged.length === 1) {
    const title = staged[0].title.trim() || 'this recommendation';
    if (paramCount === 0) {
      return `Applying "${title}" is staged — no parameter overrides will be written.`;
    }
    const paramLabel = paramCount === 1 ? '1 parameter' : `${paramCount} parameters`;
    if (blockCount > 0) {
      const blockLabel = blockCount === 1 ? '1 block' : `${blockCount} blocks`;
      return `Applying "${title}" would update ${paramLabel} across ${blockLabel}.`;
    }
    return `Applying "${title}" would update ${paramLabel}.`;
  }

  const recLabel = `${staged.length} staged recommendations`;
  if (paramCount === 0) {
    return `Applying ${recLabel} — no parameter overrides will be written.`;
  }
  const paramLabel = paramCount === 1 ? '1 parameter' : `${paramCount} parameters`;
  if (blockCount > 0) {
    const blockLabel = blockCount === 1 ? '1 block' : `${blockCount} blocks`;
    return `Applying ${recLabel} would update ${paramLabel} across ${blockLabel}.`;
  }
  return `Applying ${recLabel} would update ${paramLabel}.`;
}

function countOwningBlocks(strategy: Strategy, paramKeys: Set<string>): number {
  if (paramKeys.size === 0) return 0;
  let count = 0;
  for (const block of strategy.blocks ?? []) {
    const data = block.data;
    if (!data || typeof data !== 'object') continue;
    for (const key of Object.keys(data)) {
      if (paramKeys.has(key)) {
        count += 1;
        break;
      }
    }
  }
  return count;
}
