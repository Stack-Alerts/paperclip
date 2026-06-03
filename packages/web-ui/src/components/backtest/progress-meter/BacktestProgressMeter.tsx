'use client';

import { BacktestResult } from '@/lib/strategy-builder/types';

export interface BacktestProgressMeterProps {
  /** 0–100, drives the bar fill and the inline percentage. */
  progress: number;
  /** True while a backtest is mid-flight; tints the bar muted vs. accent. */
  isRunning: boolean;
  /** Latest run result — only used for the candle count override below. */
  result?: BacktestResult | null;
  /** Optional candle counter shown inline after the percentage when the
   *  caller has live bar counts to surface. Hidden by default to honour
   *  the board's "no multi-line counter row" directive. */
  candles?: { current: number; total: number };
}

// Slim, frameless progress indicator (board revision 2026-06-03):
// - No "PROGRESS" header, no card border, no background fill panel.
// - 3px bar (within the 2–4px board range) anchored on its caller's row.
// - Single inline row to the right with `N%` and an optional candle count.
// - TP/SL Adjustments breakdown moved to LiveOutputPanel; no counters here.
export function BacktestProgressMeter({
  progress,
  isRunning,
  candles,
}: BacktestProgressMeterProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  const candleCurrent = candles?.current ?? 0;
  const candleTotal = candles?.total ?? 0;
  const hasCandles = !!candles && candleTotal > 0;

  return (
    <div className="flex items-center gap-2 w-full">
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
            background: isRunning ? 'var(--accent-blue)' : 'var(--text-faint)',
          }}
        />
      </div>
      <span
        className="text-[10px] flex-shrink-0"
        style={{
          color: 'var(--text-muted)',
          fontVariantNumeric: 'tabular-nums',
          minWidth: 28,
          textAlign: 'right',
        }}
      >
        {hasCandles ? `${candleCurrent.toLocaleString()} / ${candleTotal.toLocaleString()}` : `${pct}%`}
      </span>
    </div>
  );
}

export default BacktestProgressMeter;
