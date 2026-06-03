'use client';

import { useEffect, useRef } from 'react';
import { BacktestStatusMessage } from '@/lib/strategy-builder/types';

export interface BacktestStatusPanelProps {
  /** Status / log feed from the active or last backtest run. */
  logs: BacktestStatusMessage[];
  /** True while a backtest is mid-flight. */
  isRunning: boolean;
  /** Cap on rendered rows when streaming. Defaults to 200 so the panel
   *  doesn't grow unbounded during long historical runs. */
  maxRows?: number;
}

// Idle-state checklist text — matches the thick-client placeholder in
// `_create_config_tab()` (src/strategy_builder/ui/backtest_config_panel.py
// lines 1252–1273). The list serves two purposes: it tells the user what
// the panel will show during a run, and it gives the empty box a sensible
// minimum height so the layout doesn't shift the moment a run begins.
const IDLE_LINES: Array<{ text: string; tone: 'header' | 'check' | 'footer' }> = [
  { text: 'Status updates will appear here when backtest starts...', tone: 'header' },
  { text: '', tone: 'header' },
  { text: 'During backtest you will see:', tone: 'header' },
  { text: '✅ Data loading progress from Unified Data Manager', tone: 'check' },
  { text: '✅ NautilusTrader initialization', tone: 'check' },
  { text: '✅ Bar aggregation status', tone: 'check' },
  { text: '✅ Hybrid data source routing (LakeAPI + Binance)', tone: 'check' },
  { text: '✅ Real-time processing updates', tone: 'check' },
  { text: '', tone: 'check' },
  { text: 'All terminal output will be captured and displayed here.', tone: 'footer' },
];

function levelColor(level: BacktestStatusMessage['level']) {
  switch (level) {
    case 'ERROR':
      return 'var(--accent-red)';
    case 'SYSTEM':
      return 'var(--accent-blue)';
    default:
      return 'var(--text-secondary)';
  }
}

export function BacktestStatusPanel({
  logs,
  isRunning,
  maxRows = 200,
}: BacktestStatusPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const showIdle = logs.length === 0 && !isRunning;
  const recent = logs.slice(-maxRows);

  useEffect(() => {
    if (!showIdle && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [recent, showIdle]);

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
          className="text-xs font-semibold tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          <span aria-hidden="true">📊</span> Status
        </span>
        <span
          className="text-xs"
          style={{ color: isRunning ? 'var(--accent-blue)' : 'var(--text-faint)' }}
        >
          {isRunning ? 'Running…' : showIdle ? 'Idle' : 'Last run'}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="px-3 py-2.5 font-mono text-[11px] leading-relaxed overflow-y-auto"
        style={{
          background: 'var(--bg-deep)',
          minHeight: 160,
          maxHeight: 240,
          color: 'var(--text-secondary)',
        }}
      >
        {showIdle ? (
          <ul className="space-y-0.5">
            {IDLE_LINES.map((line, idx) => (
              <li
                key={idx}
                style={{
                  color:
                    line.tone === 'check'
                      ? 'var(--text-secondary)'
                      : 'var(--text-muted)',
                  minHeight: '1em',
                }}
              >
                {line.text || ' '}
              </li>
            ))}
          </ul>
        ) : recent.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>Waiting for output…</p>
        ) : (
          <ul className="space-y-0.5">
            {recent.map((msg, idx) => (
              <li
                key={`${msg.timestamp}-${idx}`}
                className="flex gap-2"
                style={{ color: levelColor(msg.level), fontVariantNumeric: 'tabular-nums' }}
              >
                <span style={{ color: 'var(--text-faint)', flexShrink: 0 }}>
                  {msg.timestamp ? new Date(msg.timestamp).toISOString().slice(11, 19) : ''}
                </span>
                <span className="break-words">{msg.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default BacktestStatusPanel;
