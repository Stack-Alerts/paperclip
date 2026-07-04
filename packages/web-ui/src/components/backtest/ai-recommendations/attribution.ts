// BTCAAAAA-38731 — performance attribution for the analyze prompt.
//
// The analyze payload historically carried the trade log + aggregate metrics
// but no attribution, so the model's recommendations clustered around a few
// generic defaults (widen SL, reduce hold). This module derives two extra
// signals the app already computes and feeds them into the request payload so
// the model can produce strategy-specific, more diverse recommendations:
//
//   1. metric_divergence — per-entry vs reported metric disagreement
//      (buildDiagnoseRows), which flags when the portfolio summary and the
//      per-trade recomputation tell different stories.
//   2. entry_signal_usage / exit_type_usage — which signal gated the most
//      entries and which exit reason closed the most trades, each with the
//      net PnL attributed to it (which block contributed most to the outcome).

import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { buildDiagnoseRows } from './diagnoseMetrics';

export interface MetricDivergence {
  metric: string;
  reported: string;
  per_entry: string;
  divergent: boolean;
}

export interface SignalAttribution {
  /** Entry signal name that fired at trade open. */
  signal: string;
  /** Owning strategy block name, when the signal maps to one; else null. */
  block: string | null;
  /** Number of trades this signal gated. */
  entries: number;
  wins: number;
  win_rate_pct: number | null;
  net_pnl: number;
}

export interface ExitAttribution {
  /** Exit reason (exitType, falling back to notes). */
  exit_type: string;
  count: number;
  net_pnl: number;
}

export interface AttributionSummary {
  metric_divergence: MetricDivergence[];
  entry_signal_usage: SignalAttribution[];
  exit_type_usage: ExitAttribution[];
}

const MAX_ROWS = 8;

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

/** Map an entry signal name to the name of the strategy block that owns it. */
function buildSignalToBlock(strategy: Strategy | null | undefined): Map<string, string> {
  const map = new Map<string, string>();
  for (const block of strategy?.blocks ?? []) {
    const data = block.data as Record<string, unknown> | undefined;
    const blockName = typeof data?.name === 'string' ? data.name : null;
    if (!blockName) continue;
    const signals = Array.isArray(data?.signals) ? data.signals : [];
    for (const sig of signals) {
      const sigName = (sig as { name?: unknown })?.name;
      if (typeof sigName === 'string' && !map.has(sigName)) {
        map.set(sigName, blockName);
      }
    }
  }
  return map;
}

function buildEntrySignalUsage(
  trades: Trade[],
  signalToBlock: Map<string, string>,
): SignalAttribution[] {
  const acc = new Map<string, { entries: number; wins: number; netPnl: number }>();
  for (const t of trades) {
    const signals = t.entrySignals;
    if (!Array.isArray(signals) || signals.length === 0) continue;
    const pnl = Number(t.pnl);
    const finite = Number.isFinite(pnl);
    for (const raw of signals) {
      if (typeof raw !== 'string' || !raw.trim()) continue;
      const key = raw.trim();
      const cur = acc.get(key) ?? { entries: 0, wins: 0, netPnl: 0 };
      cur.entries += 1;
      if (finite) {
        cur.netPnl += pnl;
        if (pnl > 0) cur.wins += 1;
      }
      acc.set(key, cur);
    }
  }

  return [...acc.entries()]
    .map(([signal, v]) => ({
      signal,
      block: signalToBlock.get(signal) ?? null,
      entries: v.entries,
      wins: v.wins,
      win_rate_pct: v.entries > 0 ? round2((v.wins / v.entries) * 100) : null,
      net_pnl: round2(v.netPnl),
    }))
    .sort((a, b) => b.entries - a.entries || Math.abs(b.net_pnl) - Math.abs(a.net_pnl))
    .slice(0, MAX_ROWS);
}

function buildExitTypeUsage(trades: Trade[]): ExitAttribution[] {
  const acc = new Map<string, { count: number; netPnl: number }>();
  for (const t of trades) {
    const label =
      (typeof t.exitType === 'string' && t.exitType.trim()) ||
      (typeof t.notes === 'string' && t.notes.trim()) ||
      'unknown';
    const pnl = Number(t.pnl);
    const cur = acc.get(label) ?? { count: 0, netPnl: 0 };
    cur.count += 1;
    if (Number.isFinite(pnl)) cur.netPnl += pnl;
    acc.set(label, cur);
  }

  return [...acc.entries()]
    .map(([exit_type, v]) => ({ exit_type, count: v.count, net_pnl: round2(v.netPnl) }))
    .sort((a, b) => b.count - a.count || Math.abs(b.net_pnl) - Math.abs(a.net_pnl))
    .slice(0, MAX_ROWS);
}

/**
 * Build the performance-attribution block appended to the analyze payload.
 * Returns null when there are no trades to attribute (the model already gets
 * an explicit no-trades signal via the empty trade log).
 */
export function buildAttribution(
  result: BacktestResult | null | undefined,
  strategy: Strategy | null | undefined,
): AttributionSummary | null {
  const trades = result?.trades ?? [];
  if (trades.length === 0) return null;

  const metric_divergence = buildDiagnoseRows(result ?? null, trades).map((row) => ({
    metric: row.label,
    reported: row.reported,
    per_entry: row.perEntry,
    divergent: row.divergent,
  }));

  const signalToBlock = buildSignalToBlock(strategy);
  const entry_signal_usage = buildEntrySignalUsage(trades, signalToBlock);
  const exit_type_usage = buildExitTypeUsage(trades);

  return { metric_divergence, entry_signal_usage, exit_type_usage };
}
