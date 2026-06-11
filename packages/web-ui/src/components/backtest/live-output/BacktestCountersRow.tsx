'use client';

import { BacktestResult, Trade } from '@/lib/strategy-builder/types';

export interface BacktestCountersRowProps {
  /** Latest run result — drives Trades and TP/SL Adjustments tallies. */
  result?: BacktestResult | null;
  /** Optional candle progress; idle/no-source renders as `0 / 0`. */
  candles?: { current: number; total: number };
  /** Horizontal alignment within the parent flex/block. Defaults to `start`. */
  align?: 'start' | 'end';
  /** Optional override for the row font size. Defaults to 11px. */
  fontSize?: string;
  className?: string;
}

function tallyAdjustments(trades: Trade[] | undefined) {
  const tally = { TP1: 0, TP2: 0, TP3: 0, SL: 0 };
  if (trades) {
    for (const t of trades) {
      const key = (t.exitType ?? '').toUpperCase();
      if (key === 'TP1' || key === 'TP2' || key === 'TP3' || key === 'SL') {
        tally[key] += 1;
      }
    }
  }
  return { ...tally, total: tally.TP1 + tally.TP2 + tally.TP3 + tally.SL };
}

// Single-line counter row shared between the Config tab STATUS section
// (bottom-right anchor) and the Live Output tab header (BTCAAAAA-34582). Both
// surfaces read from the same `backTestResult` so the values always agree.
export function BacktestCountersRow({
  result = null,
  candles,
  align = 'start',
  fontSize = '11px',
  className = '',
}: BacktestCountersRowProps) {
  const candleTotal = candles?.total ?? result?.totalBars ?? 0;
  const candleCurrent = candles?.current ?? candleTotal;
  const tradeCount = result?.totalTrades ?? result?.trades?.length ?? 0;
  const adj = tallyAdjustments(result?.trades);
  const sep = (
    <span aria-hidden="true" style={{ color: 'var(--text-faint)' }}>
      |
    </span>
  );
  return (
    <div
      className={`flex flex-wrap items-center gap-x-2 gap-y-1 ${align === 'end' ? 'justify-end' : ''} ${className}`}
      style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums', fontSize }}
    >
      <span>
        Candles:{' '}
        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
          {candleCurrent.toLocaleString()} / {candleTotal.toLocaleString()}
        </span>
      </span>
      {sep}
      <span>
        Trades:{' '}
        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{tradeCount.toLocaleString()}</span>
      </span>
      {sep}
      <span>
        TP/SL Adjustments:{' '}
        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{adj.total.toLocaleString()}</span>{' '}
        <span style={{ color: 'var(--text-faint)' }}>
          (TP1: {adj.TP1}, TP2: {adj.TP2}, TP3: {adj.TP3}, SL: {adj.SL})
        </span>
      </span>
    </div>
  );
}

export default BacktestCountersRow;
