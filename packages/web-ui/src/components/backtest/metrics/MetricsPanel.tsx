'use client';

import { useEffect, useMemo, useState } from 'react';
import { BacktestResult, Trade, type BacktestRunRecord } from '@/lib/strategy-builder/types';
import { loadRunRecordsForStrategy, loadAllRunRecords } from '@/lib/backtest-history';
import { RichTooltip, type TooltipContent } from '@/components/strategy-builder/RichTooltip';
import { LiquidationRiskMeter } from './LiquidationRiskMeter';
import { DrawdownChart } from './DrawdownChart';
import { useFontSizes } from '@/components/backtest/backtestFontScale';
import {
  TrendingUp, TrendingDown, DollarSign, Activity, BarChart3, BarChart2, LineChart,
  RotateCcw, AlertTriangle, AlertOctagon, Clock, Hash, Target,
  ArrowUp, ArrowDown, Sparkles, ArrowUpCircle, ArrowDownCircle, Scale,
  Percent, Trophy, Skull, Coins, ChevronDown, ChevronUp,
  Calendar, Layers, ArrowRight, Percent as PercentIcon, Download, Undo2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  TT_TOTAL_RETURN, TT_NET_PROFIT, TT_INITIAL_CAPITAL, TT_FINAL_CAPITAL,
  TT_MAX_DRAWDOWN, TT_SHARPE, TT_SORTINO, TT_CALMAR,
  TT_TOTAL_TRADES, TT_WIN_RATE, TT_WINNING_TRADES, TT_LOSING_TRADES,
  TT_PROFIT_FACTOR, TT_EXPECTANCY, TT_AVG_WIN, TT_AVG_LOSS,
  TT_RISK_REWARD, TT_BREAKEVEN_WIN,
  TT_BEST_TRADE, TT_WORST_TRADE, TT_AVG_BARS,
  TT_MAX_CONSEC_WINS, TT_MAX_CONSEC_LOSSES,
  TT_LONG_TRADES, TT_SHORT_TRADES,
  TT_DURATION, TT_BARS_ANALYZED, TT_START_DATE, TT_END_DATE,
  TT_EXIT_TYPE,
  TT_VOLATILITY, TT_VAR_95, TT_CVAR_95, TT_EXPOSURE_TIME,
  TT_PAYOFF_RATIO, TT_LARGEST_WIN, TT_LARGEST_LOSS, TT_CURRENCY,
  TT_ADDITIONAL_METRICS, TT_RECHECKS, TT_SIGNALS_REQUIRED, TT_STRATEGY_SIGNALS_SECTION,
  TT_ENTRY_SIGNALS_FIRED, TT_ENTRY_SIGNALS_TABLE,
  TT_EXIT_SIGNALS, TT_STOP_LOSS_ADJUSTMENTS,
  TT_ANNUALIZED_RETURN, TT_MARGIN_OF_SAFETY, TT_AVG_TRADE_DURATION,
  TT_KELLY_CRITERION, TT_GROSS_PROFIT, TT_GROSS_LOSS,
  TT_LONG_WIN_RATE, TT_SHORT_WIN_RATE,
  TT_MAX_DRAWDOWN_USD, TT_PEAK_CAPITAL, TT_RECOVERY_FACTOR,
  TT_LONGEST_DRAWDOWN, TT_LIQUIDATION_BUFFER,
  TT_EQUITY_CURVE, TT_DRAWDOWN_CURVE, TT_CAPITAL_DRAWDOWN,
  TT_RECENT_RUN_RETURN, TT_RECENT_RUN_WR, TT_RECENT_RUN_TRADES, TT_RECENT_RUN_DD,
  TT_RECENT_RUN_DURATION,
} from './MetricsPanelTooltips';

// TT_ADDITIONAL_METRICS is the umbrella tooltip for the expandable section
// header; it is referenced via the section's own registry lookup so the
// eslint-plugin-react rule against unused imports does not flag it.
void TT_ADDITIONAL_METRICS;

export interface MetricsPanelProps {
  result?: BacktestResult | null;
  trades?: Trade[];
  /** Strategy id used to scope the "Recent Runs" history graphs. */
  strategyId?: string;
  /** Apply a past run's configuration back into the Config form. */
  onApplyConfig?: (record: BacktestRunRecord) => void;
  /** runId of the history record currently applied via Apply, if any. */
  appliedRunId?: string | null;
  /** Restore the run that was on screen before the last Apply. */
  onRollbackApply?: () => void;
  /** Max leverage used for the run — powers the liquidation-buffer estimate. */
  leverage?: number;
  /** Risk per trade (% of capital) — contextualises drawdown vs sizing. */
  riskPerTradePct?: number;
}

type Accent = 'green' | 'red' | 'orange' | 'blue' | 'neutral';

interface MetricRow {
  label: string;
  value: string;
  color?: string;
  tooltip: TooltipContent;
  icon: LucideIcon;
  accent: Accent;
  baseline?: string;
  strategy?: string;
}

function accentBg(accent: Accent): string {
  switch (accent) {
    case 'green': return 'color-mix(in srgb, var(--accent-green) 14%, transparent)';
    case 'red': return 'color-mix(in srgb, var(--accent-red) 14%, transparent)';
    case 'orange': return 'color-mix(in srgb, var(--accent-orange) 14%, transparent)';
    case 'blue': return 'color-mix(in srgb, var(--accent-blue) 14%, transparent)';
    default: return 'color-mix(in srgb, var(--text-muted) 14%, transparent)';
  }
}

function accentFg(accent: Accent): string {
  switch (accent) {
    case 'green': return 'var(--accent-green)';
    case 'red': return 'var(--accent-red)';
    case 'orange': return 'var(--accent-orange)';
    case 'blue': return 'var(--accent-blue)';
    default: return 'var(--text-secondary)';
  }
}

function deltaColor(delta: number | null): string {
  if (delta == null || !Number.isFinite(delta)) return 'var(--text-muted)';
  if (delta > 0) return 'var(--accent-green)';
  if (delta < 0) return 'var(--accent-red)';
  return 'var(--text-muted)';
}

function MetricCard({ label, value, color, tooltip, icon: Icon, accent, baseline, strategy }: MetricRow) {
  return (
    <RichTooltip content={tooltip}>
      <div
        className="rounded p-3 cursor-default h-full flex flex-col gap-1.5"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="flex items-center justify-center rounded-full shrink-0"
              style={{
                background: accentBg(accent),
                color: accentFg(accent),
                width: 28, height: 28,
              }}
              aria-hidden="true"
            >
              <Icon size={15} strokeWidth={2.2} />
            </span>
            <div className="min-w-0">
              {strategy && (
                <p
                  className="text-[10px] font-semibold uppercase tracking-wide truncate"
                  style={{ color: accentFg(accent), lineHeight: 1 }}
                >
                  {strategy}
                </p>
              )}
              <p
                className="text-[11px] truncate"
                style={{ color: 'var(--text-muted)', lineHeight: strategy ? 1.25 : 1 }}
                title={label}
              >
                {label}
              </p>
            </div>
          </div>
        </div>
        <p
          className="text-base font-semibold"
          style={{ color: color || 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}
        >
          {value}
        </p>
        {baseline && (
          <p
            className="text-[10px] truncate"
            style={{ color: 'var(--text-faint)', lineHeight: 1 }}
            title={baseline}
          >
            {baseline}
          </p>
        )}
      </div>
    </RichTooltip>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mt-5 mb-3 first:mt-0">
      <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
        {title}
      </p>
      {subtitle && (
        <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

function Sparkline({
  values, color, fillBelow = false, height = 56,
}: { values: number[]; color: string; fillBelow?: boolean; height?: number }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 200, H = 100;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const linePts = pts.join(' ');
  const areaPts = `0,${H} ${linePts} ${W},${H}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height, display: 'block' }}>
      {fillBelow && <polygon points={areaPts} fill={color} fillOpacity="0.12" />}
      <polyline points={linePts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** Webui-only Buy & Hold delta approximation. The backend does not currently
 *  emit a buy-and-hold benchmark series, so we approximate it from the first
 *  trade entry price and the last trade exit price. Returns null when the
 *  approximation is not meaningful (no trades, degenerate prices). */
function computeBuyHoldDelta(trades: Trade[]): { pct: number; abs: number; entry: number | null; exit: number | null } | null {
  if (!trades.length) return null;
  const closed = trades.filter(t => (t.status ?? '').toUpperCase() === 'CLOSED');
  const pool = closed.length > 0 ? closed : trades;
  const first = pool.find(t => Number.isFinite(t.entryPrice) && t.entryPrice > 0);
  const last = [...pool].reverse().find(t => Number.isFinite(t.exitPrice) && t.exitPrice > 0);
  if (!first || !last) return null;
  if (!Number.isFinite(first.entryPrice) || !Number.isFinite(last.exitPrice)) return null;
  const entry = first.entryPrice;
  const exit = last.exitPrice;
  if (entry <= 0) return null;
  const pct = ((exit - entry) / entry) * 100;
  return { pct, abs: exit - entry, entry, exit };
}

function formatTradeDuration(ms: number): string {
  const h = ms / 3_600_000;
  if (h < 1) return `${Math.round(ms / 60_000)} min`;
  if (h < 24) return `${h.toFixed(1)} h`;
  const days = h / 24;
  if (days < 30) return `${days.toFixed(1)} d`;
  return `${(days / 30.44).toFixed(1)} mo`;
}

function formatBuyHoldDeltaPct(d: { pct: number } | null): string {
  if (!d) return '—';
  const sign = d.pct >= 0 ? '↗ +' : '↘ ';
  return `vs BTC Buy&Hold ${sign}${d.pct.toFixed(2)}%`;
}

function formatBuyHoldDeltaDollar(d: { pct: number } | null, base: number): string {
  if (!d) return '—';
  const value = (base * d.pct) / 100;
  const sign = value >= 0 ? '↗ +$' : '↘ -$';
  return `vs BTC Buy&Hold ${sign}${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatBuyHoldDeltaScalar(d: { pct: number } | null): string {
  if (!d) return '—';
  const sign = d.pct >= 0 ? '↗ +' : '↘ ';
  return `vs BTC Buy&Hold ${sign}${d.pct.toFixed(2)}%`;
}

function HeroCard({
  label, value, valueColor, icon: Icon, accent, deltaPct, deltaText, tooltip,
}: {
  label: string;
  value: string;
  valueColor: string;
  icon: LucideIcon;
  accent: Accent;
  deltaPct: number | null;
  deltaText: string;
  tooltip: TooltipContent;
}) {
  return (
    <RichTooltip content={tooltip}>
      <div
        className="rounded-lg p-4 cursor-default flex flex-col gap-2 h-full"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2.5">
          <span
            className="flex items-center justify-center rounded-full shrink-0"
            style={{
              background: accentBg(accent),
              color: accentFg(accent),
              width: 26, height: 26,
            }}
            aria-hidden="true"
          >
            <Icon size={15} strokeWidth={2.2} />
          </span>
          <p
            className="text-[11px] font-medium uppercase tracking-wide truncate"
            style={{ color: 'var(--text-muted)' }}
            title={label}
          >
            {label}
          </p>
        </div>
        <p
          className="text-2xl font-semibold leading-tight"
          style={{ color: valueColor, fontVariantNumeric: 'tabular-nums' }}
        >
          {value}
        </p>
        <p
          className="text-[11px] font-medium leading-tight"
          style={{ color: deltaColor(deltaPct), fontVariantNumeric: 'tabular-nums' }}
        >
          {deltaText}
        </p>
      </div>
    </RichTooltip>
  );
}

function SparklineCard({
  label, value, icon: Icon, accent, sparkValues, sparkColor, valueColor, tooltip,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: Accent;
  sparkValues: number[];
  sparkColor: string;
  valueColor?: string;
  tooltip: TooltipContent;
}) {
  return (
    <RichTooltip content={tooltip}>
      <div
        className="rounded p-3 cursor-default h-full flex flex-col gap-1.5"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="flex items-center justify-center rounded-full shrink-0"
            style={{
              background: accentBg(accent),
              color: accentFg(accent),
              width: 24, height: 24,
            }}
            aria-hidden="true"
          >
            <Icon size={13} strokeWidth={2.2} />
          </span>
          <p
            className="text-[11px] truncate"
            style={{ color: 'var(--text-muted)' }}
            title={label}
          >
            {label}
          </p>
        </div>
        <Sparkline values={sparkValues} color={sparkColor} height={28} />
        <p
          className="text-sm font-semibold"
          style={{
            color: valueColor || 'var(--text-secondary)',
            fontVariantNumeric: 'tabular-nums',
            lineHeight: 1.1,
          }}
        >
          {value}
        </p>
      </div>
    </RichTooltip>
  );
}

function InfoCard({
  label, value, icon: Icon, accent, subValue, tooltip, className,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: Accent;
  subValue?: string;
  tooltip: TooltipContent;
  /** Optional extra class for the outer card wrapper (BTCAAAAA-66757: glow). */
  className?: string;
}) {
  return (
    <RichTooltip content={tooltip}>
      <div
        className={`rounded p-3 cursor-default h-full flex flex-col gap-1.5${className ? ` ${className}` : ''}`}
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="flex items-center justify-center rounded-full shrink-0"
            style={{
              background: accentBg(accent),
              color: accentFg(accent),
              width: 24, height: 24,
            }}
            aria-hidden="true"
          >
            <Icon size={13} strokeWidth={2.2} />
          </span>
          <p
            className="text-[11px] truncate"
            style={{ color: 'var(--text-muted)' }}
            title={label}
          >
            {label}
          </p>
        </div>
        <p
          className="text-sm font-semibold"
          style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}
        >
          {value}
        </p>
        {subValue && (
          <p
            className="text-[10px] truncate"
            style={{ color: 'var(--text-faint)', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}
            title={subValue}
          >
            {subValue}
          </p>
        )}
      </div>
    </RichTooltip>
  );
}

function computeTradeStats(trades: Trade[]) {
  if (!trades.length) return null;

  const closed = trades.filter(t => (t.status ?? '').toUpperCase() === 'CLOSED');
  const source = closed.length > 0 ? closed : trades;

  const pnls = source.map(t => t.pnl);
  // "Best trade" must be the largest *winning* P&L and "Worst trade" the
  // smallest *losing* P&L. With no winners or no losers the corresponding
  // value is 0 (BTCAAAAA-35996 / BTCAAAAA-37920).
  const winPnls = pnls.filter(p => p > 0);
  const lossPnls = pnls.filter(p => p < 0);
  const bestTrade = winPnls.length ? Math.max(...winPnls) : 0;
  const worstTrade = lossPnls.length ? Math.min(...lossPnls) : 0;
  const largestWin = winPnls.length ? Math.max(...winPnls) : 0;
  const largestLoss = lossPnls.length ? Math.min(...lossPnls) : 0;
  const avgBars = source.reduce((s, t) => s + (t.bars ?? 0), 0) / source.length;

  const longTrades = source.filter(t => (t.side ?? '').toUpperCase() === 'LONG');
  const shortTrades = source.filter(t => (t.side ?? '').toUpperCase() === 'SHORT');
  const longs = longTrades.length;
  const shorts = shortTrades.length;
  const longWinRate = longs > 0 ? (longTrades.filter(t => t.pnl > 0).length / longs) * 100 : null;
  const shortWinRate = shorts > 0 ? (shortTrades.filter(t => t.pnl > 0).length / shorts) * 100 : null;

  const durations: number[] = [];
  for (const t of source) {
    if (t.entryTime && t.exitTime) {
      const d = new Date(t.exitTime).getTime() - new Date(t.entryTime).getTime();
      if (d > 0) durations.push(d);
    }
  }
  const avgTradeDurationMs = durations.length > 0
    ? durations.reduce((s, d) => s + d, 0) / durations.length
    : null;

  const exitTypes: Record<string, number> = {};
  for (const t of source) {
    const key = t.exitType ?? 'Unknown';
    exitTypes[key] = (exitTypes[key] ?? 0) + 1;
  }

  const winsSum = winPnls.reduce((s, p) => s + p, 0);
  const lossesSum = lossPnls.reduce((s, p) => s + Math.abs(p), 0);

  // VaR95 / CVaR95 require N≥20 trades; below that surface "—".
  const returnsPct = source.map(t => t.pnlPercentage).filter(p => Number.isFinite(p));
  let var95: number | null = null;
  let cvar95: number | null = null;
  if (returnsPct.length >= 20) {
    const sorted = [...returnsPct].sort((a, b) => a - b);
    const cutoffIdx = Math.max(0, Math.floor(sorted.length * 0.05) - 1);
    var95 = sorted[cutoffIdx];
    const tail = sorted.slice(0, cutoffIdx + 1);
    cvar95 = tail.reduce((s, p) => s + p, 0) / tail.length;
  }

  let returnVolatility: number | null = null;
  if (returnsPct.length >= 2) {
    const mean = returnsPct.reduce((s, p) => s + p, 0) / returnsPct.length;
    const variance = returnsPct.reduce((s, p) => s + (p - mean) ** 2, 0) / (returnsPct.length - 1);
    returnVolatility = Math.sqrt(variance);
  }

  let maxConsecWins = 0, maxConsecLosses = 0, curWins = 0, curLosses = 0;
  for (const pnl of pnls) {
    if (pnl > 0) { curWins++; curLosses = 0; maxConsecWins = Math.max(maxConsecWins, curWins); }
    else { curLosses++; curWins = 0; maxConsecLosses = Math.max(maxConsecLosses, curLosses); }
  }

  return {
    bestTrade, worstTrade, largestWin, largestLoss, avgBars, longs, shorts,
    exitTypes, maxConsecWins, maxConsecLosses,
    winsSum, lossesSum, var95, cvar95, returnVolatility,
    longWinRate, shortWinRate, avgTradeDurationMs,
    count: source.length,
  };
}

/* ── Per-metric sparkline series ─────────────────────────────────────────── */

function buildCumulativeCount(trades: Trade[]): number[] {
  if (!trades.length) return [];
  const series: number[] = [];
  for (let i = 0; i < trades.length; i++) series.push(i + 1);
  return series;
}

function buildTradesPerDay(trades: Trade[]): number[] {
  if (!trades.length) return [];
  const byDay = new Map<string, number>();
  for (const t of trades) {
    const ts = (t as { exitTime?: string; entryTime?: string }).exitTime
      ?? (t as { entryTime?: string }).entryTime;
    if (!ts) continue;
    const day = ts.slice(0, 10);
    byDay.set(day, (byDay.get(day) ?? 0) + 1);
  }
  return Array.from(byDay.values());
}

function buildCumulativeWinLoss(trades: Trade[]): { wins: number[]; losses: number[] } {
  if (!trades.length) return { wins: [], losses: [] };
  const wins: number[] = [];
  const losses: number[] = [];
  let cw = 0, cl = 0;
  for (const t of trades) {
    if (t.pnl > 0) cw += 1;
    else if (t.pnl < 0) cl += 1;
    wins.push(cw);
    losses.push(cl);
  }
  return { wins, losses };
}

function buildRollingWinRate(trades: Trade[], window = 20): number[] {
  if (!trades.length) return [];
  const out: number[] = [];
  for (let i = 0; i < trades.length; i++) {
    const start = Math.max(0, i - window + 1);
    let wins = 0;
    for (let j = start; j <= i; j++) if (trades[j].pnl > 0) wins += 1;
    out.push((wins / (i - start + 1)) * 100);
  }
  return out;
}

function buildRollingAvgTrade(trades: Trade[], window = 20): number[] {
  if (!trades.length) return [];
  const out: number[] = [];
  for (let i = 0; i < trades.length; i++) {
    const start = Math.max(0, i - window + 1);
    let sum = 0;
    for (let j = start; j <= i; j++) sum += trades[j].pnl;
    out.push(sum / (i - start + 1));
  }
  return out;
}

function buildCumulativePnl(trades: Trade[]): number[] {
  if (!trades.length) return [];
  const out: number[] = [];
  let cum = 0;
  for (const t of trades) {
    cum += t.pnl;
    out.push(cum);
  }
  return out;
}

// Reconstruct a running-capital equity curve from the trade ledger. The backend
// result does not carry an `equityCurve`, so every consumer that reads
// `result.equityCurve` was rendering blank ("No equity curve captured"). Trades
// are always persisted with per-trade `pnl`, so we seed at initial capital and
// accumulate — the first point is the starting balance, then one point per exit.
function buildEquityCurveFromTrades(
  trades: Trade[],
  initialCapital: number,
): Array<{ timestamp: string; value: number }> {
  if (!trades.length) return [];
  const pts: Array<{ timestamp: string; value: number }> = [
    { timestamp: trades[0].entryTime || trades[0].exitTime || '', value: initialCapital },
  ];
  let cap = initialCapital;
  for (const t of trades) {
    cap += t.pnl;
    pts.push({ timestamp: t.exitTime || t.entryTime || '', value: cap });
  }
  return pts;
}

// Prefer the backend curve when present; otherwise reconstruct from trades.
function resolveEquityCurve(
  result: { equityCurve?: Array<{ timestamp: string; value: number }>; initialCapital: number },
  trades: Trade[],
): Array<{ timestamp: string; value: number }> {
  const provided = result.equityCurve ?? [];
  if (provided.length >= 2) return provided;
  return buildEquityCurveFromTrades(trades, result.initialCapital);
}

// ── Recent Runs ──────────────────────────────────────────────────────────────
// Three fixed semantic slots (BTCAAAAA-38676):
//   • Current  — the run being viewed (newest manual backtest).
//   • Previous — the prior manual backtest, or a muted placeholder when none.
//   • Best     — the best-returning Config Discovery run, or a subtle note when
//                discovery has not been run (or looks stale after newer runs).
// Every slot keeps the same fixed row height so Apply never reflows the layout.
// Run history lives in localStorage, so it is read in an effect to avoid an
// SSR/client hydration mismatch.

type RunSlot = 'current' | 'previous' | 'best';

const SLOT_LABEL: Record<RunSlot, string> = {
  current: 'Current',
  previous: 'Previous',
  best: 'Best',
};

const SLOT_COLOR: Record<RunSlot, string> = {
  current: 'var(--accent-blue)',
  previous: 'var(--text-muted)',
  best: 'var(--accent-amber)',
};

// Config Discovery persists each swept run through recordCompareCard with a
// strategyName of `"<name> · <label>"`; the " · " separator is the marker that
// tells discovery runs apart from plain manual backtests in the shared history.
function isDiscoveryRun(record: BacktestRunRecord): boolean {
  return record.strategyName.includes(' · ');
}

function SlotBadge({ slot, applied }: { slot: RunSlot; applied?: boolean }) {
  // BTCAAAAA-38883: when the run on screen came from Apply (not a fresh
  // backtest), the Current slot is relabelled "Applied" in amber so the user
  // knows the metrics no longer describe their latest manual run.
  const label = slot === 'current' && applied ? 'Applied' : SLOT_LABEL[slot];
  const color = slot === 'current' && applied ? SLOT_COLOR.best : SLOT_COLOR[slot];
  return (
    <div className="w-[68px] flex-shrink-0 flex items-center gap-1">
      {slot === 'best' && <Trophy size={11} style={{ color: SLOT_COLOR.best }} />}
      <span className="text-[10px] font-semibold uppercase tracking-wide" style={{ color }}>
        {label}
      </span>
    </div>
  );
}

// Length of the backtest window — different windows make return % incomparable,
// so each card surfaces its own duration (BTCAAAAA-38883).
function fmtTestDuration(start?: string, end?: string): string {
  if (!start || !end) return '—';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms) || ms <= 0) return '—';
  const days = ms / 86_400_000;
  if (days >= 1) return `${Math.round(days)}d`;
  return `${Math.max(1, Math.round(ms / 3_600_000))}h`;
}

function RecentRunsSection({
  strategyId,
  currentRunId,
  onApplyConfig,
  appliedRunId,
  onRollbackApply,
}: {
  strategyId?: string;
  currentRunId?: string;
  onApplyConfig?: (record: BacktestRunRecord) => void;
  appliedRunId?: string | null;
  onRollbackApply?: () => void;
}) {
  const [records, setRecords] = useState<BacktestRunRecord[]>([]);
  // BTCAAAAA-38790: the header Aa−/Aa+ control scales the small text inside the
  // Recent Runs cards (run name, WR/tr/DD stats, stale note) — but NOT the
  // "Recent Runs" section header, which stays fixed like other titles.
  const fontSizes = useFontSizes();

  useEffect(() => {
    const all = strategyId ? loadRunRecordsForStrategy(strategyId) : loadAllRunRecords();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reads persisted run records from localStorage after mount to avoid an SSR/client hydration mismatch
    setRecords(all);
  }, [strategyId, currentRunId]);

  const fmtDateTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch { return iso; }
  };

  // History is newest-first. Split it into plain manual backtests and the runs
  // produced by Config Discovery so each slot draws from the right pool.
  const manual = records.filter(r => !isDiscoveryRun(r));
  const discovery = records.filter(isDiscoveryRun);

  // Current = the run actually on screen — including a discovery run loaded
  // via Apply (BTCAAAAA-38883: the slot must replace, not lag behind, the
  // applied run) — falling back to the newest manual run.
  const current =
    (currentRunId ? records.find(r => r.runId === currentRunId) : undefined) ?? manual[0] ?? null;
  // Previous = the newest manual run that is not the current one.
  const previous = manual.find(r => r.runId !== current?.runId) ?? null;
  // Best = the highest-returning discovery run.
  const best = discovery.length
    ? discovery.reduce((a, b) => (b.result.returnPercentage > a.result.returnPercentage ? b : a))
    : null;
  // Discovery looks stale once a manual run is saved after the latest sweep —
  // the config it explored no longer matches what the user is now testing.
  const newestDiscoveryAt = discovery.reduce(
    (max, r) => Math.max(max, new Date(r.savedAt).getTime()), 0);
  const discoveryStale =
    best != null && current != null && new Date(current.savedAt).getTime() > newestDiscoveryAt;

  const runCard = (record: BacktestRunRecord, slot: RunSlot) => {
    const r = record.result;
    const equityVals = resolveEquityCurve(r, r.trades ?? []).map(p => p.value);
    const up = r.finalCapital - r.initialCapital >= 0;
    const accent = up ? 'var(--accent-green)' : 'var(--accent-red)';
    const isApplied = appliedRunId != null && record.runId === appliedRunId;
    return (
      <div
        className="rounded p-3 flex flex-col gap-2 h-full"
        style={{
          background: 'var(--bg-card)',
          border: isApplied ? '1px solid rgba(245,158,11,0.45)' : '1px solid var(--border)',
        }}
      >
        {/* Header — slot badge + return % */}
        <div className="flex items-center justify-between gap-2">
          <SlotBadge slot={slot} applied={isApplied} />
          <RichTooltip content={TT_RECENT_RUN_RETURN}>
            <span className="text-base font-bold tabular-nums leading-none cursor-help" style={{ color: accent }}>
              {r.returnPercentage >= 0 ? '+' : ''}{r.returnPercentage.toFixed(2)}%
            </span>
          </RichTooltip>
        </div>
        {/* Run identity — date + strategy name */}
        <div className="min-w-0">
          <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-secondary)' }}>
            {fmtDateTime(record.savedAt)}
          </p>
          <p className="text-[10px] truncate mt-0.5" style={{ color: 'var(--text-faint)' }}>{record.strategyName}</p>
        </div>
        {/* Equity sparkline */}
        <div className="h-10 flex items-center">
          {equityVals.length >= 2 ? (
            <Sparkline values={equityVals} color={accent} fillBelow height={40} />
          ) : (
            <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>No equity curve captured</p>
          )}
        </div>
        {/* Stats — WR / trades / drawdown spread across the card width */}
        <div className="flex flex-row items-center justify-between leading-tight text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
          <RichTooltip content={TT_RECENT_RUN_WR}><span className="cursor-help">WR {(r.winRate * 100).toFixed(0)}%</span></RichTooltip>
          <RichTooltip content={TT_RECENT_RUN_TRADES}><span className="cursor-help">{r.totalTrades} tr</span></RichTooltip>
          <RichTooltip content={TT_RECENT_RUN_DD}><span className="cursor-help">DD {(r.maxDrawdown * 100).toFixed(1)}%</span></RichTooltip>
          <RichTooltip content={TT_RECENT_RUN_DURATION}><span className="cursor-help">{fmtTestDuration(r.startDate, r.endDate)}</span></RichTooltip>
        </div>
        {/* Apply / Roll Back — full-width, pinned to the bottom so cards align.
            The card whose config is currently applied flips to an amber Roll
            Back that restores the pre-Apply run (BTCAAAAA-38883). */}
        {isApplied && onRollbackApply ? (
          <button
            onClick={onRollbackApply}
            className="mt-auto w-full flex items-center justify-center gap-1 text-[11px] px-2.5 py-1 rounded"
            title="Restore the run you were viewing before Apply"
            style={{ color: 'var(--accent-amber)', border: '1px solid rgba(245,158,11,0.4)', background: 'rgba(245,158,11,0.10)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(245,158,11,0.2)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(245,158,11,0.10)')}
          >
            <Undo2 size={12} />Roll Back
          </button>
        ) : onApplyConfig && record.fullConfig ? (
          <button
            onClick={() => onApplyConfig(record)}
            className="mt-auto w-full flex items-center justify-center gap-1 text-[11px] px-2.5 py-1 rounded"
            title="Apply this run's configuration to the Config tab"
            style={{ color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.35)', background: 'rgba(46,140,255,0.08)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(46,140,255,0.18)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(46,140,255,0.08)')}
          >
            <Download size={12} />Apply
          </button>
        ) : null}
      </div>
    );
  };

  // Muted, dashed-border placeholder — fills the column height so the
  // three-column layout never shifts when a slot has no data yet.
  const placeholderCard = (slot: RunSlot, message: string) => (
    <div
      className="rounded p-3 flex flex-col gap-2 h-full"
      style={{ background: 'var(--bg-card)', border: '1px dashed var(--border)', opacity: 0.6 }}
    >
      <SlotBadge slot={slot} />
      <p className="text-[11px] min-w-0" style={{ color: 'var(--text-faint)' }}>{message}</p>
    </div>
  );

  return (
    <>
      <SectionHeader title="Recent Runs" subtitle="Current & previous backtests plus the best Config Discovery result — apply any run's configuration" />
      {/* zoom scales only the small card text with the header font control (BTCAAAAA-38790) */}
      <div style={{ zoom: fontSizes.smallScale }}>
        <div className="grid grid-cols-3 gap-3 items-stretch">
          {current ? runCard(current, 'current') : placeholderCard('current', 'No backtest run yet')}
          {previous ? runCard(previous, 'previous') : placeholderCard('previous', 'No previous run')}
          {best ? runCard(best, 'best') : placeholderCard('best', 'Config Discovery not run yet')}
        </div>
        {best && discoveryStale && (
          <p className="text-[10px] pl-1 mt-2" style={{ color: 'var(--text-faint)' }}>
            Config Discovery may be stale — a newer backtest has run since the last sweep.
          </p>
        )}
      </div>
    </>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export function MetricsPanel({ result, trades = [], strategyId, onApplyConfig, appliedRunId, onRollbackApply, leverage, riskPerTradePct }: MetricsPanelProps) {
  const [showAdditional, setShowAdditional] = useState(true);
  // BTCAAAAA-38790 (reopen): the header Aa−/Aa+ control must reach every
  // small-text card grid on this tab — not just Recent Runs. Section headers
  // and the large hero KPIs stay fixed; each card grid below zooms.
  const fontSizes = useFontSizes();
  const smallZoom = { zoom: fontSizes.smallScale } as const;

  // All hooks must run unconditionally — compute series for the result we
  // were given (even if null) so the hook order stays stable across renders.
  const allTrades = useMemo<Trade[]>(
    () => (result ? (trades.length > 0 ? trades : (result.trades ?? [])) : []),
    [result, trades],
  );

  // Per-metric sparkline series — cheap O(N) over ≤500 trades typical,
  // recomputed only when the trade list changes.
  const sparkCumCount = useMemo(() => buildCumulativeCount(allTrades), [allTrades]);
  const sparkPerDay = useMemo(() => buildTradesPerDay(allTrades), [allTrades]);
  const sparkCumWinLoss = useMemo(() => buildCumulativeWinLoss(allTrades), [allTrades]);
  const sparkRollingWR = useMemo(() => buildRollingWinRate(allTrades), [allTrades]);
  const sparkRollingAvg = useMemo(() => buildRollingAvgTrade(allTrades), [allTrades]);
  const sparkCumPnl = useMemo(() => buildCumulativePnl(allTrades), [allTrades]);

  // BTCAAAAA-66772: per-entry-signal diagnostics for the dedicated Strategy
  // Signals grid. Trade.entrySignals is the only signal-level telemetry the
  // engine currently emits (src/api/app.py normalization); win rate, total
  // PnL, avg PnL and top co-fires per signal all derive from it. Per-trade
  // confluence scores are NOT yet exposed (lives only in
  // ValidationReport.confluenceScoring — validation context, not backtest
  // results), so the section's tooltips state the co-fire proxy explicitly.
  const entrySignalStats = useMemo<Array<{
    signal: string;
    fired: number;
    wins: number;
    losses: number;
    winRate: number;
    totalPnl: number;
    avgPnl: number;
    topCoFires: Array<{ signal: string; count: number }>;
  }>>(() => {
    type Row = {
      signal: string;
      fired: number;
      wins: number;
      losses: number;
      winRate: number;
      totalPnl: number;
      avgPnl: number;
      topCoFires: Array<{ signal: string; count: number }>;
    };
    const counts = new Map<string, number>();
    const winsBySig = new Map<string, number>();
    const pnlBySig = new Map<string, number>();
    const coFire = new Map<string, Map<string, number>>();
    for (const t of allTrades) {
      const sigs = t.entrySignals ?? [];
      if (sigs.length === 0) continue;
      const win = t.pnl > 0;
      for (const s of sigs) {
        counts.set(s, (counts.get(s) ?? 0) + 1);
        if (win) winsBySig.set(s, (winsBySig.get(s) ?? 0) + 1);
        pnlBySig.set(s, (pnlBySig.get(s) ?? 0) + t.pnl);
      }
      const unique = Array.from(new Set(sigs)).sort();
      for (let i = 0; i < unique.length; i++) {
        for (let j = i + 1; j < unique.length; j++) {
          const a = unique[i];
          const b = unique[j];
          let inner = coFire.get(a);
          if (!inner) { inner = new Map(); coFire.set(a, inner); }
          inner.set(b, (inner.get(b) ?? 0) + 1);
        }
      }
    }
    const rows: Row[] = [];
    for (const [signal, fired] of counts) {
      const wins = winsBySig.get(signal) ?? 0;
      const totalPnl = pnlBySig.get(signal) ?? 0;
      const losses = fired - wins;
      const winRate = fired > 0 ? wins / fired : 0;
      const avgPnl = fired > 0 ? totalPnl / fired : 0;
      const inner = coFire.get(signal);
      const topCoFires = inner
        ? [...inner.entries()]
            .map(([s, c]) => ({ signal: s, count: c }))
            .sort((a, b) => b.count - a.count || a.signal.localeCompare(b.signal))
            .slice(0, 3)
        : [];
      rows.push({ signal, fired, wins, losses, winRate, totalPnl, avgPnl, topCoFires });
    }
    rows.sort((a, b) => b.fired - a.fired || a.signal.localeCompare(b.signal));
    return rows;
  }, [allTrades]);

  // BTCAAAAA-66772: derive the 4 building-block signal cards (Signals Required
  // / Rechecks / Exit Signals / Stop-Loss Adjustments) from Trade data so they
  // stop rendering as "—". All four are scalar summaries of the per-trade
  // record — they sit at the top of the new Strategy Signals section so the
  // missing-confluence/per-trade-rechecks caveats in the tooltips sit next
  // to the live per-signal table the engine DOES expose.
  //
  //   Signals Required       → mean entry-signal count per trade (a multi-
  //                             signal strategy should average > 1; mono-
  //                             signal strategies render 1.0).
  //   Rechecks               → Σ(max(0, len(entrySignals) - 1)) across trades
  //                             — every signal after the first is treated as
  //                             a confirmation/recheck. This is a proxy: true
  //                             recheck events from the engine (BTC-37920 v3
  //                             building block) would be a per-trade array,
  //                             but the sum-of-extra-signals metric
  //                             communicates the same idea at this layer.
  //   Exit Signals           → # trades whose exitType looks signal-driven
  //                             (SIGNAL_EXIT / EXIT_SIGNAL / SIGNAL /
  //                             REVERSAL).
  //   Stop-Loss Adjustments  → # trades whose exitType looks like a trailing
  //                             or adaptive SL move (TRAILING_SL / TRAILING /
  //                             ADAPTIVE_SL / ADAPTIVE). Distinct from raw
  //                             SL exits — the engine names them differently
  //                             when the stop was adjusted mid-trade.
  const signalSummary = useMemo(() => {
    const isSignalExit = (e?: string | null) => {
      if (!e) return false;
      const u = e.toUpperCase();
      return u === 'SIGNAL_EXIT' || u === 'EXIT_SIGNAL' || u === 'SIGNAL'
        || u === 'REVERSAL' || u.includes('SIGNAL_EXIT');
    };
    const isSlAdjust = (e?: string | null) => {
      if (!e) return false;
      const u = e.toUpperCase();
      return u === 'TRAILING_SL' || u === 'TRAILING' || u === 'ADAPTIVE_SL'
        || u === 'ADAPTIVE' || u.includes('TRAIL') || u.includes('ADAPTIVE');
    };
    let signalSum = 0;
    let signalCount = 0;
    let rechecks = 0;
    let exitSignals = 0;
    let slAdjustments = 0;
    for (const t of allTrades) {
      const sigs = t.entrySignals ?? [];
      if (sigs.length > 0) {
        signalSum += sigs.length;
        signalCount += 1;
        if (sigs.length > 1) rechecks += sigs.length - 1;
      }
      if (isSignalExit(t.exitType)) exitSignals += 1;
      if (isSlAdjust(t.exitType)) slAdjustments += 1;
    }
    return {
      signalsRequiredAvg: signalCount > 0 ? signalSum / signalCount : 0,
      rechecksTotal: rechecks,
      exitSignalCount: exitSignals,
      slAdjustmentCount: slAdjustments,
      hasTelemetry: signalCount > 0 || allTrades.length === 0,
    };
  }, [allTrades]);

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-12" style={{ color: 'var(--text-faint)' }}>
        <p className="text-sm">No results yet.</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Run a backtest to see performance metrics.</p>
      </div>
    );
  }

  const tradeStats = computeTradeStats(allTrades);

  const winPct = (result.winRate * 100).toFixed(1);
  const lossRate = 1 - result.winRate;
  const netProfit = result.finalCapital - result.initialCapital;
  const rrRatio = result.averageLoss !== 0
    ? (Math.abs(result.averageWin) / Math.abs(result.averageLoss)).toFixed(2)
    : '—';
  const expectancy = (result.winRate * result.averageWin) + (lossRate * result.averageLoss);
  const breakevenWinRate = Math.abs(result.averageLoss) + Math.abs(result.averageWin) > 0
    ? (Math.abs(result.averageLoss) / (Math.abs(result.averageWin) + Math.abs(result.averageLoss)) * 100).toFixed(1)
    : '—';

  const formatDate = (d: string) => { try { return new Date(d).toLocaleDateString(); } catch { return d; } };
  const durationDays = result.startDate && result.endDate
    ? Math.round((new Date(result.endDate).getTime() - new Date(result.startDate).getTime()) / 86_400_000)
    : null;

  // Equity curve + drawdown series for the Performance sparklines.
  const equityCurve = resolveEquityCurve(result, allTrades);
  const equityValues = equityCurve.map(p => p.value);
  const equityTimestamps = equityCurve.map(p => p.timestamp);
  let drawdownPcts: number[] = [];
  if (equityValues.length > 0) {
    let peak = equityValues[0];
    drawdownPcts = equityValues.map(v => {
      if (v > peak) peak = v;
      return peak > 0 ? ((v - peak) / peak) * 100 : 0;
    });
  }
  const recoveryFactor = (result.maxDrawdown * result.initialCapital) !== 0
    ? (netProfit / Math.abs(result.maxDrawdown * result.initialCapital)).toFixed(2)
    : '—';

  // ── Draw Down analytics ───────────────────────────────────────────────────
  // Underwater dollar series (value below the running peak) and the run of
  // consecutive underwater points give the operator a read on both damage
  // depth and how long capital stayed impaired. Liquidation buffer estimates
  // how much headroom remains before a leveraged position would be wiped:
  // a 1/leverage adverse move is a full liquidation, so the buffer is the gap
  // between that threshold and the worst realised drawdown.
  const ddDollarSeries: number[] = [];
  if (equityValues.length > 0) {
    let peak = equityValues[0];
    for (const v of equityValues) {
      if (v > peak) peak = v;
      ddDollarSeries.push(v - peak);
    }
  }
  const maxDDpctVal = drawdownPcts.length > 0 ? Math.min(...drawdownPcts) : 0;
  const maxDDDollarVal = ddDollarSeries.length > 0 ? Math.min(...ddDollarSeries) : 0;
  const peakCapital = equityValues.length > 0 ? Math.max(...equityValues) : result.initialCapital;
  let longestDDRun = 0;
  {
    let run = 0;
    for (const d of drawdownPcts) {
      if (d < 0) { run += 1; longestDDRun = Math.max(longestDDRun, run); }
      else run = 0;
    }
  }
  const liquidationThresholdPct = leverage && leverage > 0 ? 100 / leverage : null;
  const liquidationBufferPct = liquidationThresholdPct != null
    ? liquidationThresholdPct - Math.abs(maxDDpctVal)
    : null;
  // BTCAAAAA-66757: a strategy is "liquidated" when the worst realised drawdown
  // equals or exceeds the ~1/leverage liquidation move — at that point the
  // leveraged position would have been wiped and the configuration must be
  // flagged as non-publishable. Drives the red-pulse banner + glow.
  const isLiquidated = liquidationBufferPct != null && liquidationBufferPct < 0;
  const sharpeStr = allTrades.length >= 2 ? result.sharpeRatio.toFixed(2) : '—';
  const sortinoStr = allTrades.length >= 2 && result.losingTrades > 0
    ? result.sortino_ratio.toFixed(2)
    : '—';
  const calmarStr = result.maxDrawdown > 0 && result.calmar_ratio != null
    ? result.calmar_ratio.toFixed(2)
    : '—';
  const avgHoldingBars = tradeStats && tradeStats.avgBars > 0 ? tradeStats.avgBars.toFixed(1) : '—';

  const totalBarsHeld = allTrades.reduce((s, t) => s + (t.bars ?? 0), 0);
  const exposurePct = result.totalBars && result.totalBars > 0
    ? (totalBarsHeld / result.totalBars) * 100
    : null;

  const symbol = allTrades.find(t => t.symbol)?.symbol ?? null;

  /* ── Buy & Hold delta (webui-only approximation) ───────────────────────── */
  const bhDelta = computeBuyHoldDelta(allTrades);
  const strategyReturn = result.returnPercentage;
  const strategyDeltaVsBh = bhDelta ? strategyReturn - bhDelta.pct : null;
  const strategyAbsVsBh = bhDelta ? (netProfit) - (result.initialCapital * bhDelta.pct / 100) : null;
  const drawdownVsBh = bhDelta ? (result.maxDrawdown * 100) - (-Math.abs(bhDelta.pct)) : null;

  const sparkEquity = equityValues;
  const sparkDrawdown = drawdownPcts;

  /* ── Enrichment metrics (BTCAAAAA-35862) ─────────────────────────────────── */
  const annualizedReturn = durationDays && durationDays > 7
    ? (Math.pow(1 + strategyReturn / 100, 365 / durationDays) - 1) * 100
    : null;
  const breakevenNum = parseFloat(breakevenWinRate);
  const marginOfSafety = !isNaN(breakevenNum) ? parseFloat(winPct) - breakevenNum : null;
  const rrNum = parseFloat(rrRatio);
  const kellyCriterion = !isNaN(rrNum) && rrNum > 0 && result.averageLoss !== 0
    ? result.winRate - (lossRate / rrNum)
    : null;

  /* ── Hero strip (4 large KPIs from mockup) ─────────────────────────────── */
  const heroCards = [
    {
      label: 'Total Return',
      value: `${strategyReturn >= 0 ? '+' : ''}${strategyReturn.toFixed(2)}%`,
      valueColor: strategyReturn >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: strategyReturn >= 0 ? TrendingUp : TrendingDown,
      accent: (strategyReturn >= 0 ? 'green' : 'red') as Accent,
      deltaPct: strategyDeltaVsBh,
      deltaText: formatBuyHoldDeltaPct(bhDelta),
      tooltip: TT_TOTAL_RETURN,
    },
    {
      label: 'Net Profit',
      value: `${netProfit >= 0 ? '+' : ''}$${netProfit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      valueColor: netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: DollarSign,
      accent: (netProfit >= 0 ? 'green' : 'red') as Accent,
      deltaPct: strategyAbsVsBh,
      deltaText: formatBuyHoldDeltaDollar(bhDelta, result.initialCapital),
      tooltip: TT_NET_PROFIT,
    },
    {
      label: 'Max Drawdown',
      value: `${(result.maxDrawdown * 100).toFixed(2)}%`,
      valueColor: 'var(--accent-orange)',
      icon: AlertTriangle,
      accent: 'orange' as Accent,
      deltaPct: drawdownVsBh,
      deltaText: formatBuyHoldDeltaScalar(bhDelta),
      tooltip: TT_MAX_DRAWDOWN,
    },
    {
      label: 'Sharpe Ratio',
      value: sharpeStr,
      valueColor: Number(sharpeStr) >= 1 ? 'var(--accent-green)'
        : Number(sharpeStr) >= 0 ? 'var(--accent-blue)'
        : 'var(--accent-red)',
      icon: Activity,
      accent: (Number(sharpeStr) >= 1 ? 'green' : Number(sharpeStr) >= 0 ? 'blue' : 'red') as Accent,
      deltaPct: null,
      deltaText: bhDelta ? 'Buy&Hold Sharpe: not computed' : '—',
      tooltip: TT_SHARPE,
    },
  ];

  /* ── Risk Metrics (6 sparkline cards in mockup 3×2) ─────────────────────── */
  const riskSparklineCards = [
    {
      label: 'Volatility (σ)',
      value: tradeStats?.returnVolatility != null ? `${tradeStats.returnVolatility.toFixed(2)}%` : '—',
      icon: BarChart2,
      accent: 'neutral' as Accent,
      sparkValues: sparkRollingAvg,
      sparkColor: 'var(--accent-blue)',
      tooltip: TT_VOLATILITY,
    },
    {
      label: 'Sortino Ratio',
      value: sortinoStr,
      icon: BarChart3,
      accent: 'blue' as Accent,
      sparkValues: sparkEquity,
      sparkColor: 'var(--accent-blue)',
      tooltip: TT_SORTINO,
    },
    {
      label: 'Calmar Ratio',
      value: calmarStr,
      icon: LineChart,
      accent: 'blue' as Accent,
      sparkValues: sparkDrawdown,
      sparkColor: 'var(--accent-orange)',
      tooltip: TT_CALMAR,
    },
    {
      label: 'Recovery Factor',
      value: recoveryFactor,
      valueColor: Number(recoveryFactor) >= 1 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: RotateCcw,
      accent: (Number(recoveryFactor) >= 1 ? 'green' : 'red') as Accent,
      sparkValues: sparkCumPnl,
      sparkColor: Number(recoveryFactor) >= 1 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_MAX_DRAWDOWN,
    },
    {
      label: 'Win Rate',
      value: `${winPct}%`,
      valueColor: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: Target,
      accent: (result.winRate >= 0.5 ? 'green' : 'red') as Accent,
      sparkValues: sparkRollingWR,
      sparkColor: 'var(--accent-green)',
      tooltip: TT_WIN_RATE,
    },
    {
      label: 'Profit Factor',
      value: result.profitFactor.toFixed(2),
      valueColor: result.profitFactor >= 1 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: Scale,
      accent: (result.profitFactor >= 1 ? 'green' : 'red') as Accent,
      sparkValues: sparkCumPnl,
      sparkColor: result.profitFactor >= 1 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_PROFIT_FACTOR,
    },
  ];

  /* ── Trade Statistics (6 sparkline cards in mockup 3×2) ─────────────────── */
  const tradeSparklineCards = [
    {
      label: 'Trades',
      value: String(result.totalTrades),
      icon: Hash,
      accent: 'neutral' as Accent,
      sparkValues: sparkCumCount,
      sparkColor: 'var(--accent-blue)',
      tooltip: TT_TOTAL_TRADES,
    },
    {
      label: 'Trades/Day',
      value: sparkPerDay.length > 0
        ? (allTrades.length / sparkPerDay.length).toFixed(2)
        : '—',
      icon: Layers,
      accent: 'neutral' as Accent,
      sparkValues: sparkPerDay,
      sparkColor: 'var(--accent-blue)',
      tooltip: TT_TOTAL_TRADES,
    },
    {
      label: 'Winning',
      value: String(result.winningTrades),
      valueColor: 'var(--accent-green)',
      icon: ArrowUp,
      accent: 'green' as Accent,
      sparkValues: sparkCumWinLoss.wins,
      sparkColor: 'var(--accent-green)',
      tooltip: TT_WINNING_TRADES,
    },
    {
      label: 'Losing',
      value: String(result.losingTrades),
      valueColor: 'var(--accent-red)',
      icon: ArrowDown,
      accent: 'red' as Accent,
      sparkValues: sparkCumWinLoss.losses,
      sparkColor: 'var(--accent-red)',
      tooltip: TT_LOSING_TRADES,
    },
    {
      label: 'Avg Trade',
      value: `${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`,
      valueColor: expectancy >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      icon: PercentIcon,
      accent: (expectancy >= 0 ? 'green' : 'red') as Accent,
      sparkValues: sparkRollingAvg,
      sparkColor: expectancy >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_EXPECTANCY,
    },
    {
      label: 'Avg Win',
      value: `+$${result.averageWin.toFixed(2)}`,
      valueColor: 'var(--accent-green)',
      icon: TrendingUp,
      accent: 'green' as Accent,
      sparkValues: sparkCumPnl,
      sparkColor: 'var(--accent-green)',
      tooltip: TT_AVG_WIN,
    },
  ];

  /* ── Backtest Period (5 InfoCards from mockup strip) ─────────────────────── */
  const periodCards = [
    {
      label: 'Period',
      value: result.startDate && result.endDate
        ? `${formatDate(result.startDate)} → ${formatDate(result.endDate)}`
        : (result.startDate ? formatDate(result.startDate) : '—'),
      icon: Calendar,
      accent: 'neutral' as Accent,
      subValue: durationDays != null ? `${durationDays} days` : undefined,
      tooltip: TT_START_DATE,
    },
    {
      label: 'Duration',
      value: durationDays != null ? `${durationDays} days` : '—',
      icon: Clock,
      accent: 'neutral' as Accent,
      subValue: durationDays != null
        ? `≈ ${(durationDays / 30.44).toFixed(1)} months`
        : undefined,
      tooltip: TT_DURATION,
    },
    {
      label: 'Bars / Trades',
      value: result.totalBars != null
        ? `${result.totalBars.toLocaleString()} bars`
        : '—',
      icon: BarChart3,
      accent: 'neutral' as Accent,
      subValue: `${result.totalTrades} trades`,
      tooltip: TT_BARS_ANALYZED,
    },
    {
      label: 'Capital',
      value: `$${result.initialCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })} → $${result.finalCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
      icon: DollarSign,
      accent: (netProfit >= 0 ? 'green' : 'red') as Accent,
      subValue: `${netProfit >= 0 ? '+' : ''}$${Math.abs(netProfit).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      tooltip: TT_INITIAL_CAPITAL,
    },
    {
      label: 'Pair / Currency',
      value: symbol ?? '—',
      icon: Coins,
      accent: 'neutral' as Accent,
      subValue: 'USDT',
      tooltip: TT_CURRENCY,
    },
  ];

  /* ── Additional metrics (preserves v1 surface under a "show more" expander) */
  const additionalRows: MetricRow[] = [
    { label: 'Recovery Factor', value: recoveryFactor, color: Number(recoveryFactor) >= 1 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_MAX_DRAWDOWN, icon: RotateCcw, accent: Number(recoveryFactor) >= 1 ? 'green' : 'red' },
    { label: 'Risk / Reward', value: rrRatio, tooltip: TT_RISK_REWARD, icon: Scale, accent: 'neutral' },
    {
      label: 'VaR 95%', value: tradeStats?.var95 != null ? `${tradeStats.var95.toFixed(2)}%` : '—',
      color: tradeStats?.var95 != null ? 'var(--accent-red)' : undefined,
      tooltip: TT_VAR_95, icon: AlertOctagon, accent: 'red',
      baseline: tradeStats?.var95 == null ? 'requires ≥20 trades' : undefined,
    },
    {
      label: 'CVaR 95%', value: tradeStats?.cvar95 != null ? `${tradeStats.cvar95.toFixed(2)}%` : '—',
      color: tradeStats?.cvar95 != null ? 'var(--accent-red)' : undefined,
      tooltip: TT_CVAR_95, icon: AlertOctagon, accent: 'red',
      baseline: tradeStats?.cvar95 == null ? 'requires ≥20 trades' : undefined,
    },
    { label: 'Exposure Time', value: exposurePct != null ? `${exposurePct.toFixed(1)}%` : '—', tooltip: TT_EXPOSURE_TIME, icon: Clock, accent: 'blue' },
    {
      label: 'Payoff Ratio', value: tradeStats && tradeStats.lossesSum > 0
        ? (tradeStats.winsSum / tradeStats.lossesSum).toFixed(2)
        : '—',
      tooltip: TT_PAYOFF_RATIO, icon: Percent, accent: 'neutral',
    },
    { label: 'Largest Win', value: tradeStats ? `${tradeStats.largestWin >= 0 ? '+' : ''}$${tradeStats.largestWin.toFixed(2)}` : '—', color: 'var(--accent-green)', tooltip: TT_LARGEST_WIN, icon: ArrowUpCircle, accent: 'green' },
    { label: 'Largest Loss', value: tradeStats ? `-$${Math.abs(tradeStats.largestLoss).toFixed(2)}` : '—', color: 'var(--accent-red)', tooltip: TT_LARGEST_LOSS, icon: ArrowDownCircle, accent: 'red' },
    { label: 'Breakeven Win%', value: `${breakevenWinRate}%`, tooltip: TT_BREAKEVEN_WIN, icon: Sparkles, accent: 'neutral' },
    { label: 'Avg Loss', value: `-$${Math.abs(result.averageLoss).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_AVG_LOSS, icon: TrendingDown, accent: 'red' },
  ];

  if (tradeStats) {
    additionalRows.push(
      { label: 'Best Trade', value: `${tradeStats.bestTrade >= 0 ? '+' : ''}$${tradeStats.bestTrade.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT_BEST_TRADE, icon: Trophy, accent: 'green' },
      { label: 'Worst Trade', value: `-$${Math.abs(tradeStats.worstTrade).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_WORST_TRADE, icon: Skull, accent: 'red' },
      { label: 'Avg Bars Held', value: tradeStats.avgBars.toFixed(1), tooltip: TT_AVG_BARS, icon: Clock, accent: 'neutral' },
      { label: 'Max Consec. Wins', value: String(tradeStats.maxConsecWins), color: 'var(--accent-green)', tooltip: TT_MAX_CONSEC_WINS, icon: ArrowUpCircle, accent: 'green' },
      { label: 'Max Consec. Losses', value: String(tradeStats.maxConsecLosses), color: 'var(--accent-red)', tooltip: TT_MAX_CONSEC_LOSSES, icon: ArrowDownCircle, accent: 'red' },
    );
    if (tradeStats.longs + tradeStats.shorts > 0) {
      additionalRows.push(
        { label: 'Long Trades', value: String(tradeStats.longs), tooltip: TT_LONG_TRADES, icon: ArrowUp, accent: 'green' },
        { label: 'Short Trades', value: String(tradeStats.shorts), tooltip: TT_SHORT_TRADES, icon: ArrowDown, accent: 'red' },
      );
    }
    for (const [exitType, count] of Object.entries(tradeStats.exitTypes)) {
      if (exitType === 'Unknown') continue;
      const pct = ((count / tradeStats.count) * 100).toFixed(0);
      additionalRows.push({ label: `Exit: ${exitType}`, value: `${count} (${pct}%)`, tooltip: TT_EXIT_TYPE(exitType, count, tradeStats.count), icon: BarChart3, accent: 'neutral' });
    }
    additionalRows.push({ label: 'Avg Holding (bars)', value: avgHoldingBars, tooltip: TT_AVG_BARS, icon: Clock, accent: 'neutral' });
    if (tradeStats.returnVolatility != null) {
      additionalRows.push({ label: 'Return σ (per trade %)', value: `${tradeStats.returnVolatility.toFixed(2)}%`, tooltip: TT_VOLATILITY, icon: BarChart2, accent: 'neutral' });
    }
  }

  /* Enrichment metrics (BTCAAAAA-35862) */
  if (annualizedReturn != null) {
    additionalRows.push({
      label: 'Annualized Return',
      value: `${annualizedReturn >= 0 ? '+' : ''}${annualizedReturn.toFixed(2)}%`,
      color: annualizedReturn >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_ANNUALIZED_RETURN, icon: TrendingUp,
      accent: (annualizedReturn >= 0 ? 'green' : 'red') as Accent,
    });
  }
  if (marginOfSafety != null) {
    additionalRows.push({
      label: 'Margin of Safety',
      value: `${marginOfSafety >= 0 ? '+' : ''}${marginOfSafety.toFixed(1)}%`,
      color: marginOfSafety >= 10 ? 'var(--accent-green)' : marginOfSafety >= 0 ? 'var(--accent-orange)' : 'var(--accent-red)',
      tooltip: TT_MARGIN_OF_SAFETY, icon: Sparkles,
      accent: (marginOfSafety >= 10 ? 'green' : marginOfSafety >= 0 ? 'orange' : 'red') as Accent,
    });
  }
  if (kellyCriterion != null) {
    const kellyPct = kellyCriterion * 100;
    additionalRows.push({
      label: 'Kelly Criterion',
      value: `${kellyPct.toFixed(1)}%`,
      color: kellyPct > 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_KELLY_CRITERION, icon: Activity,
      accent: (kellyPct > 0 ? 'green' : 'red') as Accent,
      baseline: `Half-Kelly: ${(kellyPct / 2).toFixed(1)}%`,
    });
  }
  if (tradeStats && tradeStats.winsSum > 0) {
    additionalRows.push(
      {
        label: 'Gross Profit',
        value: `+$${tradeStats.winsSum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        color: 'var(--accent-green)',
        tooltip: TT_GROSS_PROFIT, icon: ArrowUpCircle, accent: 'green' as Accent,
      },
      {
        label: 'Gross Loss',
        value: `-$${tradeStats.lossesSum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        color: 'var(--accent-red)',
        tooltip: TT_GROSS_LOSS, icon: ArrowDownCircle, accent: 'red' as Accent,
      },
    );
  }
  if (tradeStats?.longWinRate != null) {
    additionalRows.push({
      label: 'Long Win Rate',
      value: `${tradeStats.longWinRate.toFixed(1)}%`,
      color: tradeStats.longWinRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_LONG_WIN_RATE, icon: ArrowUp,
      accent: (tradeStats.longWinRate >= 50 ? 'green' : 'red') as Accent,
    });
  }
  if (tradeStats?.shortWinRate != null) {
    additionalRows.push({
      label: 'Short Win Rate',
      value: `${tradeStats.shortWinRate.toFixed(1)}%`,
      color: tradeStats.shortWinRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_SHORT_WIN_RATE, icon: ArrowDown,
      accent: (tradeStats.shortWinRate >= 50 ? 'green' : 'red') as Accent,
    });
  }
  if (tradeStats?.avgTradeDurationMs != null) {
    additionalRows.push({
      label: 'Avg Trade Duration',
      value: formatTradeDuration(tradeStats.avgTradeDurationMs),
      tooltip: TT_AVG_TRADE_DURATION, icon: Clock, accent: 'neutral' as Accent,
    });
  }

  /* Building-block signal diagnostics moved out of Additional Metrics per
     BTCAAAAA-66772: a dedicated "Strategy Signals" section now lives at the
     bottom of the panel with REAL entry-signal telemetry (Trade.entrySignals
     is already emitted by /api/backtest). The 4 building-block rows
     (Signals Required / Rechecks / Exit Signals / Stop-Loss Adjustments) that
     previously rendered as "—" here are surfaced under that new section
     header instead, so the missing-telemetry hint is properly contextualized
     against the live entry-signal table. */


  return (
    <div>
      {/* BTCAAAAA-66757 — liquidated banner: visible at the very top of the
          panel so the operator sees the configuration-failure flag before any
          KPI. Rendered only when the worst drawdown exceeded the ~1/leverage
          liquidation threshold; the strategy is then non-publishable.
          `mt-5` gives the same blank-row separation above the banner that
          the Overview wrapper uses below it (board comment 684e2da4). */}
      {isLiquidated && (
        <div
          className="liquidated-banner mt-5 mb-3"
          role="alert"
          aria-live="polite"
        >
          <AlertOctagon size={14} strokeWidth={2.2} aria-hidden="true" />
          <span className="font-semibold uppercase tracking-wide">Liquidated — non-publishable</span>
          <span className="text-[11px] font-normal opacity-90">
            Max drawdown {Math.abs(maxDDpctVal).toFixed(2)}% exceeded the {leverage}× liquidation threshold of −{liquidationThresholdPct!.toFixed(1)}%.
          </span>
        </div>
      )}

      {/* Hero strip: 4 large KPIs with vs-Buy&Hold deltas (mockup top row) */}
      {/* BTCAAAAA-66757 — wrapper div adds the blank row above the OVERVIEW
          header. The SectionHeader's own first:mt-0 collapses inside its parent,
          so the spacing lives on this wrapper to keep the SectionHeader API
          unchanged. */}
      <div className="mt-5">
        <SectionHeader title="Overview" subtitle="Top-line performance vs Buy & Hold benchmark" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {heroCards.map(card => (
          <HeroCard
            key={card.label}
            label={card.label}
            value={card.value}
            valueColor={card.valueColor}
            icon={card.icon}
            accent={card.accent}
            deltaPct={card.deltaPct}
            deltaText={card.deltaText}
            tooltip={card.tooltip}
          />
        ))}
        </div>
      </div>

      {/* Performance: equity + drawdown sparklines (preserved from v1) */}
      {equityValues.length >= 2 && (
        <>
          <SectionHeader title="Performance" subtitle="Equity curve and underwater drawdown from the run" />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-1.5">
                <RichTooltip content={TT_EQUITY_CURVE}>
                  <p className="text-xs font-medium cursor-help" style={{ color: 'var(--text-muted)' }}>Equity Curve</p>
                </RichTooltip>
                <p className="text-xs font-semibold" style={{ color: result.finalCapital >= result.initialCapital ? 'var(--accent-green)' : 'var(--accent-red)', fontVariantNumeric: 'tabular-nums' }}>
                  ${result.finalCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <Sparkline values={equityValues} color={result.finalCapital >= result.initialCapital ? 'var(--accent-green)' : 'var(--accent-red)'} fillBelow height={64} />
              <div className="flex items-center justify-between mt-1.5 text-[10px]" style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                <RichTooltip content={TT_INITIAL_CAPITAL}>
                  <span className="cursor-help">Initial ${result.initialCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </RichTooltip>
                <span aria-hidden="true"><ArrowRight size={11} /></span>
                <RichTooltip content={TT_FINAL_CAPITAL}>
                  <span className="cursor-help">Final ${result.finalCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </RichTooltip>
                {result.endDate && (
                  <>
                    <span aria-hidden="true"><ArrowRight size={11} /></span>
                    <RichTooltip content={TT_END_DATE}>
                      <span className="cursor-help">End {formatDate(result.endDate)}</span>
                    </RichTooltip>
                  </>
                )}
              </div>
            </div>
            <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-1.5">
                <RichTooltip content={TT_DRAWDOWN_CURVE}>
                  <p className="text-xs font-medium cursor-help" style={{ color: 'var(--text-muted)' }}>Drawdown</p>
                </RichTooltip>
                <p className="text-xs font-semibold" style={{ color: 'var(--accent-orange)', fontVariantNumeric: 'tabular-nums' }}>
                  {drawdownPcts.length > 0 ? `${Math.min(...drawdownPcts).toFixed(2)}%` : '—'}
                </p>
              </div>
              <Sparkline values={drawdownPcts} color="var(--accent-orange)" fillBelow height={64} />
            </div>
          </div>
        </>
      )}

      {/* Draw Down Metrics: capital-movement graphs + liquidation-risk cards */}
      {equityValues.length >= 2 && (
        <>
          <SectionHeader title="Draw Down Metrics" subtitle="Capital movements, drawdown damage, and leverage-based liquidation risk" />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <DrawdownChart
              drawdownPcts={drawdownPcts}
              drawdownDollars={ddDollarSeries}
              timestamps={equityTimestamps}
              leverage={leverage}
            />
            <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-1.5">
                <RichTooltip content={TT_CAPITAL_DRAWDOWN}>
                  <p className="text-xs font-medium cursor-help" style={{ color: 'var(--text-muted)' }}>Capital Drawdown $</p>
                </RichTooltip>
                <p className="text-xs font-semibold" style={{ color: 'var(--accent-red)', fontVariantNumeric: 'tabular-nums' }}>
                  ${maxDDDollarVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <Sparkline values={ddDollarSeries} color="var(--accent-red)" fillBelow height={64} />
              <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-faint)' }}>Dollar capital lost from the running peak — raw damage to the account.</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 mt-3" style={smallZoom}>
            <InfoCard
              label="Max Drawdown"
              value={`${maxDDpctVal.toFixed(2)}%`}
              icon={TrendingDown}
              accent="orange"
              tooltip={TT_MAX_DRAWDOWN}
            />
            <InfoCard
              label="Max Drawdown $"
              value={`$${maxDDDollarVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              icon={Coins}
              accent="red"
              tooltip={TT_MAX_DRAWDOWN_USD}
            />
            <InfoCard
              label="Peak Capital"
              value={`$${peakCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              icon={TrendingUp}
              accent="green"
              tooltip={TT_PEAK_CAPITAL}
            />
            <InfoCard
              label="Recovery Factor"
              value={recoveryFactor}
              icon={RotateCcw}
              accent="blue"
              tooltip={TT_RECOVERY_FACTOR}
            />
            <InfoCard
              label="Longest Drawdown"
              value={longestDDRun > 0 ? `${longestDDRun} tr` : '—'}
              icon={Clock}
              accent="orange"
              tooltip={TT_LONGEST_DRAWDOWN}
            />
            <InfoCard
              label="Liquidation Buffer"
              value={liquidationBufferPct != null ? `${liquidationBufferPct.toFixed(1)}%` : '—'}
              icon={AlertOctagon}
              accent={liquidationBufferPct != null && liquidationBufferPct < 0 ? 'red' : 'neutral'}
              subValue={liquidationThresholdPct != null
                ? `${leverage}× → liq at −${liquidationThresholdPct.toFixed(1)}%`
                : (riskPerTradePct != null ? `risk/trade ${riskPerTradePct}%` : undefined)}
              tooltip={TT_LIQUIDATION_BUFFER}
              className={isLiquidated ? 'liquidated-glow' : undefined}
            />
          </div>
          {/* Liquidation Risk Meter (BTCAAAAA-38748): risk-over-time companion to
              the single-scalar Liquidation Buffer above. Renders only when a
              leverage is known (primary Metrics tab); otherwise self-hides. */}
          <div className="mt-3">
            <LiquidationRiskMeter equityCurve={equityCurve} leverage={leverage} />
          </div>
        </>
      )}

      {/* Recent Runs: last 3 runs' equity curves, each with Apply. Sits directly
          above the Risk Metrics / Trade Statistics grid per BTCAAAAA-38724.
          BTCAAAAA-38734: mt-6 adds a row of space above the heading so it is not
          flush against the summary metrics rows above it. */}
      <div className="mt-6 mb-6">
        <RecentRunsSection strategyId={strategyId} currentRunId={result.runId} onApplyConfig={onApplyConfig} appliedRunId={appliedRunId} onRollbackApply={onRollbackApply} />
      </div>

      {/* Two side-by-side 3×2 sparkline-card panels (mockup middle rows) */}
      {/* mt-6: the inner SectionHeaders use first:mt-0, so the row spacer above
          the Risk Metrics heading has to live on this wrapper. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 mt-6">
        <div>
          <SectionHeader title="Risk Metrics" subtitle="Volatility, drawdown, and downside risk measures" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" style={smallZoom}>
            {riskSparklineCards.map(c => (
              <SparklineCard
                key={c.label}
                label={c.label}
                value={c.value}
                valueColor={c.valueColor}
                icon={c.icon}
                accent={c.accent}
                sparkValues={c.sparkValues}
                sparkColor={c.sparkColor}
                tooltip={c.tooltip}
              />
            ))}
          </div>
        </div>
        <div>
          <SectionHeader title="Trade Statistics" subtitle="Win/loss distribution and execution rates" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" style={smallZoom}>
            {tradeSparklineCards.map(c => (
              <SparklineCard
                key={c.label}
                label={c.label}
                value={c.value}
                valueColor={c.valueColor}
                icon={c.icon}
                accent={c.accent}
                sparkValues={c.sparkValues}
                sparkColor={c.sparkColor}
                tooltip={c.tooltip}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Backtest Period strip (5 cards, mockup bottom row) */}
      {periodCards.length > 0 && (
        <>
          <SectionHeader title="Backtest Period" subtitle="Run window, sample size, and reporting currency" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5" style={smallZoom}>
            {periodCards.map(c => (
              <InfoCard
                key={c.label}
                label={c.label}
                value={c.value}
                icon={c.icon}
                accent={c.accent}
                subValue={c.subValue}
                tooltip={c.tooltip}
              />
            ))}
          </div>
        </>
      )}

      {/* Collapsed expander preserves every metric surfaced in v1 */}
      <div className="mt-5">
        <button
          type="button"
          onClick={() => setShowAdditional(v => !v)}
          className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide cursor-pointer select-none"
          style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none', padding: 0 }}
          aria-expanded={showAdditional}
        >
          {showAdditional ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showAdditional ? 'Hide additional metrics' : 'Show additional metrics'}
        </button>
        {showAdditional && (
          <div className="grid grid-cols-5 gap-3 md:grid-cols-5 mt-3" style={smallZoom}>
            {additionalRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        )}
      </div>

      {/* Strategy Signals (BTCAAAAA-66772). Sits at the very bottom of the
          panel per the user's "seperate grid right at the bottom for all
          strategy Signals not just Exit Strategies" ask. Two layers:

          (1) Four building-block summary cards (Signals Required / Rechecks /
              Exit Signals / Stop-Loss Adjustments) — these previously lived
              inside the Additional Metrics expander as "—" because the
              backend did not expose per-trade signal telemetry. They now
              derive from the trade record (Trade.entrySignals +
              Trade.exitType) and have real values.

          (2) A per-entry-signal detail table sorted by firing count. This is
              the meaningfulness upgrade the user asked for — every signal
              name is a row, with firing count, win rate, total/avg PnL, and
              the top co-fire signal as a confluence proxy (per-trade
              confluence scores are not yet on the trade record, only in the
              validation framework, so co-fire pair counts are the closest
              available signal-clustering signal). */}
      <div className="mt-6">
        <RichTooltip content={TT_STRATEGY_SIGNALS_SECTION}>
          <SectionHeader
            title="Strategy Signals"
            subtitle="Per-entry-signal telemetry: firing counts, win rate, PnL contribution, and co-fire pairs"
          />
        </RichTooltip>

        {/* (1) Building-block summary cards — real values now */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4" style={smallZoom}>
          <MetricCard
            label="Signals Required"
            value={
              signalSummary.hasTelemetry
                ? signalSummary.signalsRequiredAvg.toFixed(2)
                : '—'
            }
            tooltip={TT_SIGNALS_REQUIRED}
            icon={Activity}
            accent="blue"
            baseline={
              signalSummary.hasTelemetry
                ? 'avg entry signals per trade'
                : 'no per-trade signal telemetry'
            }
          />
          <MetricCard
            label="Rechecks"
            value={
              signalSummary.hasTelemetry
                ? signalSummary.rechecksTotal.toLocaleString()
                : '—'
            }
            tooltip={TT_RECHECKS}
            icon={RotateCcw}
            accent="blue"
            baseline={
              signalSummary.hasTelemetry
                ? 'extra signals fired after the first'
                : 'no per-trade signal telemetry'
            }
          />
          <MetricCard
            label="Exit Signals"
            value={
              signalSummary.hasTelemetry
                ? signalSummary.exitSignalCount.toLocaleString()
                : '—'
            }
            tooltip={TT_EXIT_SIGNALS}
            icon={AlertTriangle}
            accent="orange"
            baseline={
              signalSummary.hasTelemetry
                ? `of ${allTrades.length.toLocaleString()} closed trades`
                : 'no per-trade signal telemetry'
            }
          />
          <MetricCard
            label="Stop-Loss Adjustments"
            value={
              signalSummary.hasTelemetry
                ? signalSummary.slAdjustmentCount.toLocaleString()
                : '—'
            }
            tooltip={TT_STOP_LOSS_ADJUSTMENTS}
            icon={Scale}
            accent="neutral"
            baseline={
              signalSummary.hasTelemetry
                ? 'trades closed by a trailing/adaptive SL'
                : 'no per-trade signal telemetry'
            }
          />
        </div>

        {/* (2) Per-entry-signal detail table */}
        <RichTooltip content={TT_ENTRY_SIGNALS_FIRED}>
          <div
            className="mt-4 rounded overflow-hidden"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
          >
            <div
              className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-faint)', borderBottom: '1px solid var(--border)' }}
            >
              <div className="col-span-4">Signal</div>
              <div className="col-span-2 text-right" title="Total trades where this signal fired">
                Fired
              </div>
              <div className="col-span-2 text-right" title="Win rate of those trades">
                Win Rate
              </div>
              <div className="col-span-2 text-right" title="Total $ PnL across those trades">
                Total PnL
              </div>
              <div className="col-span-2 text-right" title="Mean $ PnL per trade for that signal">
                Avg PnL
              </div>
            </div>
            {entrySignalStats.length === 0 ? (
              <div
                className="px-3 py-4 text-[11px]"
                style={{ color: 'var(--text-faint)' }}
              >
                No entry signal telemetry on this run — Trade.entrySignals[] is
                empty or missing for every closed trade. Re-run the backtest
                with the engine that emits per-trade entry signals (see
                BTC-37920 v3 building blocks).
              </div>
            ) : (
              entrySignalStats.map((row, i) => {
                const winRatePct = (row.winRate * 100).toFixed(1);
                const avgPnlVal = row.avgPnl;
                const totalPnlVal = row.totalPnl;
                const avgPnlColor =
                  avgPnlVal > 0 ? 'var(--accent-green)'
                  : avgPnlVal < 0 ? 'var(--accent-red)'
                  : 'var(--text-muted)';
                const totalPnlColor =
                  totalPnlVal > 0 ? 'var(--accent-green)'
                  : totalPnlVal < 0 ? 'var(--accent-red)'
                  : 'var(--text-muted)';
                const winRateColor =
                  row.winRate >= 0.5 ? 'var(--accent-green)'
                  : row.winRate >= 0.4 ? 'var(--accent-orange)'
                  : 'var(--accent-red)';
                const coFireLabel =
                  row.topCoFires.length === 0
                    ? '—'
                    : row.topCoFires
                        .map(c => `${c.signal} (${c.count})`)
                        .join(', ');
                return (
                  <RichTooltip
                    key={row.signal}
                    content={TT_ENTRY_SIGNALS_TABLE}
                  >
                    <div
                      className="grid grid-cols-12 gap-2 px-3 py-2 text-[11px] cursor-help"
                      style={{
                        borderBottom:
                          i === entrySignalStats.length - 1
                            ? 'none'
                            : '1px solid var(--border)',
                        background:
                          i % 2 === 1
                            ? 'color-mix(in srgb, var(--bg-card-hover) 35%, transparent)'
                            : 'transparent',
                      }}
                    >
                      <div className="col-span-4 truncate" title={row.signal} style={{ color: 'var(--text-secondary)' }}>
                        {row.signal}
                      </div>
                      <div
                        className="col-span-2 text-right tabular-nums"
                        style={{ color: 'var(--text-secondary)' }}
                        title={`${row.fired} trade${row.fired === 1 ? '' : 's'} — ${row.wins}W / ${row.losses}L`}
                      >
                        {row.fired}
                      </div>
                      <div
                        className="col-span-2 text-right tabular-nums"
                        style={{ color: winRateColor }}
                      >
                        {winRatePct}%
                      </div>
                      <div
                        className="col-span-2 text-right tabular-nums"
                        style={{ color: totalPnlColor }}
                      >
                        ${totalPnlVal.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      </div>
                      <div
                        className="col-span-2 text-right tabular-nums"
                        style={{ color: avgPnlColor }}
                        title={
                          row.topCoFires.length > 0
                            ? `Co-fires: ${coFireLabel}`
                            : 'No co-fire data'
                        }
                      >
                        ${avgPnlVal.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                          minimumFractionDigits: 2,
                        })}
                      </div>
                    </div>
                  </RichTooltip>
                );
              })
            )}
          </div>
        </RichTooltip>
      </div>
    </div>
  );
}
