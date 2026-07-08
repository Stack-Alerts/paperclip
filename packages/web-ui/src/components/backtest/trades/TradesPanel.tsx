'use client';

import { useMemo, useState, Fragment } from 'react';
import { Trade } from '@/lib/strategy-builder/types';
import { useFontSizes } from '@/components/backtest/backtestFontScale';
// BTCAAAAA-39028: hover-expand the collapsed totals row's NOTES preview via the
// institutional-grade tooltip BTC-39021 introduced. Same component MetricsPanel
// and LiquidationRiskMeter already consume; import path matches the convention.
import { RichTooltip, type TooltipContent, type TooltipSection } from '@/components/strategy-builder/RichTooltip';
// BTCAAAAA-39020: shared group-by-base-id helpers. BTCAAAAA-39025: the
// group P&L % math now uses entry notional (entryPrice × sum of leg qty) and
// divides the USD P&L sum by it — see tradeGrouping.ts for the full rationale.
import { groupTradesById, TradeGroup } from './tradeGrouping';

export interface TradesPanelProps {
  trades?: Trade[];
}

// BTCAAAAA-34943: data-accent colors stay on exact thick-client hex (per board
// "use exact thick-client hex/HSL values"); chrome (panel surfaces, borders,
// titles, row dim) moves to dialog CSS variables to match the rest of the UI.
const ACCENT = {
  success: '#10B981',  // styles.py COLORS['success']
  warning: '#FFA500',  // styles.py COLORS['warning']
  error:   '#C35252',  // styles.py COLORS['error']
} as const;

// Win Rate bands match the thick-client strategy profile copy in
// backtest_config_panel.py: aggressive 40-50%, balanced 50-60%, conservative
// 60-70%. ≥60% = high (success), 40-<60% = mid (warning), <40% = low (error).
function winRateColor(pct: number): string {
  if (pct >= 60) return ACCENT.success;
  if (pct >= 40) return ACCENT.warning;
  return ACCENT.error;
}

type ColumnKey =
  | 'id' | 'time' | 'symbol' | 'side' | 'size' | 'entry' | 'exit'
  | 'duration' | 'pnl' | 'pnlPct' | 'status' | 'partial' | 'notes';

interface Column { key: ColumnKey; label: string; width: number; sortable: boolean; tooltip: string; }

// Matches PyQt5 column order/widths from trades_panel.py:230,252.
// Widths trimmed (BTCAAAAA-35662) so total ~1185px fits 1280px+ screens.
// "Date/Time" widened (BTCAAAAA-36001) to fit MM/DD HH:MM:SS + padding.
// "Trade #" header widened (BTCAAAAA-39020) to fit the longer label.
// BTCAAAAA-39020: Trade # cells render a clickable chevron so users can
// collapse a trade group from any partial row OR the total summary row.
const COLUMNS: Column[] = [
  { key: 'id',       label: 'Trade #',   width: 75,  sortable: true,  tooltip: 'Trade sequence number. Partial exits share a base ID (e.g. 5.1, 5.2 = sub-exits of trade 5). Click a Trade # to collapse or expand that group.' },
  { key: 'time',     label: 'Date/Time', width: 115, sortable: true,  tooltip: 'Entry timestamp (bar open time). Hover a cell for the full ISO-8601 timestamp.' },
  { key: 'symbol',   label: 'Symbol',    width: 100, sortable: false, tooltip: 'Traded instrument. Defaults to BTC.P/USDT (perpetual futures) when not set by the engine.' },
  { key: 'side',     label: 'Side',      width: 65,  sortable: true,  tooltip: 'Trade direction: LONG = buy-to-open, SHORT = sell-to-open. Green = long, red = short.' },
  { key: 'size',     label: 'Size',      width: 75,  sortable: true,  tooltip: 'Position size in base currency (BTC). Calculated from risk % × account equity ÷ SL distance. Shows — when the engine did not report a size for this configuration.' },
  { key: 'entry',    label: 'Entry',     width: 95,  sortable: true,  tooltip: 'Fill price at trade entry including slippage, in USD.' },
  { key: 'exit',     label: 'Exit',      width: 95,  sortable: true,  tooltip: 'Fill price at trade exit (TP / SL / max-bars). Shows — for open positions.' },
  { key: 'duration', label: 'Duration',  width: 80,  sortable: false, tooltip: 'Hold time expressed in 15-minute bars, shown as h/m or d/h.' },
  { key: 'pnl',      label: 'P&L',       width: 95,  sortable: true,  tooltip: 'Realized profit or loss in USD after commission. Green = profit, red = loss.' },
  { key: 'pnlPct',   label: 'P&L %',     width: 80,  sortable: true,  tooltip: 'P&L as a percentage of entry notional (entry price × size), commissions included.' },
  { key: 'status',   label: 'Status',    width: 75,  sortable: true,  tooltip: 'CLOSED = fully exited, OPEN = active at backtest end, PARTIAL = partially closed.' },
  { key: 'partial',  label: 'Partial %', width: 115, sortable: false, tooltip: 'Exit breakdown for multi-target strategies showing each exit type and its realized P&L.' },
  { key: 'notes',    label: 'Notes',     width: 170, sortable: false, tooltip: 'Exit reason and entry signal summary. Hover the cell for the full note.' },
];

function formatDuration(bars: number): string {
  if (!bars || bars <= 0) return '—';
  // 15-minute timeframe matches thick-client trades_panel.py:_format_duration().
  const totalMinutes = bars * 15;
  if (totalMinutes < 60) return `${totalMinutes}m`;
  if (totalMinutes < 1440) {
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }
  const d = Math.floor(totalMinutes / 1440);
  const h = Math.floor((totalMinutes % 1440) / 60);
  return h > 0 ? `${d}d ${h}h` : `${d}d`;
}

function formatMoney(v: number): string {
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // BTCAAAAA-36001: include the calendar date so users can see when the trade
  // occurred, not just the time. Full ISO is exposed via the cell's title attr.
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function normalizeStatus(raw?: string): 'OPEN' | 'PARTIAL' | 'CLOSED' {
  if (!raw) return 'CLOSED';
  const u = raw.toUpperCase();
  return u === 'OPEN' ? 'OPEN' : u === 'PARTIAL' ? 'PARTIAL' : 'CLOSED';
}

function normalizeSide(raw?: string): 'LONG' | 'SHORT' | '—' {
  if (!raw) return '—';
  const u = raw.toUpperCase();
  return u === 'LONG' || u === 'SHORT' ? u : '—';
}

/**
 * BTCAAAAA-39027: render the Partial % cell for a single trade leg.
 *
 * Resolution order:
 *  1. `partialBreakdown` (pre-formatted multi-exit string from the parent row)
 *     wins over everything; it already includes every leg's dollar amount.
 *  2. If the leg has `exitType`, format `Max Bars (33%): $X` / `SL (50%): $X` /
 *     `TP1 (33%): $X` — same shape the thick client emits.
 *  3. If the leg has NO `exitType` but DOES carry `exitPercentage`, render
 *     `Partial (33%): $X`. The engine sometimes emits a partial-exit leg whose
 *     exit-type label didn't survive serialization (e.g. an SL partial lost
 *     its exit_type). Before this fix the cell bailed to '—' and the user
 *     couldn't see how much of the position had been closed.
 *  4. Bare '—' is reserved for the truly-empty case: neither `exitType` nor
 *     `exitPercentage` are populated. Do not widen it into a catch-all — the
 *     Partial % column should reflect what the engine actually computed.
 *
 * Exported so the BTC-39027 fallback chain can be unit-tested directly.
 */
export function partialDisplay(t: Trade): string {
  if (t.partialBreakdown) return t.partialBreakdown;
  // exitPercentage is decimal 0–1 from the engine; × 100 for human display.
  const exitPct = t.exitPercentage != null && t.exitPercentage > 0 ? t.exitPercentage : null;
  const pctStr = exitPct != null ? ` (${(exitPct * 100).toFixed(0)}%)` : '';
  if (!t.exitType) {
    return exitPct != null ? `Partial${pctStr}: ${formatMoney(t.pnl)}` : '—';
  }
  const u = t.exitType.toUpperCase();
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Bars${pctStr}: ${formatMoney(t.pnl)}`;
  if (u === 'SL' || u === 'STOP_LOSS') return `SL${pctStr}: ${formatMoney(t.pnl)}`;
  if (/^TP[0-9]+$/.test(u)) return `${u}${pctStr}: ${formatMoney(t.pnl)}`;
  // Unknown exit-type label (engine emitted a new code we don't recognize) —
  // with a percentage we still have useful info to show; without one, bail.
  return exitPct != null ? `Partial${pctStr}: ${formatMoney(t.pnl)}` : '—';
}

// Short exit-type codes the backend sends via exit_condition_name — these need
// expansion into human-readable notes rather than being returned verbatim.
const EXIT_TYPE_CODES = new Set(['TP1','TP2','TP3','TP4','TP5','SL','STOP_LOSS','MAX_BARS','TIME_LIMIT']);

// BTCAAAAA-39024: cap the scroll area so the sticky thead has a bounded
// scroll context. Without an explicit maxHeight the parent (SectionShell)
// grows to fit the table and the scroll div's `overflow:auto` produces no
// actual vertical scroll, making the thead's `position:sticky` a no-op for
// page scroll. ~600px fits ~12 rows + sticky h3 + sticky thead + totals —
// tall enough to be useful, short enough to keep column headers visible at
// common zoom levels on 1080p screens.
const SECTION_MAX_HEIGHT = 'min(70vh, 600px)';

// BTCAAAAA-39020 + BTCAAAAA-39024: thead sticks just below the sticky
// section title (h3). Matches SectionShell h3 height (10px+10px padding +
// ~18px line-height + 1px border). Both the h3 and thead share the
// SectionShell scroll div, so they stack correctly during vertical scroll.
const SECTION_HEADER_HEIGHT = 38;

function notesDisplay(t: Trade): string {
  const rawNotes = (t.notes ?? '').trim();
  const isAbbrev = rawNotes === '' || EXIT_TYPE_CODES.has(rawNotes.toUpperCase());

  let exitNote: string;
  if (!isAbbrev) {
    exitNote = rawNotes;
  } else {
    const u = ((t.exitType ?? rawNotes) as string).toUpperCase().trim();
    if (/^TP[0-9]+$/.test(u)) exitNote = `${u} Hit`;
    else if (u === 'SL' || u === 'STOP_LOSS') exitNote = 'Stop Loss Hit';
    else if (u === 'MAX_BARS' || u === 'TIME_LIMIT') exitNote = `Max Hold Time (${t.bars ?? 0} bars)`;
    else if (u) exitNote = u;
    else exitNote = '—';
  }

  // Append entry signals (e.g. "SIGNAL(BULLISH_BREAK)") when present — mirrors
  // thick-client "STRATEGY: X" / "SIGNAL(X)" note format from exit_hierarchy_evaluator.
  const sigs = t.entrySignals;
  if (sigs && sigs.length > 0) {
    const sigStr = sigs.map(s => `SIGNAL(${s})`).join(', ');
    return exitNote !== '—' ? `${exitNote} | ${sigStr}` : sigStr;
  }
  return exitNote;
}

// BTCAAAAA-39020: institutional-grade hover tooltip for the Notes column.
// Reopens the umbrella ticket: per-leg notes (TradeRow) and group-level notes
// (TotalRow) must share the SAME structure so users see the same four sections
// no matter which row they hover — `Exit` (what closed the leg), `Entry Signals`
// (what opened it), `Position` (size, prices, duration), and `Result` (P&L USD
// and %). The flat `title=` attr that TradeRow used previously is gone.
//
// `scope: 'leg'` (default) renders one exit-line + the signals that opened the
// leg + position size for that leg. `scope: 'group'` renders the aggregate
// exit-info + all entry signals across the group's legs + aggregate position
// totals (sum qty, weighted avg entry/exit, total bars). Both scopes produce
// identical TooltipContent shape (title + body + sections) so the markup in
// TradesPanel is uniform and RichTooltip renders them identically.
export interface NotesTooltipOpts {
  scope?: 'leg' | 'group';
  tradeId?: string | number;
  // group-aggregate inputs (only used when scope === 'group')
  totalPnl?: number;
  totalPnlPct?: number;
  totalQty?: number;
  totalBars?: number;
  weightedEntry?: number;
  weightedExit?: number;
  legCount?: number;
  // Override the rendered body line. Defaults to notesDisplay(t). The TotalRow
  // passes the joined `notesFull` string from groupNotesPreview so the group's
  // hover preview matches the per-row preview format.
  bodyOverride?: string;
}

function formatUsd(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  const sign = n < 0 ? '-' : '';
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

function formatPct(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function formatPrice(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return `$${n.toFixed(2)}`;
}

function formatQty(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return n.toFixed(4);
}

export function notesTooltipContent(t: Trade, opts: NotesTooltipOpts = {}): TooltipContent {
  const scope = opts.scope ?? 'leg';
  const idLabel = opts.tradeId !== undefined ? `Trade ${opts.tradeId}` : `Trade ${t.id}`;
  const title = `${idLabel} — Notes`;
  const body = opts.bodyOverride ?? notesDisplay(t);

  const sections: TooltipSection[] = [];

  // ── Exit section ─────────────────────────────────────────────────────────
  const exitItems: string[] = [];
  const rawNotes = (t.notes ?? '').trim();
  const isAbbrev = rawNotes === '' || EXIT_TYPE_CODES.has(rawNotes.toUpperCase());
  if (!isAbbrev && rawNotes) {
    exitItems.push(`Engine note: ${rawNotes}`);
  }
  if (t.exitType) {
    const u = t.exitType.toUpperCase().trim();
    let pretty = u;
    if (/^TP[0-9]+$/.test(u)) pretty = `${u} (Take Profit)`;
    else if (u === 'SL' || u === 'STOP_LOSS') pretty = 'SL (Stop Loss)';
    else if (u === 'MAX_BARS') pretty = 'Max Bars (time-based exit)';
    else if (u === 'TIME_LIMIT') pretty = 'Time Limit';
    exitItems.push(`Exit type: ${pretty}`);
  }
  if (typeof t.exitPercentage === 'number' && t.exitPercentage > 0) {
    exitItems.push(`Closed ${(t.exitPercentage * 100).toFixed(0)}% of position`);
  }
  if (t.status) {
    exitItems.push(`Status: ${String(t.status).toUpperCase()}`);
  }
  if (scope === 'group' && t.partialBreakdown) {
    exitItems.push(`Breakdown: ${t.partialBreakdown}`);
  }
  if (exitItems.length > 0) {
    sections.push({ header: 'Exit', items: exitItems });
  }

  // ── Entry Signals section ────────────────────────────────────────────────
  if (t.entrySignals && t.entrySignals.length > 0) {
    sections.push({
      header: 'Entry Signals',
      items: t.entrySignals.map(s => `• ${s}`),
    });
  }

  // ── Position section ─────────────────────────────────────────────────────
  if (scope === 'group') {
    const posItems: string[] = [];
    if (opts.legCount !== undefined) {
      posItems.push(`Legs: ${opts.legCount}`);
    }
    posItems.push(`Total qty: ${formatQty(opts.totalQty ?? t.quantity)}`);
    posItems.push(`Weighted entry: ${formatPrice(opts.weightedEntry ?? t.entryPrice)}`);
    posItems.push(`Weighted exit: ${formatPrice(opts.weightedExit ?? t.exitPrice)}`);
    posItems.push(`Side: ${t.side ?? '—'}`);
    if (opts.totalBars !== undefined || t.bars !== undefined) {
      posItems.push(`Bars held: ${opts.totalBars ?? t.bars}`);
    }
    sections.push({ header: 'Position', items: posItems });
  } else {
    const posItems: string[] = [
      `Side: ${t.side ?? '—'}`,
      `Qty: ${formatQty(t.quantity)}`,
      `Entry: ${formatPrice(t.entryPrice)}`,
      `Exit: ${formatPrice(t.exitPrice)}`,
      `Bars: ${t.bars ?? 0}`,
    ];
    sections.push({ header: 'Position', items: posItems });
  }

  // ── Result section ───────────────────────────────────────────────────────
  if (scope === 'group') {
    sections.push({
      header: 'Result',
      items: [
        `P&L: ${formatUsd(opts.totalPnl ?? t.pnl)}`,
        `Return: ${formatPct(opts.totalPnlPct ?? t.pnlPercentage)}`,
      ],
    });
  } else {
    sections.push({
      header: 'Result',
      items: [
        `P&L: ${formatUsd(t.pnl)}`,
        `Return: ${formatPct(t.pnlPercentage)}`,
      ],
    });
  }

  return { title, body, sections };
}

/**
 * BTCAAAAA-39028: effective status for a collapsed group's Total row.
 *
 * Precedence (matches thick-client TradesPanel collapsed totals):
 *   - any OPEN leg → "OPEN" (the group isn't fully exited yet)
 *   - else any PARTIAL leg → "PARTIAL" (some legs closed, others not)
 *   - else "CLOSED" (all legs closed)
 *
 * Engine sometimes emits lowercase status strings (e.g. "open"/"closed") — we
 * normalize via `normalizeStatus` so casing doesn't flip the verdict.
 *
 * Exported for direct unit testing — the TotalRow rendering layer only invokes
 * this with 2+ legs (single-trade groups skip TotalRow), but the helpers are
 * defensive about empty/single-trade inputs so they degrade gracefully if the
 * caller ever changes.
 */
export function groupEffectiveStatus(legs: Trade[]): 'OPEN' | 'PARTIAL' | 'CLOSED' {
  if (legs.length === 0) return 'CLOSED';
  const statuses = legs.map(t => normalizeStatus(t.status));
  if (statuses.some(s => s === 'OPEN')) return 'OPEN';
  if (statuses.some(s => s === 'PARTIAL')) return 'PARTIAL';
  return 'CLOSED';
}

/**
 * BTCAAAAA-39028: partial-exit count for the collapsed group's Total row.
 *
 * Distinct from the per-row "Partial %" column (which shows the exit breakdown
 * for a single leg). The Total row aggregates to "N partials" so users see at
 * a glance how many legs a collapsed group represents.
 *
 * Singular/plural: "1 partial" / "2 partials" — matches the thick-client copy
 * the trade notes already use. Empty group renders as "0 partials" defensively
 * even though TotalRow never invokes this with 0 legs at the render layer.
 */
export function groupPartialCount(legs: Trade[]): string {
  const n = legs.length;
  return `${n} partial${n === 1 ? '' : 's'}`;
}

/**
 * BTCAAAAA-39028: truncated notes preview + full text for the collapsed group's
 * Total row NOTES cell.
 *
 * - Closing leg = `legs[legs.length - 1]` (last in array). `groupTradesById`
 *   preserves engine order, and `sortGroupValue` already establishes this
 *   "last leg = closing leg" pattern at line 199.
 * - `full` is what `notesDisplay(closing)` renders, including any
 *   entry-signal annotation appended for "TP2 Hit | SIGNAL(BULLISH_BREAK)" etc.
 * - `preview` is the first 3-5 words of `full` plus a horizontal ellipsis
 *   (HORIZONTAL ELLIPSIS U+2026). If the note is ≤ 5 words, no ellipsis.
 * - If `full` is empty or the engine rendered '—', both preview and full are
 *   defensive — preview stays '—', full becomes '' so the tooltip omits an
 *   empty body.
 */
export function groupNotesPreview(legs: Trade[]): { preview: string; full: string } {
  if (legs.length === 0) return { preview: '—', full: '' };
  const closing = legs[legs.length - 1];
  const full = notesDisplay(closing);
  if (!full || full === '—') return { preview: '—', full: '' };
  const words = full.split(/\s+/);
  const slice = words.slice(0, Math.min(5, Math.max(3, words.length))).join(' ');
  const preview = words.length > 5 ? `${slice}…` : slice;
  return { preview, full };
}

/**
 * BTCAAAAA-39020 (round 2): per-group aggregate values for the Total row's
 * middle columns (Date/Time, Symbol, Side, Size, Entry, Exit, Duration).
 *
 * The original TotalRow collapsed those seven columns into a single
 * `<td colSpan={7}>` containing only the leg count text — visually that left
 * 6 of the 7 columns looking empty (the "many empty columns" complaint from
 * the user). The fix is to render real aggregate values per column instead,
 * so the totals row reads as a proper group summary in both expanded and
 * collapsed states.
 *
 * Source-of-truth rules (each independent — mix-and-match so partial data
 * degrades gracefully):
 *   - entryTime  → first leg's entryTime (parent trade open bar). All legs
 *                  of the same parent share an entry timestamp.
 *   - symbol     → first leg's symbol (all legs share). Falls back to the
 *                  BTC.P/USDT default TradeRow uses on line 817 when the
 *                  engine didn't populate one.
 *   - side       → first leg's side (LONG/SHORT/— via normalizeSide).
 *   - totalQty   → sum of leg quantities (gross capital committed). Each
 *                  leg carries the partial-exit size, so summing recovers
 *                  the parent position size.
 *   - entryPrice → first leg's entryPrice (parent fill price).
 *   - exitPrice  → closing leg's exitPrice (last leg's fill). May be 0 for
 *                  an OPEN leg; TradeRow falls back to '—' in that case.
 *   - totalBars  → sum of leg bars (total hold time across legs).
 *
 * Defensive: empty group yields zero/empty strings so the cells fall back
 * to the same '—' / '$0.00' formatting the per-row renderer would produce.
 *
 * Exported so the acceptance fixture in __tests__/groupRowSummary.test.ts
 * can pin down the math without rendering the table.
 */
export function groupRowSummary(legs: Trade[]): {
  entryTime: string;
  symbol: string;
  side: 'LONG' | 'SHORT' | '—';
  totalQty: number;
  entryPrice: number;
  exitPrice: number;
  totalBars: number;
} {
  if (legs.length === 0) {
    return {
      entryTime: '',
      symbol: 'BTC.P/USDT',
      side: '—',
      totalQty: 0,
      entryPrice: 0,
      exitPrice: 0,
      totalBars: 0,
    };
  }
  const first = legs[0];
  const closing = legs[legs.length - 1];
  const totalQty = legs.reduce((s, t) => s + (t.quantity ?? 0), 0);
  const totalBars = legs.reduce((s, t) => s + (t.bars ?? 0), 0);
  return {
    entryTime: first.entryTime ?? '',
    symbol: first.symbol ?? 'BTC.P/USDT',
    side: normalizeSide(first.side),
    totalQty,
    entryPrice: first.entryPrice ?? 0,
    exitPrice: closing.exitPrice ?? 0,
    totalBars,
  };
}

/**
 * BTCAAAAA-39026: per-leg displayId for the collapsed-view "Trade #" column.
 *
 * Multi-leg groups (2+ partial-exit legs of the same parent trade) keep the
 * `${baseId}.${ti + 1}` shape so partial exits stay distinguishable (5.1, 5.2,
 * 5.3). Single-leg groups render just the baseId (5) — previously the cell
 * always appended ".1", which made a single-leg trade look like a partial
 * exit even though it wasn't.
 *
 * Exported so the acceptance fixture in __tests__/legDisplayId.test.ts can
 * pin down the exact displayIds without rendering the table.
 */
export function legDisplayId(group: TradeGroup, ti: number): string {
  if (group.trades.length <= 1) return group.baseId;
  return `${group.baseId}.${ti + 1}`;
}

/**
 * BTCAAAAA-39057: derive a per-row SIZE when the engine omits `quantity`,
 * so the SIZE column doesn't bail to '—' for every leg the backend fails
 * to populate. Returns the rendered value plus a reason code so the cell
 * can show a per-row tooltip explaining what it knows.
 *
 * Tier 1 (reported): `quantity > 0` → use it as-is. The engine reported the
 *   actual filled quantity; this is the happy path and the reason still
 *   survives in the return so callers can log / surface a "backend reported
 *   size" audit note if they ever need it.
 *
 * Tier 2 (partialBreakdown present): the engine emits `partialBreakdown` as
 *   a pre-formatted string like "TP1: $33.00 (33%) | TP2: $66.00 (66%)".
 *   That string carries USD P&L and the percentage share but NOT per-leg
 *   size, so we cannot recover the qty from it. We surface this as
 *   `value: null` + the breakdown string in the tooltip so the operator
 *   can see the engine *did* emit data — it just didn't include size.
 *
 * Tier 3 (riskGuard derivation): if BOTH `riskUsd` and
 *   `stopDistanceAtEntry` are populated and positive, the position notional
 *   the stop would have lost is `riskUsd / stopDistanceAtEntry`. That
 *   gives a position size in the same unit as `quantity` (price-units
 *   cancel; USD / USD-per-unit = units). It is the *notional the stop
 *   would lose*, not the actual fill — close enough for a diagnostic
 *   fallback when the backend omits `quantity` entirely.
 *
 * Tier 4 (unavailable): nothing to show. Render '—' with a per-row tooltip
 *   naming exactly what is missing, so the operator has a precise phrase
 *   to grep when triaging backend gaps.
 *
 * Exported so the acceptance fixture in __tests__/sizeColumn.test.ts can
 * pin down the chain without rendering the table.
 */
export type DerivedSizeReason = 'reported' | 'partialBreakdown' | 'riskGuard' | 'unavailable';

export function derivedSize(trade: Trade): {
  value: number | null;
  reason: DerivedSizeReason;
  tooltip: string;
} {
  if (typeof trade.quantity === 'number' && trade.quantity > 0) {
    return {
      value: trade.quantity,
      reason: 'reported',
      tooltip:
        `Trade ${trade.id}: backend reported size ${trade.quantity.toFixed(4)}.`,
    };
  }

  const breakdown = trade.partialBreakdown;
  if (typeof breakdown === 'string' && breakdown.length > 0) {
    return {
      value: null,
      reason: 'partialBreakdown',
      tooltip:
        `Trade ${trade.id}: backend omitted quantity, but the partial-exit ` +
        `breakdown "${breakdown}" was emitted. The breakdown carries USD P&L ` +
        `and the exit-percentage share but not per-leg size, so SIZE cannot ` +
        `be derived from it.`,
    };
  }

  if (
    typeof trade.riskUsd === 'number' &&
    trade.riskUsd > 0 &&
    typeof trade.stopDistanceAtEntry === 'number' &&
    trade.stopDistanceAtEntry > 0
  ) {
    const derived = trade.riskUsd / trade.stopDistanceAtEntry;
    return {
      value: derived,
      reason: 'riskGuard',
      tooltip:
        `Trade ${trade.id}: backend omitted quantity. Derived size = ` +
        `riskUsd (${trade.riskUsd}) / stopDistanceAtEntry ` +
        `(${trade.stopDistanceAtEntry}) = ${derived.toFixed(4)}.`,
    };
  }

  return {
    value: null,
    reason: 'unavailable',
    tooltip:
      `Trade ${trade.id}: no size reported and not derivable from the risk ` +
      `guard (riskUsd or stopDistanceAtEntry missing).`,
  };
}

// Strip trailing .N or _N suffix is now provided by `baseTradeId` in
// ./tradeGrouping, along with `groupTradesById` and the `TradeGroup` type.
// See tradeGrouping.ts for BTCAAAAA-39025's corrected P&L % math.

function sortGroupValue(g: TradeGroup, key: ColumnKey): number | string {
  const first = g.trades[0];
  switch (key) {
    case 'id':     return Number(g.baseId) || 0;
    case 'time':   return new Date(first.entryTime).getTime() || 0;
    case 'side':   return normalizeSide(first.side);
    case 'size':   return first.quantity;
    case 'entry':  return first.entryPrice;
    case 'exit':   return first.exitPrice;
    // Sort by group totals so ordering reflects the complete trade outcome.
    case 'pnl':    return g.totalPnl;
    case 'pnlPct': return g.totalPnlPct;
    case 'status': return normalizeStatus(g.trades[g.trades.length - 1].status);
    default:       return 0;
  }
}

export function TradesPanel({ trades = [] }: TradesPanelProps) {
  const [sortKey, setSortKey] = useState<ColumnKey>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  // BTCAAAAA-39020: collapsed baseIds hide partial-exit rows. Empty set = all
  // expanded (default). Click a Trade # cell to toggle a single group, or use
  // the expand-all / collapse-all / reset-view controls in the section header.
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  // BTCAAAAA-38790: header Aa−/Aa+ control scales the small-text data here too
  // (summary strip + trade table); the TRADE HISTORY section title stays fixed.
  const fontSizes = useFontSizes();
  const smallZoom = { zoom: fontSizes.smallScale } as const;

  // Show individual partial-exit rows (no aggregation) — mirrors thick-client display.
  const summary = useMemo(() => {
    const total = trades.length;
    const wins = trades.filter(t => t.pnl > 0).length;
    const losses = trades.filter(t => t.pnl < 0).length;
    const longs = trades.filter(t => normalizeSide(t.side) === 'LONG').length;
    const shorts = trades.filter(t => normalizeSide(t.side) === 'SHORT').length;
    const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);
    const winRate = total > 0 ? (wins / total) * 100 : 0;
    return { total, wins, losses, longs, shorts, totalPnl, winRate };
  }, [trades]);

  const sortedGroups = useMemo(() => {
    const groups = groupTradesById(trades);
    if (groups.length === 0) return groups;
    groups.sort((a, b) => {
      const av = sortGroupValue(a, sortKey);
      const bv = sortGroupValue(b, sortKey);
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return groups;
  }, [trades, sortKey, sortDir]);

  const handleHeaderClick = (col: Column) => {
    if (!col.sortable) return;
    if (sortKey === col.key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(col.key);
      setSortDir('asc');
    }
  };

  // BTCAAAAA-39020: per-group collapse + bulk controls. Toggling one baseId
  // never affects the others, and reset clears sort + collapse in one call.
  const toggleCollapse = (baseId: string) => setCollapsed(prev => {
    const next = new Set(prev);
    if (next.has(baseId)) next.delete(baseId);
    else next.add(baseId);
    return next;
  });
  const expandAll = () => setCollapsed(new Set());
  const collapseAll = () => setCollapsed(new Set(sortedGroups.map(g => g.baseId)));
  const resetView = () => {
    setSortKey('id');
    setSortDir('asc');
    setCollapsed(new Set());
  };

  if (trades.length === 0) {
    return (
      <div className="flex flex-col min-w-0">
        <div style={smallZoom}>
          <PerformanceSummary summary={summary} hasTrades={false} />
        </div>
        <SectionShell title="Trade History">
          <div
            className="flex flex-col items-center justify-center py-12"
            style={{ color: 'var(--text-muted)' }}
          >
            <p className="text-sm">No trades yet.</p>
            <p className="text-xs mt-1">Run a backtest to see the trade log.</p>
          </div>
        </SectionShell>
      </div>
    );
  }

  const totalWidth = COLUMNS.reduce((s, c) => s + c.width, 0);

  return (
    <div className="flex flex-col min-w-0">
      <div style={smallZoom}>
        <PerformanceSummary summary={summary} hasTrades />
      </div>

      <SectionShell
        title="Trade History"
        actions={
          <HeaderActions
            hasGroups={sortedGroups.length > 0}
            onExpandAll={expandAll}
            onCollapseAll={collapseAll}
            onResetView={resetView}
          />
        }
      >
        <div style={{ minWidth: 0, ...smallZoom }}>
          <table
            style={{
              minWidth: totalWidth,
              width: '100%',
              borderCollapse: 'collapse',
              color: 'var(--text-muted)',
              fontVariantNumeric: 'tabular-nums',
              fontSize: 12,
            }}
          >
            <colgroup>
              {COLUMNS.map(c => (<col key={c.key} style={{ width: c.width }} />))}
            </colgroup>
            {/* BTCAAAAA-39024: thead sticks just below the sticky h3 inside
                the SectionShell scroll div. The h3 + thead now share a
                single scroll context (SectionShell's `overflow:auto` div),
                so they stack correctly during vertical scroll. Previous
                version had h3 sticky to the page and thead sticky to a
                wrapper that never actually scrolled, so the thead pinned
                never engaged. */}
            <thead style={{ position: 'sticky', top: SECTION_HEADER_HEIGHT, zIndex: 1 }}>
              <tr>
                {COLUMNS.map(col => {
                  const isSorted = col.sortable && sortKey === col.key;
                  return (
                    <th
                      key={col.key}
                      onClick={() => handleHeaderClick(col)}
                      title={col.tooltip}
                      onMouseEnter={e => {
                        if (col.sortable) {
                          (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
                        }
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.background = 'var(--bg-deep)';
                      }}
                      style={{
                        background: 'var(--bg-deep)',
                        color: 'var(--text-muted)',
                        padding: '10px 12px',
                        borderBottom: '1px solid var(--border)',
                        fontWeight: 600,
                        textAlign: 'center',
                        cursor: col.sortable ? 'pointer' : 'default',
                        userSelect: 'none',
                        whiteSpace: 'nowrap',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        fontSize: 11,
                      }}
                    >
                      {col.label}
                      {isSorted && (
                        <span style={{ marginLeft: 6, color: 'var(--text-secondary)' }}>
                          {sortDir === 'asc' ? '▲' : '▼'}
                        </span>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedGroups.map((group, gi) => {
                const rowBg = gi % 2 === 0 ? 'transparent' : 'rgb(81 126 227 / 4%)';
                const isCollapsed = collapsed.has(group.baseId);
                const visibleTrades = isCollapsed ? [] : group.trades;
                return (
                  <Fragment key={group.baseId}>
                    {visibleTrades.map((trade, ti) => (
                      <TradeRow
                        key={`${group.baseId}-${ti}`}
                        trade={trade}
                        rowBg={rowBg}
                        displayId={legDisplayId(group, ti)}
                        isCollapsed={isCollapsed}
                        onToggleCollapse={() => toggleCollapse(group.baseId)}
                      />
                    ))}
                    {group.trades.length > 1 && (
                      <TotalRow
                        group={group}
                        rowBg={rowBg}
                        isCollapsed={isCollapsed}
                        onToggleCollapse={() => toggleCollapse(group.baseId)}
                      />
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        <div
          style={{
            padding: '10px 14px',
            borderTop: '1px solid var(--border)',
            color: 'var(--text-muted)',
            fontSize: 12,
            ...smallZoom,
          }}
        >
          Showing: <b style={{ color: 'var(--text-secondary)' }}>All Trades ({trades.length})</b>
        </div>
      </SectionShell>
    </div>
  );
}

// Frameless section container matching the dialog's SectionCard pattern:
// subtle hairline border, transparent tinted background, muted uppercase
// title with a hairline divider underneath. BTCAAAAA-39024: h3 now lives
// INSIDE the inner scroll div (not as a sibling of it) so it shares a
// scroll context with the sticky thead — the two stickies can then stack
// correctly (h3 pins to top:0, thead pins to top:SECTION_HEADER_HEIGHT)
// during vertical scroll. Previously the h3 was page-level sticky while
// the thead was wrapper-level sticky, so they were in different scroll
// contexts and the thead never actually pinned.
function SectionShell({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-[4px]"
      style={{
        border: '1px solid var(--border)',
        background: 'rgb(28 61 76 / 2%)',
        // flex column + minHeight:0 lets the inner scroll div shrink to
        // SECTION_MAX_HEIGHT instead of stretching to fit content.
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div
        style={{
          // This div is the scroll context for BOTH the h3 (sticky top:0)
          // and the table thead (sticky top:SECTION_HEADER_HEIGHT). Setting
          // overflow:auto on both axes keeps horizontal scroll for narrow
          // viewports while capping vertical scroll at SECTION_MAX_HEIGHT.
          overflow: 'auto',
          maxHeight: SECTION_MAX_HEIGHT,
          minHeight: 0,
        }}
      >
        <h3
          className="text-xs font-semibold uppercase tracking-wider"
          style={{
            color: 'var(--text-secondary)',
            padding: '10px 14px',
            borderBottom: '1px solid var(--border)',
            margin: 0,
            position: 'sticky',
            top: 0,
            // zIndex above thead so the title overlays the column-header
            // row when both are pinned at the top of the scroll container.
            zIndex: 3,
            background: 'var(--bg-deep)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            // Pin the h3 height so the thead's sticky offset is deterministic.
            flexShrink: 0,
          }}
        >
          <span>{title}</span>
          {actions && <span style={{ display: 'inline-flex', gap: 6 }}>{actions}</span>}
        </h3>
        {children}
      </div>
    </section>
  );
}

// BTCAAAAA-39020: bulk-trade-history controls anchored to the right of the
// sticky section header. Disabled state is honored so the empty-state branch
// (no groups to expand/collapse) can't get a confusing click.
function HeaderActions({
  hasGroups,
  onExpandAll,
  onCollapseAll,
  onResetView,
}: {
  hasGroups: boolean;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onResetView: () => void;
}) {
  const disabled = !hasGroups;
  const btn = (label: string, onClick: () => void, title: string) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        background: 'transparent',
        color: disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 3,
        padding: '3px 8px',
        fontSize: 11,
        textTransform: 'lowercase',
        letterSpacing: '0.02em',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {label}
    </button>
  );
  return (
    <>
      {btn('expand all', onExpandAll, 'Expand every collapsed trade group')}
      {btn('collapse all', onCollapseAll, 'Collapse every trade group to its totals')}
      {btn('Reset view', onResetView, 'Sort by Trade # ascending and expand all groups')}
    </>
  );
}

function PerformanceSummary({
  summary,
  hasTrades,
}: {
  summary: { total: number; wins: number; losses: number; longs: number; shorts: number; totalPnl: number; winRate: number };
  hasTrades: boolean;
}) {
  // Total P&L: thick-client _update_metrics rule (success/error/muted by sign).
  const totalPnlColor =
    !hasTrades           ? 'var(--text-muted)'
    : summary.totalPnl > 0 ? ACCENT.success
    : summary.totalPnl < 0 ? ACCENT.error
    :                       'var(--text-muted)';

  // Win Rate / Long / Short coloring matches the issue's "thick-client pattern":
  // win rate banded, long-green / short-red consistent with trade-row Side cell.
  const winRateColored = hasTrades ? winRateColor(summary.winRate) : 'var(--text-muted)';
  const longColor   = hasTrades && summary.longs   > 0 ? ACCENT.success : 'var(--text-muted)';
  const shortColor  = hasTrades && summary.shorts  > 0 ? ACCENT.error   : 'var(--text-muted)';

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 30,
        padding: '14px 14px',
        borderBottom: '1px solid var(--border)',
        color: 'var(--text-muted)',
        fontSize: 13,
      }}
    >
      <SummaryItem label="Total P&L" value={formatMoney(summary.totalPnl)} valueColor={totalPnlColor} tooltip="Sum of all realized P&L across the backtest period, after commissions." />
      <SummaryItem label="Win Rate" value={`${summary.winRate.toFixed(2)}%`} valueColor={winRateColored} tooltip="Percentage of trades that closed with positive P&L. Bands: ≥60% high (green), 40–60% mid (orange), <40% low (red)." />
      <SummaryItem label="Long Trades" value={String(summary.longs)} valueColor={longColor} tooltip="Number of buy-side (long) positions opened during the backtest." />
      <SummaryItem label="Short Trades" value={String(summary.shorts)} valueColor={shortColor} tooltip="Number of sell-side (short) positions opened during the backtest." />
      <SummaryItem label="Winning Trades" value={String(summary.wins)} valueColor={hasTrades && summary.wins > 0 ? ACCENT.success : undefined} tooltip="Total number of trades that closed with a net positive P&L." />
      <SummaryItem label="Losing Trades" value={String(summary.losses)} valueColor={hasTrades && summary.losses > 0 ? ACCENT.error : undefined} tooltip="Total number of trades that closed at breakeven or negative P&L." />
    </div>
  );
}

function SummaryItem({ label, value, valueColor, tooltip }: { label: string; value: string; valueColor?: string; tooltip?: string }) {
  return (
    <span title={tooltip}>
      {label}:{' '}
      <b style={{ color: valueColor ?? 'var(--text-secondary)' }}>{value}</b>
    </span>
  );
}

function TotalRow({
  group,
  rowBg,
  isCollapsed,
  onToggleCollapse,
}: {
  group: TradeGroup;
  rowBg: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? 'rgb(81 126 227 / 7%)' : rowBg;
  const pnlColor = group.totalPnl > 0 ? ACCENT.success : group.totalPnl < 0 ? ACCENT.error : 'var(--text-muted)';
  const pctColor = group.totalPnlPct > 0 ? ACCENT.success : group.totalPnlPct < 0 ? ACCENT.error : 'var(--text-muted)';

  // BTCAAAAA-39028: STATUS / PARTIAL % / NOTES used to render literal '—' here
  // regardless of the group's actual data. Compute real aggregates via the
  // exported helpers, then render with status color matching TradeRow (line
  // 667: OPEN=success, PARTIAL=warning, CLOSED=muted).
  const status = groupEffectiveStatus(group.trades);
  const statusColor = status === 'OPEN' ? ACCENT.success : status === 'PARTIAL' ? ACCENT.warning : 'var(--text-muted)';
  const partial = groupPartialCount(group.trades);
  const { preview: notesPreview, full: notesFull } = groupNotesPreview(group.trades);

  // BTCAAAAA-39020: per-row aggregates (entry time, symbol, side, total size,
  // entry price, closing-leg exit price, total duration) so the previously
  // empty 7 columns render real values when a multi-leg group is collapsed.
  const summary = groupRowSummary(group.trades);
  const summarySideColor =
    summary.side === 'LONG' ? ACCENT.success
    : summary.side === 'SHORT' ? ACCENT.error
    : 'var(--text-muted)';

  const cellStyle: React.CSSProperties = {
    padding: '6px 8px',
    borderBottom: '2px solid var(--border)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
    fontSize: 11,
  };

  // BTCAAAAA-39020: Trade # cell shows the chevron + baseId, mirrors the
  // per-row trigger so users can expand a collapsed group from the totals row.
  const idCellStyle: React.CSSProperties = {
    ...cellStyle,
    color: 'var(--text-secondary)',
    fontWeight: 700,
    fontStyle: 'italic',
    cursor: 'pointer',
    userSelect: 'none',
  };

  // BTCAAAAA-39028: NOTES preview gets the BTC-39021 institutional tooltip so
  // users can hover to see the full note (including any appended entry-signal
  // annotation).
  //
  // BTCAAAAA-39020 reopen: always render the sectioned RichTooltip (Exit /
  // Entry Signals / Position / Result) so the TotalRow hover shape matches the
  // TradeRow hover shape exactly — fixes the "tooltip structures differ"
  // complaint. The closing leg carries the partialBreakdown surfaced in Exit.
  const notesCellStyle: React.CSSProperties = {
    ...cellStyle,
    color: 'var(--text-secondary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: 170,
  };
  const closingLeg = group.trades[group.trades.length - 1] ?? group.trades[0];
  const groupNotesTooltip: TooltipContent | null = closingLeg
    ? notesTooltipContent(closingLeg, {
        scope: 'group',
        tradeId: group.baseId,
        bodyOverride: notesPreview !== '—' ? notesFull : undefined,
        totalPnl: group.totalPnl,
        totalPnlPct: group.totalPnlPct,
        totalQty: summary.totalQty,
        totalBars: summary.totalBars,
        weightedEntry: summary.entryPrice,
        weightedExit: summary.exitPrice,
        legCount: group.trades.length,
      })
    : null;
  const notesSpan = (
    <span style={{ fontStyle: notesPreview === '—' ? 'italic' : 'normal' }}>{notesPreview}</span>
  );

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: bg, borderTop: '1px solid var(--border)' }}
    >
      <td
        style={idCellStyle}
        onClick={onToggleCollapse}
        title={`Trade ${group.baseId} — click to ${isCollapsed ? 'expand' : 'collapse'} partial-exit rows`}
      >
        <span style={{ marginRight: 4 }}>{isCollapsed ? '▶' : '▼'}</span>
        #{group.baseId} Total
      </td>
      <td style={cellStyle} title={summary.entryTime}>{formatTime(summary.entryTime)}</td>
      <td style={cellStyle}>{summary.symbol}</td>
      <td style={{ ...cellStyle, color: summarySideColor, fontWeight: 600 }}>{summary.side}</td>
      <td style={cellStyle}>{summary.totalQty > 0 ? summary.totalQty.toFixed(4) : '—'}</td>
      <td style={cellStyle}>{summary.entryPrice > 0 ? formatMoney(summary.entryPrice) : '—'}</td>
      <td style={cellStyle}>{summary.exitPrice > 0 ? formatMoney(summary.exitPrice) : '—'}</td>
      <td style={cellStyle}>{summary.totalBars > 0 ? formatDuration(summary.totalBars) : '—'}</td>
      <td style={{ ...cellStyle, color: pnlColor, fontWeight: 700 }}>{formatMoney(group.totalPnl)}</td>
      <td style={{ ...cellStyle, color: pctColor, fontWeight: 700 }}>{`${group.totalPnlPct.toFixed(2)}%`}</td>
      <td style={{ ...cellStyle, color: statusColor, fontWeight: 600 }}>{status}</td>
      <td style={{ ...cellStyle, color: 'var(--text-secondary)' }}>{partial}</td>
      <td style={notesCellStyle}>
        {groupNotesTooltip ? <RichTooltip content={groupNotesTooltip}>{notesSpan}</RichTooltip> : notesSpan}
      </td>
    </tr>
  );
}

function TradeRow({
  trade,
  rowBg,
  displayId,
  isCollapsed,
  onToggleCollapse,
}: {
  trade: Trade;
  rowBg: string;
  displayId: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? 'rgb(81 126 227 / 9%)' : rowBg;
  const side = normalizeSide(trade.side);
  const status = normalizeStatus(trade.status);
  const pnlColor = trade.pnl > 0 ? ACCENT.success : trade.pnl < 0 ? ACCENT.error : 'var(--text-muted)';
  const pctColor = trade.pnlPercentage > 0 ? ACCENT.success : trade.pnlPercentage < 0 ? ACCENT.error : 'var(--text-muted)';
  const sideColor = side === 'LONG' ? ACCENT.success : side === 'SHORT' ? ACCENT.error : 'var(--text-muted)';
  const statusColor = status === 'OPEN' ? ACCENT.success : status === 'PARTIAL' ? ACCENT.warning : 'var(--text-muted)';
  const partial = partialDisplay(trade);

  // BTCAAAAA-39057: per-row SIZE column now goes through derivedSize() so
  // trades that lack `quantity` no longer bail to '—' silently. The helper
  // picks the best available source (reported → partialBreakdown-acknowledged
  // → riskGuard-derived → unavailable) and we only attach the RichTooltip on
  // the non-reported paths — happy-path trades get no tooltip noise.
  const size = derivedSize(trade);
  const sizeDisplay = size.value !== null ? size.value.toFixed(4) : '—';
  const sizeTooltip: TooltipContent | null =
    size.reason === 'reported'
      ? null
      : {
          title: `Trade ${trade.id} — SIZE (${size.reason})`,
          body: size.tooltip,
        };

  const cellStyle: React.CSSProperties = {
    padding: '10px 8px',
    borderBottom: '1px solid var(--border)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  };

  // BTCAAAAA-39020: Trade # is rendered as a clickable chevron + sequential id
  // (e.g. "▼ 5.1"). Backend sends only the base ID for partials; the parent
  // passes the renumbered displayId so each row gets its own sub-index.
  const idCellStyle: React.CSSProperties = {
    ...cellStyle,
    cursor: 'pointer',
    userSelect: 'none',
    fontVariantNumeric: 'tabular-nums',
  };

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: bg }}
    >
      <td
        style={idCellStyle}
        onClick={onToggleCollapse}
        title={`Trade ${displayId} — click to ${isCollapsed ? 'expand' : 'collapse'} this trade group`}
      >
        <span style={{ marginRight: 4 }}>{isCollapsed ? '▶' : '▼'}</span>
        {displayId}
      </td>
      <td style={cellStyle} title={trade.entryTime}>{formatTime(trade.entryTime)}</td>
      <td style={cellStyle}>{trade.symbol ?? 'BTC.P/USDT'}</td>
      <td style={{ ...cellStyle, color: sideColor, fontWeight: 600 }}>{side}</td>
      <td style={cellStyle}>
        {sizeTooltip ? (
          <RichTooltip content={sizeTooltip}>
            <span>{sizeDisplay}</span>
          </RichTooltip>
        ) : (
          sizeDisplay
        )}
      </td>
      <td style={cellStyle}>{formatMoney(trade.entryPrice)}</td>
      <td style={cellStyle}>{trade.exitPrice ? formatMoney(trade.exitPrice) : '—'}</td>
      <td style={cellStyle}>{formatDuration(trade.bars)}</td>
      <td style={{ ...cellStyle, color: pnlColor, fontWeight: 600 }}>{formatMoney(trade.pnl)}</td>
      <td style={{ ...cellStyle, color: pctColor, fontWeight: 600 }}>
        {`${trade.pnlPercentage.toFixed(2)}%`}
      </td>
      <td style={{ ...cellStyle, color: statusColor, fontWeight: 600 }}>{status}</td>
      <td style={{ ...cellStyle, color: pnlColor }}>{partial}</td>
      <td style={{ ...cellStyle, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 170 }}>
        <RichTooltip content={notesTooltipContent(trade, { tradeId: displayId })}>
          <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'help' }}>
            {notesDisplay(trade)}
          </span>
        </RichTooltip>
      </td>
    </tr>
  );
}
