'use client';

import { useRef, useEffect, useState } from 'react';
import { BacktestStatusMessage, BacktestResult } from '@/lib/strategy-builder/types';
import { BacktestCountersRow } from './BacktestCountersRow';

export interface LiveOutputPanelProps {
  logs?: BacktestStatusMessage[];
  isRunning?: boolean;
  /** Latest run result — drives the Candles/Trades/TP-SL breakdown counters
   *  at the top of the panel. The same counter row is also rendered at the
   *  bottom-right of the Config tab STATUS section (BTCAAAAA-34582). */
  result?: BacktestResult | null;
}

export function LiveOutputPanel({ logs = [], isRunning = false, result = null }: LiveOutputPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);

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

      {/* Run counters row — shared with the Config tab STATUS section
          (BTCAAAAA-34582). Both surfaces read from the same `result` so the
          values always agree. */}
      <BacktestCountersRow result={result} className="mb-2" />


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
        {logs.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            {isRunning ? 'Waiting for output…' : 'No output yet. Start a backtest to see live output.'}
          </p>
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
