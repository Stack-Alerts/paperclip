'use client';

import { BacktestResult, Trade } from '@/lib/strategy-builder/types';
import { RichTooltip, type TooltipContent } from '@/components/strategy-builder/RichTooltip';
import {
  TrendingUp, TrendingDown, DollarSign, Activity, BarChart3, BarChart2, LineChart,
  RotateCcw, AlertTriangle, AlertOctagon, Clock, Hash, Target,
  ArrowUp, ArrowDown, Sparkles, ArrowUpCircle, ArrowDownCircle, Scale,
  Percent, Trophy, Skull, Coins,
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
  TT_START_DATE, TT_END_DATE, TT_DURATION, TT_BARS_ANALYZED,
  TT_EXIT_TYPE,
  TT_VOLATILITY, TT_VAR_95, TT_CVAR_95, TT_EXPOSURE_TIME,
  TT_PAYOFF_RATIO, TT_LARGEST_WIN, TT_LARGEST_LOSS, TT_CURRENCY,
} from './MetricsPanelTooltips';

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
  // Optional secondary line beneath the value (e.g. "vs BTC 100K: -22.1%").
  // Drives the small muted pill rendered below the value.
  baseline?: string;
  // Optional small chip rendered above the label (e.g. "LONG", "SHORT", "Strategy A").
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

function Sparkline({ values, color, fillBelow = false, height = 56 }: { values: number[]; color: string; fillBelow?: boolean; height?: number }) {
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

function computeTradeStats(trades: Trade[]) {
  if (!trades.length) return null;

  const closed = trades.filter(t => (t.status ?? '').toUpperCase() === 'CLOSED');
  const source = closed.length > 0 ? closed : trades;

  const pnls = source.map(t => t.pnl);
  // "Best trade" must be the largest *winning* P&L and "Worst trade" the
  // smallest *losing* P&L. Using all-PnL min/max made a single winning trade
  // show +$X as Best and -$X as Worst (the display layer hardcodes a leading
  // minus for Worst Trade), producing the impossible +203/-203 pair seen in
  // BTCAAAAA-35996. With no winners or no losers the corresponding value is 0.
  const winPnls = pnls.filter(p => p > 0);
  const lossPnls = pnls.filter(p => p < 0);
  const bestTrade = winPnls.length ? Math.max(...winPnls) : 0;
  const worstTrade = lossPnls.length ? Math.min(...lossPnls) : 0;
  // Largest Win / Largest Loss mirror best/worst but surface the raw single-
  // trade magnitudes for the Trade Statistics row (BTCAAAAA-37920 mockup).
  const largestWin = winPnls.length ? Math.max(...winPnls) : 0;
  const largestLoss = lossPnls.length ? Math.min(...lossPnls) : 0;
  const avgBars = source.reduce((s, t) => s + (t.bars ?? 0), 0) / source.length;

  const longs = source.filter(t => (t.side ?? '').toUpperCase() === 'LONG').length;
  const shorts = source.filter(t => (t.side ?? '').toUpperCase() === 'SHORT').length;

  const exitTypes: Record<string, number> = {};
  for (const t of source) {
    const key = t.exitType ?? 'Unknown';
    exitTypes[key] = (exitTypes[key] ?? 0) + 1;
  }

  // Aggregate payoff ratio (Σwins / Σlosses) — distinct from per-trade
  // Risk/Reward which divides averages. Surface in Trade Statistics row.
  const winsSum = winPnls.reduce((s, p) => s + p, 0);
  const lossesSum = lossPnls.reduce((s, p) => s + Math.abs(p), 0);

  // VaR95 / CVaR95 require a meaningful sample of per-trade returns.
  // Industry convention gates these at N≥20 trades; below that, surface "—"
  // rather than emit a percentile from 8 data points that users will
  // over-trust. (BTCAAAAA-37920)
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

  // Return volatility = sample std dev of per-trade percent returns.
  // Sample std dev requires N>=2; with degenerate inputs we emit "—".
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
    count: source.length,
  };
}


// ── Component ──────────────────────────────────────────────────────────────────

export function MetricsPanel({ result, trades = [] }: MetricsPanelProps) {
  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-12" style={{ color: 'var(--text-faint)' }}>
        <p className="text-sm">No results yet.</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Run a backtest to see performance metrics.</p>
      </div>
    );
  }

  const allTrades = trades.length > 0 ? trades : (result.trades ?? []);
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
  // Drawdown is reported as a negative percent relative to the running peak.
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
  // Sample std dev requires N>=2; downside deviation requires >=1 losing trade;
  // Calmar's denominator is max drawdown. With degenerate inputs the backend
  // returns 0.0 for these (app.py:1989-2000) — the math is actually undefined,
  // not zero. Match the recoveryFactor / rrRatio "—" pattern so users see the
  // same "undefined" sentinel for every undefined denominator (BTCAAAAA-35996).
  const sharpeStr = allTrades.length >= 2 ? result.sharpeRatio.toFixed(2) : '—';
  const sortinoStr = allTrades.length >= 2 && result.losingTrades > 0
    ? result.sortino_ratio.toFixed(2)
    : '—';
  const calmarStr = result.maxDrawdown > 0 && result.calmar_ratio != null
    ? result.calmar_ratio.toFixed(2)
    : '—';
  const avgHoldingBars = tradeStats && tradeStats.avgBars > 0 ? tradeStats.avgBars.toFixed(1) : '—';

  // ── Derived metrics for the new mockup rows (BTCAAAAA-37920) ────────────────
  // Exposure Time: fraction of bars the strategy held a position. With no
  // totalBars from the backend we surface "—" rather than fabricate.
  const totalBarsHeld = allTrades.reduce((s, t) => s + (t.bars ?? 0), 0);
  const exposurePct = result.totalBars && result.totalBars > 0
    ? (totalBarsHeld / result.totalBars) * 100
    : null;

  // Symbol is per-trade; display the first non-empty value or "—" (USDT assumed).
  const symbol = allTrades.find(t => t.symbol)?.symbol ?? null;

  // ── Section: Key Metrics (4 KPIs from mockup) ──────────────────────────────
  const keyMetricRows: MetricRow[] = [
    {
      label: 'Total Return', value: `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`,
      color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_TOTAL_RETURN,
      icon: result.returnPercentage >= 0 ? TrendingUp : TrendingDown,
      accent: result.returnPercentage >= 0 ? 'green' : 'red',
    },
    {
      label: 'Net Profit', value: `${netProfit >= 0 ? '+' : ''}$${netProfit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      color: netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_NET_PROFIT,
      icon: DollarSign,
      accent: netProfit >= 0 ? 'green' : 'red',
    },
    {
      label: 'Max Drawdown', value: `${(result.maxDrawdown * 100).toFixed(2)}%`,
      color: 'var(--accent-orange)',
      tooltip: TT_MAX_DRAWDOWN,
      icon: AlertTriangle,
      accent: 'orange',
    },
    {
      label: 'Profit Factor', value: result.profitFactor.toFixed(2),
      color: result.profitFactor >= 1 ? 'var(--accent-green)' : 'var(--accent-red)',
      tooltip: TT_PROFIT_FACTOR,
      icon: Scale,
      accent: result.profitFactor >= 1 ? 'green' : 'red',
    },
  ];

  // ── Section: Risk Metrics (8 from mockup) ─────────────────────────────────
  const riskRows: MetricRow[] = [
    { label: 'Recovery Factor', value: recoveryFactor, color: Number(recoveryFactor) >= 1 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_MAX_DRAWDOWN, icon: RotateCcw, accent: Number(recoveryFactor) >= 1 ? 'green' : 'red' },
    { label: 'Sharpe Ratio', value: sharpeStr, tooltip: TT_SHARPE, icon: Activity, accent: 'blue' },
    { label: 'Sortino Ratio', value: sortinoStr, tooltip: TT_SORTINO, icon: BarChart3, accent: 'blue' },
    { label: 'Calmar Ratio', value: calmarStr, tooltip: TT_CALMAR, icon: LineChart, accent: 'blue' },
    {
      label: 'Volatility (σ)', value: tradeStats?.returnVolatility != null ? `${tradeStats.returnVolatility.toFixed(2)}%` : '—',
      tooltip: TT_VOLATILITY, icon: BarChart2, accent: 'neutral',
    },
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
    {
      label: 'Exposure Time', value: exposurePct != null ? `${exposurePct.toFixed(1)}%` : '—',
      tooltip: TT_EXPOSURE_TIME, icon: Clock, accent: 'blue',
    },
  ];

  // ── Section: Trade Statistics (12 from mockup) ────────────────────────────
  const tradeRows: MetricRow[] = [
    { label: 'Total Trades', value: String(result.totalTrades), tooltip: TT_TOTAL_TRADES, icon: Hash, accent: 'neutral' },
    { label: 'Win Rate', value: `${winPct}%`, color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_WIN_RATE, icon: Target, accent: result.winRate >= 0.5 ? 'green' : 'red' },
    { label: 'Winning Trades', value: String(result.winningTrades), color: 'var(--accent-green)', tooltip: TT_WINNING_TRADES, icon: ArrowUp, accent: 'green' },
    { label: 'Losing Trades', value: String(result.losingTrades), color: 'var(--accent-red)', tooltip: TT_LOSING_TRADES, icon: ArrowDown, accent: 'red' },
    { label: 'Largest Win', value: tradeStats ? `${tradeStats.largestWin >= 0 ? '+' : ''}$${tradeStats.largestWin.toFixed(2)}` : '—', color: 'var(--accent-green)', tooltip: TT_LARGEST_WIN, icon: ArrowUpCircle, accent: 'green' },
    { label: 'Largest Loss', value: tradeStats ? `-$${Math.abs(tradeStats.largestLoss).toFixed(2)}` : '—', color: 'var(--accent-red)', tooltip: TT_LARGEST_LOSS, icon: ArrowDownCircle, accent: 'red' },
    { label: 'Avg Win', value: `$${result.averageWin.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT_AVG_WIN, icon: TrendingUp, accent: 'green' },
    { label: 'Avg Loss', value: `-$${Math.abs(result.averageLoss).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_AVG_LOSS, icon: TrendingDown, accent: 'red' },
    { label: 'Risk / Reward', value: rrRatio, tooltip: TT_RISK_REWARD, icon: Scale, accent: 'neutral' },
    {
      label: 'Payoff Ratio', value: tradeStats && tradeStats.lossesSum > 0
        ? (tradeStats.winsSum / tradeStats.lossesSum).toFixed(2)
        : '—',
      tooltip: TT_PAYOFF_RATIO, icon: Percent, accent: 'neutral',
    },
    { label: 'Breakeven Win%', value: `${breakevenWinRate}%`, tooltip: TT_BREAKEVEN_WIN, icon: Sparkles, accent: 'neutral' },
    { label: 'Expectancy', value: `${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`, color: expectancy >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_EXPECTANCY, icon: Activity, accent: expectancy >= 0 ? 'green' : 'red' },
  ];

  // ── Section: Trade Insights (conditional — preserved from original) ───────
  const insightRows: MetricRow[] = [];
  if (tradeStats) {
    insightRows.push(
      { label: 'Best Trade', value: `${tradeStats.bestTrade >= 0 ? '+' : ''}$${tradeStats.bestTrade.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT_BEST_TRADE, icon: Trophy, accent: 'green' },
      { label: 'Worst Trade', value: `-$${Math.abs(tradeStats.worstTrade).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_WORST_TRADE, icon: Skull, accent: 'red' },
      { label: 'Avg Bars Held', value: tradeStats.avgBars.toFixed(1), tooltip: TT_AVG_BARS, icon: Clock, accent: 'neutral' },
      { label: 'Max Consec. Wins', value: String(tradeStats.maxConsecWins), color: 'var(--accent-green)', tooltip: TT_MAX_CONSEC_WINS, icon: ArrowUpCircle, accent: 'green' },
      { label: 'Max Consec. Losses', value: String(tradeStats.maxConsecLosses), color: 'var(--accent-red)', tooltip: TT_MAX_CONSEC_LOSSES, icon: ArrowDownCircle, accent: 'red' },
    );
    if (tradeStats.longs + tradeStats.shorts > 0) {
      insightRows.push(
        { label: 'Long Trades', value: String(tradeStats.longs), tooltip: TT_LONG_TRADES, icon: ArrowUp, accent: 'green' },
        { label: 'Short Trades', value: String(tradeStats.shorts), tooltip: TT_SHORT_TRADES, icon: ArrowDown, accent: 'red' },
      );
    }
    for (const [exitType, count] of Object.entries(tradeStats.exitTypes)) {
      if (exitType === 'Unknown') continue;
      const pct = ((count / tradeStats.count) * 100).toFixed(0);
      insightRows.push({ label: `Exit: ${exitType}`, value: `${count} (${pct}%)`, tooltip: TT_EXIT_TYPE(exitType, count, tradeStats.count), icon: BarChart3, accent: 'neutral' });
    }
    insightRows.push({ label: 'Avg Holding (bars)', value: avgHoldingBars, tooltip: TT_AVG_BARS, icon: Clock, accent: 'neutral' });
    if (tradeStats.returnVolatility != null) {
      insightRows.push({ label: 'Return σ (per trade %)', value: `${tradeStats.returnVolatility.toFixed(2)}%`, tooltip: TT_VOLATILITY, icon: BarChart2, accent: 'neutral' });
    }
  }

  // ── Section: Backtest Period (7 fields from mockup) ────────────────────────
  const periodRows: MetricRow[] = [];
  if (result.startDate) periodRows.push({ label: 'Start Date', value: formatDate(result.startDate), tooltip: TT_START_DATE, icon: Clock, accent: 'neutral' });
  if (result.endDate) periodRows.push({ label: 'End Date', value: formatDate(result.endDate), tooltip: TT_END_DATE, icon: Clock, accent: 'neutral' });
  if (durationDays != null) periodRows.push({ label: 'Duration', value: `${durationDays} days`, tooltip: TT_DURATION, icon: Clock, accent: 'neutral' });
  if (result.totalBars != null) periodRows.push({ label: 'Bars Analyzed', value: result.totalBars.toLocaleString(), tooltip: TT_BARS_ANALYZED, icon: Hash, accent: 'neutral' });
  periodRows.push({
    label: 'Currency', value: 'USDT',
    tooltip: TT_CURRENCY, icon: Coins, accent: 'neutral',
    baseline: symbol ? `pair: ${symbol}` : 'BacktestResult has no currency field — USDT assumed',
  });

  return (
    <div>
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
                <span aria-hidden="true">→</span>
                <RichTooltip content={TT_FINAL_CAPITAL}>
                  <span className="cursor-help">Final ${result.finalCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </RichTooltip>
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

      <SectionHeader title="Key Metrics" subtitle="Top-line performance indicators" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {keyMetricRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      <SectionHeader title="Risk Metrics" subtitle="Volatility, drawdown, and downside risk measures" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {riskRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      <SectionHeader title="Trade Statistics" subtitle="Win/loss distribution, averages, and ratios" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tradeRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      {insightRows.length > 0 && (
        <>
          <SectionHeader title="Trade Insights" subtitle="Per-trade aggregates and exit-type breakdown" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {insightRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        </>
      )}

      {periodRows.length > 0 && (
        <>
          <SectionHeader title="Backtest Period" subtitle="Run window, sample size, and reporting currency" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {periodRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        </>
      )}
    </div>
  );
}
