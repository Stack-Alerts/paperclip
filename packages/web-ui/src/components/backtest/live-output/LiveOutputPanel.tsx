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
      const text = msg.message ?? '';
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

      {/* ── Thick-client filter bar ─────────────────────────────────────────── */}
      <div className="mb-1 flex flex-col gap-1" data-testid="live-output-filters">
        {/* Level filter row: INFO | DECISION | WIN | LOSS | STOP/LOSS */}
        <div className="flex items-center flex-wrap gap-1">
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

        {/* Category filter row: Global | TRADE | RISK | SYSTEM | OPTIMIZER | SERVICE */}
        <div className="flex items-center flex-wrap gap-1">
          <span className="text-[10px] uppercase tracking-wider mr-1" style={{ color: 'var(--text-muted)' }}>
            Categories:
          </span>
          {CATEGORY_DEFS_TC.map(def => {
            const on = enabledCategories.has(def.tag);
            const isHexColor = def.color.startsWith('#');
            return (
              <button
                key={def.tag}
                type="button"
                aria-label={def.label}
                aria-pressed={on}
                onClick={() => toggleCategory(def.tag)}
                className="text-[11px] font-semibold px-2 py-0.5 rounded"
                style={{
                  background: on ? (isHexColor ? `${def.color}22` : 'var(--bg-hover)') : 'var(--bg-deep)',
                  color: on ? (isHexColor ? def.color : 'var(--text-secondary)') : 'var(--text-muted)',
                  border: `1px solid ${on && isHexColor ? def.color : 'var(--border)'}`,
                  cursor: 'pointer',
                }}
              >
                {def.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Log output ─────────────────────────────────────────────────────── */}
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
                  className="flex items-baseline gap-1.5 leading-[1.4]"
                  data-testid="log-row"
                  style={{ paddingLeft: row.isContext ? 12 : 0 }}
                >
                  <span style={{ color: 'var(--text-faint)', whiteSpace: 'nowrap', flexShrink: 0, minWidth: '12ch', display: 'inline-block' }}>{time}</span>
                  <span style={{ color: lColor, whiteSpace: 'nowrap', flexShrink: 0, fontWeight: 700, minWidth: '11ch', display: 'inline-block' }}>
                    [{lDef?.label ?? row.lvl}]
                  </span>
                  <span style={{ color: cColor, whiteSpace: 'nowrap', flexShrink: 0, fontWeight: 600, minWidth: '11ch', display: 'inline-block' }}>
                    [{cDef?.label ?? row.cat}]
                  </span>
                  <span style={{ color: '#9AA0A6', wordBreak: 'break-word' }}>
                    {row.text}
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
        <span>Decisions: <b style={{ color: '#FF8C00' }}>{decisions.toLocaleString()}</b></span>
        <span>Winners: <b style={{ color: '#10B981' }}>{winners.toLocaleString()}</b></span>
        <span>Losses: <b style={{ color: '#C35252' }}>{losses.toLocaleString()}</b></span>
        <span>Stop Loss: <b style={{ color: '#FF4040' }}>{stopLoss.toLocaleString()}</b></span>
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

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}.${d.getMilliseconds().toString().padStart(3, '0')}`;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export { EVENT_DEFS, EVENT_GROUPS };
