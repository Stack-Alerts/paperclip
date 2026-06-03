'use client';

import { useRef, useEffect, useState } from 'react';
import { BacktestStatusMessage, BacktestResult, Trade } from '@/lib/strategy-builder/types';

export interface LiveOutputPanelProps {
  logs?: BacktestStatusMessage[];
  isRunning?: boolean;
  /** Latest run result — drives the TP/SL breakdown counters that used
   *  to live in the Config tab's progress widget (board revision
   *  2026-06-03 moved them into Live Output). */
  result?: BacktestResult | null;
}

// Idle-state checklist — verbatim from the thick-client placeholder in
// `_create_config_tab()` (src/strategy_builder/ui/backtest_config_panel.py
// lines 1252–1273). Board moved this off the Config tab into Live Output
// so the Config form fits without scrolling.
const IDLE_LINES: string[] = [
  'Status updates will appear here when backtest starts...',
  '',
  'During backtest you will see:',
  '✅ Data loading progress from Unified Data Manager',
  '✅ NautilusTrader initialization',
  '✅ Bar aggregation status',
  '✅ Hybrid data source routing (LakeAPI + Binance)',
  '✅ Real-time processing updates',
  '',
  'All terminal output will be captured and displayed here.',
];

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

export function LiveOutputPanel({ logs = [], isRunning = false, result = null }: LiveOutputPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const showIdle = logs.length === 0 && !isRunning;
  const tradeCount = result?.totalTrades ?? result?.trades?.length ?? 0;
  const adj = tallyAdjustments(result?.trades);

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  const levelColor = (level: BacktestStatusMessage['level']) => {
    switch (level) {
      case 'ERROR': return 'var(--accent-red)';
      case 'SYSTEM': return 'var(--accent-orange)';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ minHeight: 300 }}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          Live Output
        </p>
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="text-xs" style={{ color: 'var(--accent-green)' }}>
              ● RUNNING
            </span>
          )}
          <button
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
            className="text-xs px-2 py-1 rounded"
            style={{
              background: isPaused ? 'var(--bg-hover)' : 'transparent',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
            }}
            title="Hover to pause auto-scroll"
          >
            {isPaused ? 'Paused' : 'Auto-scroll'}
          </button>
        </div>
      </div>

      {/* Run counters row — moved from the Config tab's progress widget
          (BTCAAAAA-34190 board revision 2026-06-03). Trades + TP/SL
          breakdown appear here so the Config tab can stay scroll-free. */}
      <div
        className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-2 text-[11px]"
        style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
      >
        <span>
          Trades:{' '}
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{tradeCount.toLocaleString()}</span>
        </span>
        <span>
          TP/SL Adjustments:{' '}
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{adj.total.toLocaleString()}</span>{' '}
          <span style={{ color: 'var(--text-faint)' }}>
            (TP1: {adj.TP1}, TP2: {adj.TP2}, TP3: {adj.TP3}, SL: {adj.SL})
          </span>
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded font-mono text-xs"
        style={{
          background: 'var(--bg-deep)',
          border: '1px solid var(--border)',
          padding: '0.75rem',
          minHeight: 200,
          maxHeight: 400,
        }}
      >
        {showIdle ? (
          // Verbatim thick-client idle checklist (board revision 2026-06-03 moved
          // it from a Config-tab Status panel into Live Output's empty state).
          <ul className="space-y-0.5 leading-relaxed">
            {IDLE_LINES.map((line, idx) => (
              <li
                key={idx}
                style={{
                  color: line.startsWith('✅') ? 'var(--text-secondary)' : 'var(--text-muted)',
                  minHeight: '1em',
                }}
              >
                {line || ' '}
              </li>
            ))}
          </ul>
        ) : logs.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>Waiting for output…</p>
        ) : (
          logs.map((msg, i) => (
            <div key={i} className="flex gap-2 mb-1 leading-relaxed">
              <span style={{ color: 'var(--text-faint)', flexShrink: 0 }}>
                {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
              </span>
              <span style={{ color: levelColor(msg.level) }}>{msg.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
