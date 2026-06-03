'use client';

import { BacktestResult } from '@/lib/strategy-builder/types';

export interface BacktestProgressMeterProps {
  /** 0–100, drives the bar fill and the right-aligned percentage. */
  progress: number;
  /** True while a backtest is mid-flight; tints the bar muted vs. accent. */
  isRunning: boolean;
  /** Latest run result — when present (and `isRunning` is false) the row
   *  reports a completed state instead of idle. */
  result?: BacktestResult | null;
  /** Optional inline candle counter (`current / total`) shown next to the
   *  status word when the caller has live bar counts. */
  candles?: { current: number; total: number };
}

// Cycle-12 inline-status row (CEO over-correction 2026-06-03):
// single ≤24px row with `● <State>` on the left, slim 3px bar in the middle,
// and right-aligned `N%` (plus optional `Candles N/M  Trades K` ultra-compact
// muted counters). No card, no border, no header. The detailed Status
// checklist + event stream remain in the Live Output tab.
export function BacktestProgressMeter({
  progress,
  isRunning,
  result,
  candles,
}: BacktestProgressMeterProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  const candleCurrent = candles?.current ?? 0;
  const candleTotal = candles?.total ?? 0;
  const hasCandles = !!candles && candleTotal > 0;
  const tradeCount = result?.totalTrades ?? result?.trades?.length ?? 0;
  const isComplete = !isRunning && !!result;

  const stateLabel = isRunning ? 'Running' : isComplete ? 'Complete' : 'Idle';
  const dotColor = isRunning
    ? 'var(--accent-blue)'
    : isComplete
      ? 'var(--accent-green)'
      : 'var(--text-faint)';
  const stateColor = isRunning
    ? 'var(--accent-blue)'
    : isComplete
      ? 'var(--accent-green)'
      : 'var(--text-muted)';

  return (
    <div className="flex items-center gap-2 w-full text-[11px]" style={{ minHeight: 18 }}>
      <span
        className="flex items-center gap-1 flex-shrink-0"
        style={{ color: stateColor, fontVariantNumeric: 'tabular-nums' }}
      >
        <span
          aria-hidden="true"
          className={isRunning ? 'animate-pulse' : ''}
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: dotColor,
          }}
        />
        {stateLabel}
      </span>

      {hasCandles && (
        <span
          className="flex-shrink-0"
          style={{ color: 'var(--text-faint)', fontVariantNumeric: 'tabular-nums' }}
        >
          {candleCurrent.toLocaleString()} / {candleTotal.toLocaleString()}
        </span>
      )}
      {(isRunning || isComplete) && (
        <span
          className="flex-shrink-0"
          style={{ color: 'var(--text-faint)', fontVariantNumeric: 'tabular-nums' }}
        >
          Trades {tradeCount.toLocaleString()}
        </span>
      )}

      <div
        className="flex-1 h-[3px] rounded-full overflow-hidden"
        style={{ background: 'var(--border)' }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Backtest progress"
      >
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            background: isRunning
              ? 'var(--accent-blue)'
              : isComplete
                ? 'var(--accent-green)'
                : 'var(--text-faint)',
          }}
        />
      </div>

      <span
        className="flex-shrink-0"
        style={{
          color: 'var(--text-muted)',
          fontVariantNumeric: 'tabular-nums',
          minWidth: 28,
          textAlign: 'right',
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

export default BacktestProgressMeter;
