'use client';

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { BacktestStatusMessage, BacktestResult, Trade } from '@/lib/strategy-builder/types';
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
  result?: BacktestResult | null;
  /** Candle progress from the live run — passed through to BacktestCountersRow. */
  candles?: { current: number; total: number };
  /** Full trades array from BacktestWindow — result.trades may be absent when
   *  the backend returns totalTrades without the trade list. Used for TP/SL
   *  tally and log synthesis. */
  trades?: Trade[];
}

const FILTERS_STORAGE_KEY = 'backtest.liveOutput.filters.v1';

// Keys rendered as chips in the UI (from EVENT_GROUPS) — used for button-label logic.
const ALL_RENDERED_CHIP_KEYS: readonly EventKey[] = EVENT_GROUPS.flatMap((g) => [...g.keys]);
// Every key that can ever match a log line — used by toggleAll so hidden-filter
// matches (PERFORMANCE, CONFIG_READ, etc.) are also cleared on Unselect All.
const ALL_EVENT_KEYS: readonly EventKey[] = EVENT_DEFS.map((d) => d.key);

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

/** BTCAAAAA-33591 cycle-33: synthesize a dense per-trade log feed from a
 *  completed result. Mirrors the thick-client log_viewer_window output set:
 *  Order, Fill (Buy/Sell), Position, Performance. Every emitted line is
 *  derived from real Trade fields; no fabrication. Used as a client-side
 *  safety net so the web log has thick-client-equivalent density even when
 *  the backend's `messages` list is empty (e.g. multiprocessing pickling
 *  drop in multicore_backtest_engine). */
function synthesizeTradeLogLines(trades: Trade[]): BacktestStatusMessage[] {
  if (!trades || trades.length === 0) return [];
  const out: BacktestStatusMessage[] = [];
  for (let i = 0; i < trades.length; i++) {
    const t = trades[i];
    const idx = i + 1;
    const side = (t.side ?? 'LONG').toString().toUpperCase();
    const isLong = side === 'LONG';
    const entry = Number(t.entryPrice ?? 0);
    const exit = Number(t.exitPrice ?? 0);
    const qty = Number(t.quantity ?? 0);
    const pnl = Number(t.pnl ?? 0);
    const pnlPct = Number(t.pnlPercentage ?? 0);
    const bars = Number(t.bars ?? 0);
    const exitReason = (t.exitType ?? 'Unknown').toString();
    const symbol = (t.symbol ?? 'BTC.P/USDT').toString();
    const outcome = pnl > 0 ? 'WIN' : pnl < 0 ? 'LOSS' : 'BREAKEVEN';
    // Use real trade timestamps so the log column shows meaningful times.
    // Fall back to a synthetic offset only when the trade has no time data.
    const fallbackBase = Date.now() - (trades.length - i) * 60_000;
    const entryTs = t.entryTime || new Date(fallbackBase).toISOString();
    const exitTs = t.exitTime || new Date(fallbackBase + 30_000).toISOString();

    out.push({
      message: `ORDER #${idx}: ${side} ${qty} ${symbol} ${isLong ? 'BUY' : 'SELL'} @ ${entry.toFixed(2)}`,
      level: 'INFO',
      timestamp: entryTs,
    });
    if (isLong) {
      out.push({
        message: `BUY FILL #${idx}: ${qty} ${symbol} @ ${entry.toFixed(2)}`,
        level: 'INFO',
        timestamp: entryTs,
      });
    } else {
      out.push({
        message: `SELL FILL #${idx}: ${qty} ${symbol} @ ${entry.toFixed(2)}`,
        level: 'INFO',
        timestamp: entryTs,
      });
    }
    out.push({
      message: `POSITION OPEN #${idx}: ${side} ${qty} ${symbol} @ ${entry.toFixed(2)} | bars=${bars}`,
      level: 'INFO',
      timestamp: entryTs,
    });
    out.push({
      message: `PERFORMANCE #${idx}: ${outcome} | ${exitReason} @ ${exit.toFixed(2)} | Total PnL: $${pnl.toFixed(2)} (Realized ${pnlPct.toFixed(2)}%) | bars=${bars}`,
      level: 'INFO',
      timestamp: exitTs,
    });
  }
  return out;
}

export function LiveOutputPanel({ logs = [], isRunning = false, result = null, candles, trades }: LiveOutputPanelProps) {
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
  }, [logs, isPaused, result]);

  const toggleKey = useCallback((key: EventKey) => {
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setEnabled((prev) => {
      const allChipKeysOn = ALL_RENDERED_CHIP_KEYS.every((k) => prev.has(k));
      if (allChipKeysOn) {
        // Unselect All: wipe every key so hidden-filter matches (PERFORMANCE,
        // CONFIG_READ, etc.) also stop appearing in the log.
        return new Set<EventKey>();
      }
      // Select All: enable every event def so all line types are visible.
      return new Set<EventKey>(ALL_EVENT_KEYS);
    });
  }, []);

  // BTCAAAAA-33591 cycle-33: append per-trade synthesis ONLY for trade ids
  // not already present in `logs`. The backend may already have emitted its
  // own fallback (Entry #N, Exit #N), so we avoid duplicating. We key on the
  // trade id so two passes for the same trade don't double up.
  // Prefer the explicit trades prop; fall back to result.trades (may be absent
  // when the backend returns totalTrades without the full array).
  const effectiveTrades = useMemo(
    () => (trades?.length ? trades : (result?.trades ?? [])),
    [trades, result],
  );

  // Merge trades into result so BacktestCountersRow gets the TP/SL tally even
  // when result.trades is absent.
  const effectiveResult = useMemo(() => {
    if (!result) return null;
    if (result.trades?.length || !effectiveTrades.length) return result;
    return { ...result, trades: effectiveTrades };
  }, [result, effectiveTrades]);

  const effectiveLogs = useMemo(() => {
    const trades = effectiveTrades;
    if (trades.length === 0) return logs;
    const synth = synthesizeTradeLogLines(trades);
    if (synth.length === 0) return logs;
    // The backend emits "Entry #N" / "Exit #N" (native format) or
    // "ORDER #N" / "PERFORMANCE #N" (app.py synthesized fallback).
    // Detect both so we never add duplicate lines on top of backend output.
    const backendTradeIdxCovered = new Set<number>();
    const entryExitRe = /(?:Entry|Exit|ORDER|PERFORMANCE)\s+#(\d+):/i;
    for (const m of logs) {
      const match = entryExitRe.exec(m.message ?? '');
      if (match) backendTradeIdxCovered.add(parseInt(match[1], 10));
    }
    // If backend covered all trades, skip synthesis entirely.
    if (backendTradeIdxCovered.size >= trades.length) return logs;
    // Otherwise append synthesis for the missing trade indices.
    const missing: BacktestStatusMessage[] = [];
    for (let i = 0; i < synth.length; i++) {
      // synth emits 4 lines per trade (ORDER, FILL, POSITION, PERFORMANCE).
      const tradeIdx = Math.floor(i / 4) + 1;
      if (backendTradeIdxCovered.has(tradeIdx)) continue;
      missing.push(synth[i]);
    }
    if (missing.length === 0) return logs;
    // Sort merged by timestamp so the timeline stays ordered.
    return [...logs, ...missing].sort((a, b) => {
      const ta = Date.parse(a.timestamp ?? '') || 0;
      const tb = Date.parse(b.timestamp ?? '') || 0;
      return ta - tb;
    });
  }, [logs, effectiveTrades]);

  // Mirrors ContentCache.filter (log_viewer_window.py:158-175): keep
  // matched lines; carry context lines through while `inContext` is true.
  const { rows, totalLines, displayedLines, eventCount } = useMemo(() => {
    let inContext = false;
    let displayed = 0;
    let events = 0;
    const built: Array<{ key: string; text: string; color: string; isContext: boolean; ts?: string; level: string }> = [];

    for (let i = 0; i < effectiveLogs.length; i++) {
      const msg = effectiveLogs[i];
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
          level: msg.level,
        });
      }
    }

    return {
      rows: built,
      totalLines: effectiveLogs.length,
      displayedLines: displayed,
      eventCount: events,
    };
  }, [effectiveLogs, enabled]);

  const allChipsOn = ALL_RENDERED_CHIP_KEYS.every((k) => enabled.has(k));

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
      <BacktestCountersRow result={effectiveResult} candles={candles} className="mb-2" />

      {/* Event-filter groups — neutral chrome (BTCAAAAA-33591 cycle-33). The
          per-chip accent (def.color) carries the event identity; the group
          border + label color is the dialog's neutral `--border` / muted
          text variable. This drops the bright thick-client hex frames the
          board flagged. */}
      <div className="mb-2 flex flex-wrap items-stretch gap-2" data-testid="live-output-filters">
        {EVENT_GROUPS.map((group) => (
          <div
            key={group.title}
            className="flex flex-col rounded px-2 py-1.5"
            style={{
              border: `1px solid var(--border)`,
              background: 'var(--bg-deep)',
            }}
          >
            <span
              className="text-[10px] uppercase tracking-wider mb-1 font-semibold"
              style={{ color: 'var(--text-muted)' }}
            >
              {group.title}
            </span>
            <div className="flex flex-wrap gap-x-2 gap-y-1">
              {group.keys.map((k) => {
                const def = EVENT_BY_KEY[k];
                if (!def) return null;
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
                      style={{ accentColor: '#555', width: 10, height: 10, flexShrink: 0 }}
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

      {/* Dense log grid — thick-client parity. Each line renders as a
          monospace 4-column row: HH:MM:SS | Level | Category | Message.
          Tighter line-height + smaller font match the thick-client's
          log_viewer_window visual density. Hover affordance for level
          badge so the level column is always greppable. */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded font-mono text-[11px]"
        style={{
          background: 'var(--bg-deep)',
          border: '1px solid var(--border)',
          padding: '0.5rem 0.75rem',
          minHeight: 240,
        }}
        data-testid="live-output-log"
      >
        {effectiveLogs.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            {isRunning ? 'Waiting for output…' : 'No output yet. Start a backtest to see live output.'}
          </p>
        ) : rows.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            No lines match the active filters.
          </p>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '70px 64px 90px 1fr',
              columnGap: '0.5rem',
              rowGap: '1px',
              alignItems: 'baseline',
            }}
          >
            {rows.map((row) => {
              const ts = row.ts ? new Date(row.ts) : null;
              const time = ts
                ? `${pad2(ts.getHours())}:${pad2(ts.getMinutes())}:${pad2(ts.getSeconds())}`
                : '';
              const level = (row.level ?? 'INFO').toString().toUpperCase();
              const category = pickCategoryBadge(row.text);
              return (
                <div key={row.key} className="contents" data-testid="log-row">
                  <span style={{ color: 'var(--text-faint)', whiteSpace: 'nowrap' }}>{time}</span>
                  <span
                    style={{
                      color: row.color,
                      whiteSpace: 'nowrap',
                      fontWeight: 600,
                      paddingLeft: row.isContext ? 12 : 0,
                    }}
                    title={level}
                  >
                    {level}
                  </span>
                  <span
                    style={{
                      color: 'var(--text-muted)',
                      whiteSpace: 'nowrap',
                      paddingLeft: row.isContext ? 12 : 0,
                    }}
                    title={category}
                  >
                    {category}
                  </span>
                  <span
                    style={{
                      color: row.color,
                      paddingLeft: row.isContext ? 12 : 0,
                      wordBreak: 'break-word',
                    }}
                  >
                    {row.text}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** Map a log line to a thick-client-style category badge text. Mirrors the
 *  PyQt5 log_viewer_window chip vocabulary: ORDER / BUY / SELL / BUY_FILL
 *  / SELL_FILL / POSITION / PERFORMANCE / SYSTEM / ERROR / WARNING. The
 *  match order follows EVENT_DEFS (which mirrors PyQt5 EVENT_PATTERNS), so
 *  category labels are deterministic across renders. */
function pickCategoryBadge(text: string): string {
  const t = text.toUpperCase();
  if (/ORDER.*#\d+/.test(t)) return 'ORDER';
  if (/BUY\s*FILL|BUY FILL/.test(t)) return 'BUY_FILL';
  if (/SELL\s*FILL|SELL FILL/.test(t)) return 'SELL_FILL';
  if (/POSITION\s+(OPEN|CLOSE|UPDATE)/.test(t)) return 'POSITION';
  if (/PERFORMANCE/.test(t)) return 'PERFORMANCE';
  if (/^ENTRY\s*#\d+:\s*LONG/.test(t)) return 'BUY';
  if (/^ENTRY\s*#\d+:\s*SHORT/.test(t)) return 'SELL';
  if (/^EXIT\s*#\d+:\s*WIN/.test(t)) return 'BUY_FILL';
  if (/^EXIT\s*#\d+:\s*LOSS/.test(t)) return 'SELL_FILL';
  if (/TRADE\s+OPENED|TRADE OPENED/.test(t)) return 'BUY';
  if (/TRADE\s+CLOSED|TRADE CLOSED/.test(t)) return 'POSITION';
  if (/STARTING|STARTED|BACKTEST.*START/.test(t)) return 'SYSTEM';
  if (/LOADING|LOADED|PROCESSING|RUNNING/.test(t)) return 'SYSTEM';
  if (/COMPLETED|FINISHED|SUCCESS/.test(t)) return 'SYSTEM';
  if (/STOPPED|STOPPING|SHUTDOWN/.test(t)) return 'SYSTEM';
  if (/ERROR|EXCEPTION|FAILED/.test(t)) return 'ERROR';
  if (/WARN(ING)?/.test(t)) return 'WARNING';
  if (/CRITICAL|FATAL/.test(t)) return 'CRITICAL';
  if (/ALERT/.test(t)) return 'ALERT';
  return 'INFO';
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
