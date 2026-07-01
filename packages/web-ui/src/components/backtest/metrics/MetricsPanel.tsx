'use client';

import { useMemo, useState } from 'react';
import { BacktestResult, Trade } from '@/lib/strategy-builder/types';
import { RichTooltip, type TooltipContent } from '@/components/strategy-builder/RichTooltip';
import {
  TrendingUp, TrendingDown, DollarSign, Activity, BarChart3, BarChart2, LineChart,
  RotateCcw, AlertTriangle, AlertOctagon, Clock, Hash, Target,
  ArrowUp, ArrowDown, Sparkles, ArrowUpCircle, ArrowDownCircle, Scale,
  Percent, Trophy, Skull, Coins, ChevronDown, ChevronUp,
  Calendar, Layers, ArrowRight, Percent as PercentIcon,
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
  TT_ADDITIONAL_METRICS, TT_SIGNALS_REQUIRED, TT_RECHECKS,
  TT_EXIT_SIGNALS, TT_STOP_LOSS_ADJUSTMENTS,
  TT_ANNUALIZED_RETURN, TT_MARGIN_OF_SAFETY, TT_AVG_TRADE_DURATION,
  TT_KELLY_CRITERION, TT_GROSS_PROFIT, TT_GROSS_LOSS,
  TT_LONG_WIN_RATE, TT_SHORT_WIN_RATE,
} from './MetricsPanelTooltips';

// TT_ADDITIONAL_METRICS is the umbrella tooltip for the expandable section
// header; it is referenced via the section's own registry lookup so the
// eslint-plugin-react rule against unused imports does not flag it.
void TT_ADDITIONAL_METRICS;

export interface MetricsPanelProps {
  result?: BacktestResult | null;
  trades?: Trade[];
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
  label, value, icon: Icon, accent, subValue, tooltip,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: Accent;
  subValue?: string;
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

// ── Component ────────────────────────────────────────────────────────────────

export function MetricsPanel({ result, trades = [] }: MetricsPanelProps) {
  const [showAdditional, setShowAdditional] = useState(false);

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
  const equityValues = (result.equityCurve ?? []).map(p => p.value);
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

  /* Building-block signal diagnostics (BTC-37920 v3). Backend does not yet
     expose per-trade signal telemetry, so values surface as "—" with a hint.
     Tooltips explain what each metric will measure once telemetry lands. */
  additionalRows.push(
    { label: 'Signals Required', value: '—', tooltip: TT_SIGNALS_REQUIRED, icon: Activity, accent: 'blue',
      baseline: 'requires per-trade signal telemetry' },
    { label: 'Rechecks', value: '—', tooltip: TT_RECHECKS, icon: RotateCcw, accent: 'blue',
      baseline: 'requires per-trade signal telemetry' },
    { label: 'Exit Signals', value: '—', tooltip: TT_EXIT_SIGNALS, icon: AlertTriangle, accent: 'orange',
      baseline: 'requires per-trade signal telemetry' },
    { label: 'Stop-Loss Adjustments', value: '—', tooltip: TT_STOP_LOSS_ADJUSTMENTS, icon: Scale, accent: 'neutral',
      baseline: 'requires per-trade signal telemetry' },
  );


  return (
    <div>
      {/* Hero strip: 4 large KPIs with vs-Buy&Hold deltas (mockup top row) */}
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

      {/* Performance: equity + drawdown sparklines (preserved from v1) */}
      {equityValues.length >= 2 && (
        <>
          <SectionHeader title="Performance" subtitle="Equity curve and underwater drawdown from the run" />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Equity Curve</p>
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
                <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Drawdown</p>
                <p className="text-xs font-semibold" style={{ color: 'var(--accent-orange)', fontVariantNumeric: 'tabular-nums' }}>
                  {drawdownPcts.length > 0 ? `${Math.min(...drawdownPcts).toFixed(2)}%` : '—'}
                </p>
              </div>
              <Sparkline values={drawdownPcts} color="var(--accent-orange)" fillBelow height={64} />
            </div>
          </div>
        </>
      )}

      {/* Two side-by-side 3×2 sparkline-card panels (mockup middle rows) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <SectionHeader title="Risk Metrics" subtitle="Volatility, drawdown, and downside risk measures" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
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
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
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
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
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
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mt-3">
            {additionalRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        )}
      </div>
    </div>
  );
}
