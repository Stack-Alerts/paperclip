'use client';

import { BacktestResult, Trade } from '@/lib/strategy-builder/types';
import { RichTooltip, type TooltipContent } from '@/components/strategy-builder/RichTooltip';

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

// ── Tooltip definitions ────────────────────────────────────────────────────────

const TT: Record<string, TooltipContent> = {
  totalReturn: {
    title: 'Total Return',
    body: 'Cumulative percentage gain or loss on the initial capital over the entire backtest period.',
    sections: [{ header: 'Benchmarks', items: ['< 0%: Strategy lost money', '0–15%: Marginal', '15–50%: Acceptable', '> 50%: Strong (verify overfitting)'] }],
  },
  netProfit: {
    title: 'Net Profit',
    body: 'Absolute dollar P&L: Final Capital minus Initial Capital. Provides scale context alongside the percentage return.',
  },
  initialCapital: {
    title: 'Initial Capital',
    body: 'Starting portfolio value used as the denominator for all percentage-based metrics.',
  },
  finalCapital: {
    title: 'Final Capital',
    body: 'Portfolio value at the end of the backtest. Equal to Initial Capital plus net profit from all closed trades.',
  },
  maxDrawdown: {
    title: 'Max Drawdown',
    body: 'Largest peak-to-trough decline in portfolio equity, expressed as a percentage of the peak value.',
    sections: [{ header: 'Benchmarks', items: ['< 5%: Very low risk', '5–15%: Acceptable', '15–25%: Elevated — review position sizing', '> 25%: High — unsuitable for most live deployments'] }],
  },
  sharpe: {
    title: 'Sharpe Ratio',
    body: 'Risk-adjusted return: mean per-trade return divided by standard deviation, scaled by √n. Measures reward per unit of total volatility.',
    sections: [{ header: 'Benchmarks', items: ['< 0.5: Poor', '0.5–1.0: Acceptable', '1.0–2.0: Good', '> 2.0: Excellent'] }],
  },
  sortino: {
    title: 'Sortino Ratio',
    body: 'Like Sharpe but penalises only downside volatility, ignoring upside swings. Preferred when return distribution is positively skewed.',
    sections: [{ header: 'Benchmarks', items: ['< 1.0: Needs improvement', '1.0–2.0: Good', '> 2.0: Excellent', 'Sortino > Sharpe is expected for profitable strategies'] }],
  },
  calmar: {
    title: 'Calmar Ratio',
    body: 'Total return divided by Max Drawdown. Balances return against the worst historical loss. Widely used in fund evaluation.',
    sections: [{ header: 'Benchmarks', items: ['< 0.5: Poor', '0.5–1.0: Acceptable', '1.0–3.0: Good', '> 3.0: Excellent'] }],
  },
  totalTrades: {
    title: 'Total Trades',
    body: 'Number of completed (closed) trades in the backtest. Statistical significance increases with trade count.',
    sections: [{ items: ['< 30 trades: Insufficient for reliable statistics', '30–100: Minimum viable', '> 100: Statistically meaningful'] }],
  },
  winRate: {
    title: 'Win Rate',
    body: 'Percentage of closed trades that closed in profit. Must be interpreted alongside Risk/Reward — a 40% win rate can be highly profitable with a 3:1 R:R.',
    sections: [{ header: 'Context', items: ['Compare against Breakeven Win% for margin of safety', 'High win rate + poor R:R is often worse than low win rate + strong R:R'] }],
  },
  winningTrades: {
    title: 'Winning Trades',
    body: 'Count of trades that closed with positive P&L.',
  },
  losingTrades: {
    title: 'Losing Trades',
    body: 'Count of trades that closed with zero or negative P&L.',
  },
  profitFactor: {
    title: 'Profit Factor',
    body: 'Gross profit divided by gross loss across all trades. A single ratio that captures both win rate and reward-to-risk.',
    sections: [{ header: 'Benchmarks', items: ['< 1.0: Losing strategy', '1.0–1.5: Marginal', '1.5–2.0: Good', '> 2.0: Excellent — verify for overfitting'] }],
  },
  expectancy: {
    title: 'Expectancy',
    body: 'Average dollar expected per trade: (Win Rate × Avg Win) + (Loss Rate × Avg Loss). The true edge of the strategy. Positive means profitable on average.',
    sections: [{ header: 'Interpretation', items: ['Negative: Strategy destroys value on average', 'Positive but small: Low edge, sensitive to costs and slippage', 'Large positive: Strong edge'] }],
  },
  avgWin: {
    title: 'Average Win',
    body: 'Mean dollar profit across all winning trades. Compare against Average Loss to evaluate the reward-to-risk profile.',
  },
  avgLoss: {
    title: 'Average Loss',
    body: 'Mean dollar loss across all losing trades. Ideally significantly smaller in magnitude than Average Win.',
  },
  riskReward: {
    title: 'Risk / Reward Ratio',
    body: 'Average Win divided by absolute Average Loss. Represents dollars earned for each dollar risked.',
    sections: [{ header: 'Benchmarks', items: ['< 1.0: Unfavourable — requires very high win rate to profit', '1.0–1.5: Acceptable with > 50% win rate', '1.5–2.5: Good', '> 2.5: Excellent'] }],
  },
  breakevenWin: {
    title: 'Breakeven Win Rate',
    body: 'Minimum win rate needed to break even at the current Risk/Reward. Calculated as: Avg Loss / (Avg Win + Avg Loss).',
    sections: [{ header: 'Usage', items: ['Current Win Rate must exceed this value to be profitable', 'Margin of safety = Win Rate − Breakeven Win Rate', 'Larger margin = more robust to regime changes'] }],
  },
  bestTrade: {
    title: 'Best Trade',
    body: 'Largest single-trade profit in the backtest. A very large outlier relative to the average may indicate the strategy relies on rare events.',
  },
  worstTrade: {
    title: 'Worst Trade',
    body: 'Largest single-trade loss. Compare to Average Loss to assess stop-loss consistency.',
  },
  avgBars: {
    title: 'Average Bars Held',
    body: 'Mean number of price bars a position was held open. Combined with timeframe, gives average trade duration.',
    sections: [{ items: ['Short hold times increase transaction cost impact', 'Long hold times expose capital to overnight / weekend risk'] }],
  },
  maxConsecWins: {
    title: 'Max Consecutive Wins',
    body: 'Longest unbroken sequence of profitable trades. Useful for understanding momentum characteristics and position sizing during hot streaks.',
  },
  maxConsecLosses: {
    title: 'Max Consecutive Losses',
    body: 'Longest unbroken losing sequence. Defines the worst-case losing run — live traders must be prepared to endure this without deviating from the strategy.',
    sections: [{ items: ['Used in Kelly Criterion and risk-of-ruin calculations', 'If this sequence would cause a margin call, reduce position sizing'] }],
  },
  longTrades: {
    title: 'Long Trades',
    body: 'Number of trades entered in the long (buy) direction. Compare to Short Trades to check for directional bias.',
  },
  shortTrades: {
    title: 'Short Trades',
    body: 'Number of trades entered in the short (sell) direction. Heavy skew toward one direction may mean the strategy only works in a specific market regime.',
  },
  startDate: {
    title: 'Backtest Start Date',
    body: 'First date from which price data was included in the backtest.',
  },
  endDate: {
    title: 'Backtest End Date',
    body: 'Last date up to which price data was included.',
  },
  duration: {
    title: 'Backtest Duration',
    body: 'Total calendar days covered. Longer periods expose the strategy to more market regimes and improve statistical robustness.',
    sections: [{ items: ['< 90 days: Insufficient for most strategies', '90–365 days: Acceptable minimum', '> 365 days: Recommended before live deployment'] }],
  },
  barsAnalyzed: {
    title: 'Bars Analyzed',
    body: 'Total number of price candles processed. Confirms data density and effective timeframe resolution.',
  },
};

function exitTypeTooltip(label: string, count: number, total: number): TooltipContent {
  return {
    title: `Exit: ${label}`,
    body: `${count} of ${total} trades (${((count / total) * 100).toFixed(0)}%) exited via "${label}".`,
    sections: [{ items: ['TP exits: take-profit target was reached', 'SL exits: stop-loss was hit', 'High SL% relative to TP% may indicate tight stops or poor entry timing'] }],
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

  const returnsRows: MetricRow[] = [
    { label: 'Total Return', value: `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`, color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT.totalReturn },
    { label: 'Net Profit', value: `${netProfit >= 0 ? '+' : ''}$${netProfit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, color: netProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT.netProfit },
    { label: 'Initial Capital', value: `$${result.initialCapital.toLocaleString()}`, tooltip: TT.initialCapital },
    { label: 'Final Capital', value: `$${result.finalCapital.toLocaleString()}`, tooltip: TT.finalCapital },
  ];

  const riskRows: MetricRow[] = [
    { label: 'Max Drawdown', value: `${result.maxDrawdown.toFixed(2)}%`, color: 'var(--accent-orange)', tooltip: TT.maxDrawdown },
    { label: 'Sharpe Ratio', value: result.sharpeRatio.toFixed(2), tooltip: TT.sharpe },
    { label: 'Sortino Ratio', value: result.sortino_ratio.toFixed(2), tooltip: TT.sortino },
  ];
  if (result.calmar_ratio != null) {
    riskRows.push({ label: 'Calmar Ratio', value: result.calmar_ratio.toFixed(2), tooltip: TT.calmar });
  }

  const tradeRows: MetricRow[] = [
    { label: 'Total Trades', value: String(result.totalTrades), tooltip: TT.totalTrades },
    { label: 'Win Rate', value: `${winPct}%`, color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT.winRate },
    { label: 'Winning Trades', value: String(result.winningTrades), color: 'var(--accent-green)', tooltip: TT.winningTrades },
    { label: 'Losing Trades', value: String(result.losingTrades), color: 'var(--accent-red)', tooltip: TT.losingTrades },
    { label: 'Profit Factor', value: result.profitFactor.toFixed(2), tooltip: TT.profitFactor },
    { label: 'Expectancy', value: `${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`, color: expectancy >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', tooltip: TT.expectancy },
    { label: 'Avg Win', value: `$${result.averageWin.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT.avgWin },
    { label: 'Avg Loss', value: `-$${Math.abs(result.averageLoss).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT.avgLoss },
    { label: 'Risk/Reward', value: rrRatio, tooltip: TT.riskReward },
    { label: 'Breakeven Win%', value: `${breakevenWinRate}%`, tooltip: TT.breakevenWin },
  ];

  const insightRows: MetricRow[] = [];
  if (tradeStats) {
    insightRows.push(
      { label: 'Best Trade', value: `${tradeStats.bestTrade >= 0 ? '+' : ''}$${tradeStats.bestTrade.toFixed(2)}`, color: 'var(--accent-green)', tooltip: TT.bestTrade },
      { label: 'Worst Trade', value: `-$${Math.abs(tradeStats.worstTrade).toFixed(2)}`, color: 'var(--accent-red)', tooltip: TT.worstTrade },
      { label: 'Avg Bars Held', value: tradeStats.avgBars.toFixed(1), tooltip: TT.avgBars },
      { label: 'Max Consec. Wins', value: String(tradeStats.maxConsecWins), color: 'var(--accent-green)', tooltip: TT.maxConsecWins },
      { label: 'Max Consec. Losses', value: String(tradeStats.maxConsecLosses), color: 'var(--accent-red)', tooltip: TT.maxConsecLosses },
    );
    if (tradeStats.longs + tradeStats.shorts > 0) {
      insightRows.push(
        { label: 'Long Trades', value: String(tradeStats.longs), tooltip: TT.longTrades },
        { label: 'Short Trades', value: String(tradeStats.shorts), tooltip: TT.shortTrades },
      );
    }
    for (const [exitType, count] of Object.entries(tradeStats.exitTypes)) {
      if (exitType === 'Unknown') continue;
      const pct = ((count / tradeStats.count) * 100).toFixed(0);
      insightRows.push({ label: `Exit: ${exitType}`, value: `${count} (${pct}%)`, tooltip: exitTypeTooltip(exitType, count, tradeStats.count) });
    }
  }

  const periodRows: MetricRow[] = [];
  if (result.startDate) periodRows.push({ label: 'Start Date', value: formatDate(result.startDate), tooltip: TT.startDate });
  if (result.endDate) periodRows.push({ label: 'End Date', value: formatDate(result.endDate), tooltip: TT.endDate });
  if (durationDays != null) periodRows.push({ label: 'Duration', value: `${durationDays} days`, tooltip: TT.duration });
  if (result.totalBars != null) periodRows.push({ label: 'Bars Analyzed', value: result.totalBars.toLocaleString(), tooltip: TT.barsAnalyzed });

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
