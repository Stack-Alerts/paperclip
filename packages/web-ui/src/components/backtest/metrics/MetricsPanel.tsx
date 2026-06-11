'use client';

import { BacktestResult, Trade } from '@/lib/strategy-builder/types';
import { RichTooltip, type TooltipContent } from '@/components/strategy-builder/RichTooltip';
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
} from './MetricsPanelTooltips';

export interface MetricsPanelProps {
  result?: BacktestResult | null;
  trades?: Trade[];
}

interface MetricRow {
  label: string;
  value: string;
  color?: string;
  tooltip: TooltipContent;
}

function MetricCard({ label, value, color, tooltip }: MetricRow) {
  return (
    <RichTooltip content={tooltip}>
      <div
        className="rounded p-3 cursor-default"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
        <p className="text-sm font-semibold" style={{ color: color || 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
          {value}
        </p>
      </div>
    </RichTooltip>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wide mt-5 mb-3 first:mt-0" style={{ color: 'var(--text-muted)' }}>
      {title}
    </p>
  );
}

function computeTradeStats(trades: Trade[]) {
  if (!trades.length) return null;

  const closed = trades.filter(t => (t.status ?? '').toUpperCase() === 'CLOSED');
  const source = closed.length > 0 ? closed : trades;

  const pnls = source.map(t => t.pnl);
  const bestTrade = Math.max(...pnls);
  const worstTrade = Math.min(...pnls);
  const avgBars = source.reduce((s, t) => s + (t.bars ?? 0), 0) / source.length;

  const longs = source.filter(t => (t.side ?? '').toUpperCase() === 'LONG').length;
  const shorts = source.filter(t => (t.side ?? '').toUpperCase() === 'SHORT').length;

  const exitTypes: Record<string, number> = {};
  for (const t of source) {
    const key = t.exitType ?? 'Unknown';
    exitTypes[key] = (exitTypes[key] ?? 0) + 1;
  }

  let maxConsecWins = 0, maxConsecLosses = 0, curWins = 0, curLosses = 0;
  for (const pnl of pnls) {
    if (pnl > 0) { curWins++; curLosses = 0; maxConsecWins = Math.max(maxConsecWins, curWins); }
    else { curLosses++; curWins = 0; maxConsecLosses = Math.max(maxConsecLosses, curLosses); }
  }

  return { bestTrade, worstTrade, avgBars, longs, shorts, exitTypes, maxConsecWins, maxConsecLosses, count: source.length };
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

  const returnsRows: MetricRow[] = [
    { label: 'Total Return', value: `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`, color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_TOTAL_RETURN },
    { label: 'Net Profit', value: `${netProfit >= 0 ? '+' : ''}$${netProfit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, color: netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_NET_PROFIT },
    { label: 'Initial Capital', value: `$${result.initialCapital.toLocaleString()}`, tooltip: TT_INITIAL_CAPITAL },
    { label: 'Final Capital', value: `$${result.finalCapital.toLocaleString()}`, tooltip: TT_FINAL_CAPITAL },
  ];

  const riskRows: MetricRow[] = [
    { label: 'Max Drawdown', value: `${result.maxDrawdown.toFixed(2)}%`, color: 'var(--accent-orange)', tooltip: TT_MAX_DRAWDOWN },
    { label: 'Sharpe Ratio', value: result.sharpeRatio.toFixed(2), tooltip: TT_SHARPE },
    { label: 'Sortino Ratio', value: result.sortino_ratio.toFixed(2), tooltip: TT_SORTINO },
  ];
  if (result.calmar_ratio != null) {
    riskRows.push({ label: 'Calmar Ratio', value: result.calmar_ratio.toFixed(2), tooltip: TT_CALMAR });
  }

  const tradeRows: MetricRow[] = [
    { label: 'Total Trades', value: String(result.totalTrades), tooltip: TT_TOTAL_TRADES },
    { label: 'Win Rate', value: `${winPct}%`, color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_WIN_RATE },
    { label: 'Winning Trades', value: String(result.winningTrades), color: 'var(--accent-green)', tooltip: TT_WINNING_TRADES },
    { label: 'Losing Trades', value: String(result.losingTrades), color: 'var(--accent-red)', tooltip: TT_LOSING_TRADES },
    { label: 'Profit Factor', value: result.profitFactor.toFixed(2), tooltip: TT_PROFIT_FACTOR },
    { label: 'Expectancy', value: `${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`, color: expectancy >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT_EXPECTANCY },
    { label: 'Avg Win', value: `$${result.averageWin.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT_AVG_WIN },
    { label: 'Avg Loss', value: `-$${Math.abs(result.averageLoss).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_AVG_LOSS },
    { label: 'Risk/Reward', value: rrRatio, tooltip: TT_RISK_REWARD },
    { label: 'Breakeven Win%', value: `${breakevenWinRate}%`, tooltip: TT_BREAKEVEN_WIN },
  ];

  const insightRows: MetricRow[] = [];
  if (tradeStats) {
    insightRows.push(
      { label: 'Best Trade', value: `${tradeStats.bestTrade >= 0 ? '+' : ''}$${tradeStats.bestTrade.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT_BEST_TRADE },
      { label: 'Worst Trade', value: `-$${Math.abs(tradeStats.worstTrade).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT_WORST_TRADE },
      { label: 'Avg Bars Held', value: tradeStats.avgBars.toFixed(1), tooltip: TT_AVG_BARS },
      { label: 'Max Consec. Wins', value: String(tradeStats.maxConsecWins), color: 'var(--accent-green)', tooltip: TT_MAX_CONSEC_WINS },
      { label: 'Max Consec. Losses', value: String(tradeStats.maxConsecLosses), color: 'var(--accent-red)', tooltip: TT_MAX_CONSEC_LOSSES },
    );
    if (tradeStats.longs + tradeStats.shorts > 0) {
      insightRows.push(
        { label: 'Long Trades', value: String(tradeStats.longs), tooltip: TT_LONG_TRADES },
        { label: 'Short Trades', value: String(tradeStats.shorts), tooltip: TT_SHORT_TRADES },
      );
    }
    for (const [exitType, count] of Object.entries(tradeStats.exitTypes)) {
      if (exitType === 'Unknown') continue;
      const pct = ((count / tradeStats.count) * 100).toFixed(0);
      insightRows.push({ label: `Exit: ${exitType}`, value: `${count} (${pct}%)`, tooltip: TT_EXIT_TYPE(exitType, count, tradeStats.count) });
    }
  }

  const periodRows: MetricRow[] = [];
  if (result.startDate) periodRows.push({ label: 'Start Date', value: formatDate(result.startDate), tooltip: TT_START_DATE });
  if (result.endDate) periodRows.push({ label: 'End Date', value: formatDate(result.endDate), tooltip: TT_END_DATE });
  if (durationDays != null) periodRows.push({ label: 'Duration', value: `${durationDays} days`, tooltip: TT_DURATION });
  if (result.totalBars != null) periodRows.push({ label: 'Bars Analyzed', value: result.totalBars.toLocaleString(), tooltip: TT_BARS_ANALYZED });

  return (
    <div>
      <SectionHeader title="Returns & Capital" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {returnsRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      <SectionHeader title="Risk Metrics" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {riskRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      <SectionHeader title="Trade Statistics" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {tradeRows.map(r => <MetricCard key={r.label} {...r} />)}
      </div>

      {insightRows.length > 0 && (
        <>
          <SectionHeader title="Trade Insights" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {insightRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        </>
      )}

      {periodRows.length > 0 && (
        <>
          <SectionHeader title="Backtest Period" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {periodRows.map(r => <MetricCard key={r.label} {...r} />)}
          </div>
        </>
      )}
    </div>
  );
}
