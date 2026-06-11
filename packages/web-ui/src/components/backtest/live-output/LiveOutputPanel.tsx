'use client';

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { BacktestStatusMessage, BacktestResult, Trade } from '@/lib/strategy-builder/types';
import { BacktestCountersRow } from './BacktestCountersRow';
import {
  EVENT_DEFS,
  EVENT_GROUPS,
  LEVEL_DEFS_TC,
  CATEGORY_DEFS_TC,
  type LevelTag,
  type CategoryTag,
  detectLevel,
  detectCategory,
  isContextLine,
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

const FILTERS_STORAGE_KEY = 'backtest.liveOutput.filters.v3';
const FONT_SCALE_KEY = 'backtest.liveOutput.fontScale';
const LOG_FONT_SIZES = ['10px', '11px', '13px'] as const;
const LOG_FONT_LABELS = ['Compact', 'Normal', 'Large'] as const;
type LogFontScaleIdx = 0 | 1 | 2;

function loadStoredFilters(): { levels: Set<LevelTag>; categories: Set<CategoryTag> } | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return null;
    const obj = JSON.parse(raw) as { levels?: string[]; categories?: string[] };
    if (!Array.isArray(obj.levels) || !Array.isArray(obj.categories)) return null;
    const validLevels = new Set(LEVEL_DEFS_TC.map(d => d.tag));
    const validCats = new Set(CATEGORY_DEFS_TC.map(d => d.tag));
    const levels = new Set<LevelTag>(obj.levels.filter((x): x is LevelTag => validLevels.has(x as LevelTag)));
    const categories = new Set<CategoryTag>(obj.categories.filter((x): x is CategoryTag => validCats.has(x as CategoryTag)));
    if (levels.size === 0 && categories.size === 0) return null;
    return { levels, categories };
  } catch {
    return null;
  }
}

function defaultLevels(): Set<LevelTag> {
  return new Set(LEVEL_DEFS_TC.map(d => d.tag));
}

function defaultCategories(): Set<CategoryTag> {
  return new Set<CategoryTag>(['GLOBAL']);
}

/** BTCAAAAA-33591 cycle-33: synthesize dense per-trade log lines from a
 *  completed result when the backend messages list is empty. */
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
    const fallbackBase = Date.now() - (trades.length - i) * 60_000;
    const entryTs = t.entryTime || new Date(fallbackBase).toISOString();
    const exitTs = t.exitTime || new Date(fallbackBase + 30_000).toISOString();

    out.push({ message: `ORDER #${idx}: ${side} ${qty} ${symbol} ${isLong ? 'BUY' : 'SELL'} @ ${entry.toFixed(2)}`, level: 'INFO', timestamp: entryTs });
    out.push({ message: isLong
      ? `BUY FILL #${idx}: ${qty} ${symbol} @ ${entry.toFixed(2)}`
      : `SELL FILL #${idx}: ${qty} ${symbol} @ ${entry.toFixed(2)}`,
      level: 'INFO', timestamp: entryTs });
    out.push({ message: `POSITION OPEN #${idx}: ${side} ${qty} ${symbol} @ ${entry.toFixed(2)} | bars=${bars}`, level: 'INFO', timestamp: entryTs });
    out.push({ message: `PERFORMANCE #${idx}: ${outcome} | ${exitReason} @ ${exit.toFixed(2)} | Total PnL: $${pnl.toFixed(2)} (Realized ${pnlPct.toFixed(2)}%) | bars=${bars}`, level: 'INFO', timestamp: exitTs });
  }
  return out;
}

export function LiveOutputPanel({ logs = [], isRunning = false, result = null, candles, trades }: LiveOutputPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [enabledLevels, setEnabledLevels] = useState<Set<LevelTag>>(defaultLevels);
  const [enabledCategories, setEnabledCategories] = useState<Set<CategoryTag>>(defaultCategories);
  const [clearedBefore, setClearedBefore] = useState(0);
  const [fontScaleIdx, setFontScaleIdx] = useState<LogFontScaleIdx>(() => {
    if (typeof window === 'undefined') return 1;
    const n = parseInt(window.localStorage.getItem(FONT_SCALE_KEY) ?? '1', 10);
    return (n === 0 || n === 1 || n === 2) ? n as LogFontScaleIdx : 1;
  });

  useEffect(() => {
    const stored = loadStoredFilters();
    if (stored) {
      if (stored.levels.size > 0) setEnabledLevels(stored.levels);
      if (stored.categories.size > 0) setEnabledCategories(stored.categories);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
        levels: Array.from(enabledLevels),
        categories: Array.from(enabledCategories),
      }));
    } catch { /* quota/private-mode */ }
  }, [enabledLevels, enabledCategories]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try { window.localStorage.setItem(FONT_SCALE_KEY, String(fontScaleIdx)); } catch { /* quota/private-mode */ }
  }, [fontScaleIdx]);

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isPaused, result]);

  const toggleLevel = useCallback((tag: LevelTag) => {
    setEnabledLevels(prev => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag); else next.add(tag);
      return next;
    });
  }, []);

  const toggleCategory = useCallback((tag: CategoryTag) => {
    setEnabledCategories(prev => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag); else next.add(tag);
      return next;
    });
  }, []);

  const allOn = enabledLevels.size === LEVEL_DEFS_TC.length && enabledCategories.has('GLOBAL');

  const toggleAll = useCallback(() => {
    if (allOn) {
      setEnabledLevels(new Set());
      setEnabledCategories(new Set());
    } else {
      setEnabledLevels(defaultLevels());
      setEnabledCategories(defaultCategories());
    }
  }, [allOn]);

  const effectiveTrades = useMemo(
    () => (trades?.length ? trades : (result?.trades ?? [])),
    [trades, result],
  );

  const effectiveResult = useMemo(() => {
    if (!result) return null;
    if (result.trades?.length || !effectiveTrades.length) return result;
    return { ...result, trades: effectiveTrades };
  }, [result, effectiveTrades]);

  const effectiveLogs = useMemo(() => {
    const tradeList = effectiveTrades;
    if (tradeList.length === 0) return logs;
    const synth = synthesizeTradeLogLines(tradeList);
    if (synth.length === 0) return logs;
    const backendTradeIdxCovered = new Set<number>();
    const re = /(?:Entry|Exit|ORDER|PERFORMANCE)\s+#(\d+):/i;
    for (const m of logs) {
      const match = re.exec(m.message ?? '');
      if (match) backendTradeIdxCovered.add(parseInt(match[1], 10));
    }
    if (backendTradeIdxCovered.size >= tradeList.length) return logs;
    const missing: BacktestStatusMessage[] = [];
    for (let i = 0; i < synth.length; i++) {
      const tradeIdx = Math.floor(i / 4) + 1;
      if (backendTradeIdxCovered.has(tradeIdx)) continue;
      missing.push(synth[i]);
    }
    if (missing.length === 0) return logs;
    return [...logs, ...missing].sort((a, b) => {
      const ta = Date.parse(a.timestamp ?? '') || 0;
      const tb = Date.parse(b.timestamp ?? '') || 0;
      return ta - tb;
    });
  }, [logs, effectiveTrades]);

  const visibleLogs = useMemo(
    () => effectiveLogs.slice(Math.min(clearedBefore, effectiveLogs.length)),
    [effectiveLogs, clearedBefore],
  );

  const categoryFilterActive = enabledCategories.size > 0 && !enabledCategories.has('GLOBAL');
  const showAll = enabledLevels.size === LEVEL_DEFS_TC.length && !categoryFilterActive;

  const { rows, displayedLines } = useMemo(() => {
    let inContext = false;
    let displayed = 0;
    const built: Array<{
      key: string; text: string; lvl: LevelTag; cat: CategoryTag; isContext: boolean; ts?: string;
    }> = [];

    for (let i = 0; i < visibleLogs.length; i++) {
      const msg = visibleLogs[i];
      // Strip leading whitespace so Python logger output (which may include
      // leading spaces/tabs from formatting) doesn't mis-trigger isContextLine
      // and doesn't render as indentation artifacts in the message column.
      const text = (msg.message ?? '').replace(/^\s+/, '');
      const isCtx = isContextLine(text);
      const lvl = detectLevel(text);
      const cat = detectCategory(text);

      let keep = false;
      if (showAll) {
        keep = true; inContext = true;
      } else {
        const levelOk = enabledLevels.has(lvl);
        const catOk = !categoryFilterActive || enabledCategories.has(cat);
        if (levelOk && catOk) {
          keep = true; inContext = true;
        } else if (inContext && (isCtx || text.trim() === '')) {
          keep = true;
        } else {
          inContext = false;
        }
      }

      if (keep) {
        displayed++;
        built.push({ key: `${i}`, text, lvl, cat, isContext: isCtx, ts: msg.timestamp });
      }
    }
    return { rows: built, displayedLines: displayed };
  }, [visibleLogs, showAll, enabledLevels, enabledCategories, categoryFilterActive]);

  // Bottom-bar stats: count from ALL effective logs (mirrors thick-client counters).
  const { decisions, winners, losses, stopLoss, tradeCount } = useMemo(() => {
    let dec = 0, win = 0, loss = 0, sl = 0;
    for (const msg of effectiveLogs) {
      const lvl = detectLevel(msg.message ?? '');
      if (lvl === 'DECISION') dec++;
      else if (lvl === 'WIN') win++;
      else if (lvl === 'LOSS') loss++;
      else if (lvl === 'STOP_LOSS') sl++;
    }
    return {
      decisions: dec, winners: win, losses: loss, stopLoss: sl,
      tradeCount: result?.totalTrades ?? result?.trades?.length ?? effectiveTrades.length,
    };
  }, [effectiveLogs, result, effectiveTrades]);

  const handleCopy = useCallback(() => {
    const text = rows.map(r => {
      const ts = r.ts ? formatTime(r.ts) : '';
      const lLabel = LEVEL_DEFS_TC.find(d => d.tag === r.lvl)?.label ?? r.lvl;
      const cLabel = CATEGORY_DEFS_TC.find(d => d.tag === r.cat)?.label ?? r.cat;
      return `${ts} [${lLabel}] [${cLabel}] ${r.text}`;
    }).join('\n');
    navigator.clipboard.writeText(text).catch(() => {});
  }, [rows]);

  const handleExport = useCallback(() => {
    const text = rows.map(r => {
      const ts = r.ts ? formatTime(r.ts) : '';
      const lLabel = LEVEL_DEFS_TC.find(d => d.tag === r.lvl)?.label ?? r.lvl;
      const cLabel = CATEGORY_DEFS_TC.find(d => d.tag === r.cat)?.label ?? r.cat;
      return `${ts} [${lLabel}] [${cLabel}] ${r.text}`;
    }).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'backtest-log.txt';
    a.click();
    URL.revokeObjectURL(url);
  }, [rows]);

  const handleClear = useCallback(() => {
    setClearedBefore(effectiveLogs.length);
  }, [effectiveLogs.length]);

  return (
    <div className="flex flex-col h-full" style={{ minHeight: 300 }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          Live Output
        </p>
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="text-xs" style={{ color: 'var(--accent-green)' }}>● RUNNING</span>
          )}
          {/* Aa−/Aa+ font scale — mirrors BacktestConfigDialog header control */}
          <div
            role="group"
            aria-label="Log font size"
            className="flex items-center rounded-[4px] overflow-hidden"
            style={{ border: '1px solid var(--border)', background: 'var(--bg-deep)' }}
          >
            <button
              onClick={() => setFontScaleIdx(i => Math.max(0, i - 1) as LogFontScaleIdx)}
              disabled={fontScaleIdx === 0}
              aria-label="Decrease font size"
              title="Decrease font size"
              className="px-2 py-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ color: 'var(--text-secondary)' }}
            >
              <span style={{ fontSize: '11px' }}>A</span><span style={{ fontSize: '13px' }}>a</span><span style={{ marginLeft: 2 }}>−</span>
            </button>
            <span
              aria-live="polite"
              className="px-2 text-[10px] font-medium uppercase tracking-wider whitespace-nowrap select-none"
              style={{ color: 'var(--text-muted)' }}
            >
              {LOG_FONT_LABELS[fontScaleIdx]}
            </span>
            <button
              onClick={() => setFontScaleIdx(i => Math.min(2, i + 1) as LogFontScaleIdx)}
              disabled={fontScaleIdx === 2}
              aria-label="Increase font size"
              title="Increase font size"
              className="px-2 py-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ color: 'var(--text-secondary)' }}
            >
              <span style={{ fontSize: '11px' }}>A</span><span style={{ fontSize: '15px' }}>a</span><span style={{ marginLeft: 2 }}>+</span>
            </button>
          </div>
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

      {/* TP/SL + candles counters row */}
      <BacktestCountersRow result={effectiveResult} candles={candles} className="mb-2" />

      {/* ── Filter bar — single inline row ──────────────────────────────────── */}
      <div className="mb-1 flex items-center flex-wrap gap-1" data-testid="live-output-filters">
        <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
          Levels:
        </span>
        {LEVEL_DEFS_TC.map(def => {
          const on = enabledLevels.has(def.tag);
          return (
            <button
              key={def.tag}
              type="button"
              aria-label={def.label}
              aria-pressed={on}
              onClick={() => toggleLevel(def.tag)}
              className="text-[11px] font-semibold px-2 py-0.5 rounded"
              style={{
                background: on ? `${def.color}22` : 'var(--bg-deep)',
                color: on ? def.color : 'var(--text-muted)',
                border: `1px solid ${on ? def.color : 'var(--border)'}`,
                cursor: 'pointer',
              }}
            >
              {def.label}
            </button>
          );
        })}

        <span style={{ color: 'var(--border)', margin: '0 4px', flexShrink: 0, userSelect: 'none' }}>|</span>

        <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
          Categories:
        </span>
        {CATEGORY_DEFS_TC.map(def => {
          const on = enabledCategories.has(def.tag);
          const isHexColor = def.color.startsWith('#');
          const globalActive = enabledCategories.has('GLOBAL');
          const dimmed = def.tag !== 'GLOBAL' && globalActive;
          return (
            <button
              key={def.tag}
              type="button"
              aria-label={def.label}
              aria-pressed={on}
              onClick={() => toggleCategory(def.tag)}
              className="text-[11px] font-semibold px-2 py-0.5 rounded"
              style={{
                background: on && !dimmed ? (isHexColor ? `${def.color}22` : 'var(--bg-hover)') : 'var(--bg-deep)',
                color: dimmed ? 'var(--text-faint)' : on ? (isHexColor ? def.color : 'var(--text-secondary)') : 'var(--text-muted)',
                border: `1px solid ${on && !dimmed && isHexColor ? def.color : 'var(--border)'}`,
                cursor: 'pointer',
                opacity: dimmed ? 0.4 : 1,
              }}
            >
              {def.label}
            </button>
          );
        })}

        <div className="flex-1" />
        <button
          type="button"
          onClick={toggleAll}
          title="Toggle all event filters"
          className="text-[11px] px-3 py-0.5 rounded"
          style={{
            background: 'var(--bg-deep)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
        >
          {allOn ? 'Unselect All' : 'Select All'}
        </button>
      </div>

      {/* ── Log output ─────────────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded font-mono"
        style={{
          background: 'var(--bg-deep)',
          border: '1px solid var(--border)',
          padding: '0.5rem 0.75rem',
          minHeight: 240,
          fontSize: LOG_FONT_SIZES[fontScaleIdx],
        }}
        data-testid="live-output-log"
      >
        {visibleLogs.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>
            {isRunning ? 'Waiting for output…' : 'No output yet. Start a backtest to see live output.'}
          </p>
        ) : rows.length === 0 ? (
          <p style={{ color: 'var(--text-faint)' }}>No lines match the active filters.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {rows.map(row => {
              const time = row.ts ? formatTime(row.ts) : '';
              const lDef = LEVEL_DEFS_TC.find(d => d.tag === row.lvl);
              const cDef = CATEGORY_DEFS_TC.find(d => d.tag === row.cat);
              const lColor = lDef?.color ?? '#9AA0A6';
              const cColor = cDef?.color ?? '#9AA0A6';
              return (
                <div
                  key={row.key}
                  className="rounded leading-[1.4]"
                  data-testid="log-row"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '12ch 12ch 13ch 1fr',
                    columnGap: '0.25rem',
                    alignItems: 'baseline',
                    paddingLeft: row.isContext ? 12 : 2,
                    paddingRight: 4,
                    paddingTop: 1,
                    paddingBottom: 1,
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.04)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = ''; }}
                >
                  <span style={{ color: 'var(--text-faint)', whiteSpace: 'nowrap', overflow: 'hidden' }}>{time}</span>
                  <span style={{ color: lColor, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden' }}>
                    [{lDef?.label ?? row.lvl}]
                  </span>
                  <span style={{ color: cColor, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden' }}>
                    [{cDef?.label ?? row.cat}]
                  </span>
                  <span style={{ color: '#9AA0A6', wordBreak: 'break-word', minWidth: 0 }}>
                    {colorizeMessage(row.text)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Bottom stats bar (mirrors thick-client _create_bottom_bar) ──────── */}
      <div
        className="mt-1 flex items-center gap-3 text-[11px] flex-wrap"
        data-testid="live-output-stats"
        style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
      >
        <span>Messages: <b style={{ color: 'var(--text-secondary)' }}>{effectiveLogs.length.toLocaleString()}</b></span>
        <span>Displayed: <b style={{ color: 'var(--text-secondary)' }}>{displayedLines.toLocaleString()}</b></span>
        <span>Decisions: <b style={{ color: '#FFD700' }}>{decisions.toLocaleString()}</b></span>
        <span>Winners: <b style={{ color: '#10B981' }}>{winners.toLocaleString()}</b></span>
        <span>Losses: <b style={{ color: '#FF8C00' }}>{losses.toLocaleString()}</b></span>
        <span>Stop Loss: <b style={{ color: '#C35252' }}>{stopLoss.toLocaleString()}</b></span>
        <span>Trades: <b style={{ color: 'var(--text-secondary)' }}>{tradeCount.toLocaleString()}</b></span>
        <div className="flex-1" />
        <button
          type="button" onClick={handleCopy}
          className="text-[11px] px-2 py-0.5 rounded"
          style={{ background: 'var(--bg-deep)', color: 'var(--text-muted)', border: '1px solid var(--border)', cursor: 'pointer' }}
          title="Copy displayed log to clipboard"
        >Copy</button>
        <button
          type="button" onClick={handleClear}
          className="text-[11px] px-2 py-0.5 rounded"
          style={{ background: 'var(--bg-deep)', color: 'var(--text-muted)', border: '1px solid var(--border)', cursor: 'pointer' }}
          title="Clear log display"
        >Clear</button>
        <button
          type="button" onClick={handleExport}
          className="text-[11px] px-2 py-0.5 rounded"
          style={{ background: 'var(--bg-deep)', color: 'var(--text-muted)', border: '1px solid var(--border)', cursor: 'pointer' }}
          title="Export log as text file"
        >Export</button>
      </div>
    </div>
  );
}

/** Highlight PnL dollar + pct pairs green (positive) or red (negative).
 *  Only "PnL: $X.XX (Y.YY%)" patterns are colored — price context stays neutral. */
function colorizeMessage(text: string): React.ReactNode {
  const re = /(PnL:\s*)(-?\$[\d,]+\.?\d*)\s*\((-?[\d,]+\.?\d*%)\)/g;
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  let m: RegExpExecArray | null;
  let idx = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > cursor) nodes.push(text.slice(cursor, m.index));
    const neg = m[2].startsWith('-') || m[3].startsWith('-');
    const color = neg ? '#C35252' : '#10B981';
    nodes.push(<span key={idx++} style={{ color }}>{m[1]}{m[2]} ({m[3]})</span>);
    cursor = m.index + m[0].length;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes.length > 1 ? <>{nodes}</> : text;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}.${d.getMilliseconds().toString().padStart(3, '0')}`;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export { EVENT_DEFS, EVENT_GROUPS };
