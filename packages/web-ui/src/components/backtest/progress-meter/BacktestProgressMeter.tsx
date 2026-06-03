'use client';

import { Trade, BacktestResult, TpSlAdjustments } from '@/lib/strategy-builder/types';

export interface BacktestProgressMeterProps {
  /** 0–100, drives the bar fill and the right-aligned percentage. */
  progress: number;
  /** True while a backtest is mid-flight; controls the live/idle wording. */
  isRunning: boolean;
  /** Latest run result — drives Trades + TP/SL Adjustments breakdown. */
  result?: BacktestResult | null;
  /** Optional override for the candle counter (used when the backend
   *  starts emitting bar counts; defaults to '0 / 0' to match the thick
   *  client's idle screenshot). */
  candles?: { current: number; total: number };
}

function tallyAdjustments(trades: Trade[] | undefined): TpSlAdjustments & { total: number } {
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

export function BacktestProgressMeter({
  progress,
  isRunning,
  result,
  candles,
}: BacktestProgressMeterProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  const trades = result?.trades ?? [];
  const tradeCount = result?.totalTrades ?? trades.length;
  const adj = tallyAdjustments(trades);
  const candleCurrent = candles?.current ?? 0;
  const candleTotal = candles?.total ?? 0;

  return (
    <div
      className="rounded-[4px]"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-1.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <span
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          Progress
        </span>
        <span
          className="text-xs"
          style={{
            color: isRunning ? 'var(--accent-blue)' : 'var(--text-faint)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {pct}%
        </span>
      </div>

      <div className="px-3 py-2.5 space-y-2">
        <div
          className="w-full h-2.5 rounded-full overflow-hidden"
          style={{ background: 'var(--bg-deep)' }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Backtest progress"
        >
          <div
            className="h-full transition-all duration-300"
            style={{ width: `${pct}%`, background: 'var(--accent-blue)' }}
          />
        </div>

        <div
          className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]"
          style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
        >
          <span>
            Candles:{' '}
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              {candleCurrent.toLocaleString()} / {candleTotal.toLocaleString()}
            </span>
          </span>
          <span>
            Trades:{' '}
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              {tradeCount.toLocaleString()}
            </span>
          </span>
          <span>
            TP/SL Adjustments:{' '}
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              {adj.total.toLocaleString()}
            </span>{' '}
            <span style={{ color: 'var(--text-faint)' }}>
              (TP1: {adj.TP1}, TP2: {adj.TP2}, TP3: {adj.TP3}, SL: {adj.SL})
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

export default BacktestProgressMeter;
