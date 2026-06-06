'use client';

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { BacktestStatusMessage, BacktestResult } from '@/lib/strategy-builder/types';
import { BacktestCountersRow } from './BacktestCountersRow';
import {
  EVENT_DEFS,
  EVENT_GROUPS,
  EVENT_BY_KEY,
  BACKTEST_VISIBLE_KEYS,
  type EventKey,
  matchEvents,
  isContextLine,
  colorForLine,
} from './liveOutputEvents';

export interface LiveOutputPanelProps {
  logs?: BacktestStatusMessage[];
  isRunning?: boolean;
  /** Latest run result — drives the Candles/Trades/TP-SL breakdown counters
   *  at the top of the panel. The same counter row is also rendered at the
   *  bottom-right of the Config tab STATUS section (BTCAAAAA-34582). */
  result?: BacktestResult | null;
}

const FILTERS_STORAGE_KEY = 'backtest.liveOutput.filters.v1';

function loadStoredFilters(): Set<EventKey> | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return null;
    const arr = JSON.parse(raw) as unknown;
    if (!Array.isArray(arr)) return null;
    const keys = arr.filter((x): x is EventKey => typeof x === 'string' && x in EVENT_BY_KEY);
    return new Set(keys);
  } catch {
    return null;
  }
}

function defaultEnabledSet(): Set<EventKey> {
  // Thick-client parity: `event_filters` defaults to all-24-on
  // (log_viewer_window.py:469). Tab visibility only hides chips, it does
  // not disable filters — so untagged-looking lines like
  // "Loading bars from Binance…" (CONFIG_READ) still flow through.
  return new Set(EVENT_DEFS.map((d) => d.key));
}

export function LiveOutputPanel({ logs = [], isRunning = false, result = null }: LiveOutputPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [enabled, setEnabled] = useState<Set<EventKey>>(() => defaultEnabledSet());

  useEffect(() => {
    const stored = loadStoredFilters();
    if (stored && stored.size > 0) setEnabled(stored);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(Array.from(enabled)));
    } catch {
      // localStorage may be unavailable (private mode / quota) — silent ignore.
    }
  }, [enabled]);

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  const toggleKey = useCallback((key: EventKey) => {
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Visible chip keys come from the Backtest tab subset
  // (log_viewer_window.py:847-850). Hidden filters stay always-on, matching
  // thick-client behavior where tab visibility limits chips but not filters.
  const toggleAll = useCallback(() => {
    setEnabled((prev) => {
      const allChipsOn = BACKTEST_VISIBLE_KEYS.every((k) => prev.has(k));
      const next = new Set(prev);
      if (allChipsOn) {
        for (const k of BACKTEST_VISIBLE_KEYS) next.delete(k);
      } else {
        for (const k of BACKTEST_VISIBLE_KEYS) next.add(k);
      }
      return next;
    });
  }, []);

  // Mirrors ContentCache.filter (log_viewer_window.py:158-175): keep
  // matched lines; carry context lines through while `inContext` is true.
  const { rows, totalLines, displayedLines, eventCount } = useMemo(() => {
    let inContext = false;
    let displayed = 0;
    let events = 0;
    const built: Array<{ key: string; text: string; color: string; isContext: boolean; ts?: string }> = [];

    for (let i = 0; i < logs.length; i++) {
      const msg = logs[i];
      const text = msg.message ?? '';
      const matched = matchEvents(text);
      const matchedEnabled = Array.from(matched).some((k) => enabled.has(k));

      const isCtx = isContextLine(text);
      let keep = false;

      if (matchedEnabled) {
        keep = true;
        inContext = true;
        events += 1;
      } else if (inContext && (isCtx || text.trim() === '')) {
        keep = true;
      } else {
        inContext = false;
      }

      if (keep) {
        displayed += 1;
        const c = colorForLine(text) ?? levelFallbackColor(msg.level);
        built.push({
          key: `${i}`,
          text,
          color: c,
          isContext: isCtx,
          ts: msg.timestamp,
        });
      }
    }

    return {
      rows: built,
      totalLines: logs.length,
      displayedLines: displayed,
      eventCount: events,
    };
  }, [logs, enabled]);

  const allChipsOn = BACKTEST_VISIBLE_KEYS.every((k) => enabled.has(k));

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

      {/* Event-filter groups — thick-client parity. Border color per group
          mirrors the dominant event color family in styles.py. Chips render
          in their exact thick-client color (no fill — matches
          `get_event_filter_checkbox_style` styles.py:2025). */}
      <div className="mb-2 flex flex-wrap items-stretch gap-2" data-testid="live-output-filters">
        {EVENT_GROUPS.map((group) => (
          <div
            key={group.title}
            className="flex flex-col rounded px-2 py-1.5"
            style={{
              border: `1px solid ${group.borderColor}`,
              background: 'var(--bg-deep)',
            }}
          >
            <span
              className="text-[10px] uppercase tracking-wider mb-1 font-semibold"
              style={{ color: group.borderColor }}
            >
              {group.title}
            </span>
            <div className="flex flex-wrap gap-x-2 gap-y-1">
              {group.keys.map((k) => {
                const def = EVENT_BY_KEY[k];
                const on = enabled.has(k);
                return (
                  <label
                    key={k}
                    className="flex items-center gap-1 cursor-pointer select-none text-[11px]"
                    style={{ color: def.color, opacity: on ? 1 : 0.4 }}
                    title={`Filter: ${def.label}`}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggleKey(k)}
                      aria-label={def.label}
                      style={{ accentColor: def.color }}
                    />
                    <span>{def.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={toggleAll}
          className="text-[11px] px-3 rounded self-stretch"
          style={{
            background: 'var(--bg-deep)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
          }}
          title="Toggle all event filters"
        >
          {allChipsOn ? 'Unselect All' : 'Select All'}
        </button>
      </div>

      {/* Stat counters (Total / Displayed / Events) — mirrors thick-client
          bottom-bar (`_create_bottom_bar` log_viewer_window.py:647). Events
          counter uses the warning color (#FFA500) per
          `get_label_style("warning")`. */}
      <div className="mb-1 flex items-center gap-4 text-[11px]" data-testid="live-output-stats">
        <span style={{ color: 'var(--text-muted)' }}>
          Total Lines: <b>{totalLines.toLocaleString()}</b>
        </span>
        <span style={{ color: 'var(--text-muted)' }}>
          Displayed: <b>{displayedLines.toLocaleString()}</b>
        </span>
        <span style={{ color: '#FFA500' }}>
          Events: <b>{eventCount.toLocaleString()}</b>
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
        {logs.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            {isRunning ? 'Waiting for output…' : 'No output yet. Start a backtest to see live output.'}
          </p>
        ) : rows.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            No lines match the active filters.
          </p>
        ) : (
          rows.map((row) => (
            <div key={row.key} className="flex gap-2 mb-1 leading-relaxed">
              <span style={{ color: 'var(--text-faint)', flexShrink: 0 }}>
                {row.ts ? new Date(row.ts).toLocaleTimeString() : ''}
              </span>
              <span style={{ color: row.color, paddingLeft: row.isContext ? 12 : 0 }}>
                {row.text}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function levelFallbackColor(level: BacktestStatusMessage['level']): string {
  // Only consulted when no EVENT_PATTERN matches. Keeps prior coarse
  // INFO/SYSTEM/ERROR coloring as a graceful fallback.
  switch (level) {
    case 'ERROR':
      return 'var(--accent-red)';
    case 'SYSTEM':
      return 'var(--accent-orange)';
    default:
      return 'var(--text-secondary)';
  }
}

export { EVENT_DEFS, EVENT_GROUPS };
