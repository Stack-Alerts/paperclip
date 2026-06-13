'use client';

import { useMemo, useState, Fragment } from 'react';
import { Trade } from '@/lib/strategy-builder/types';

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
const COLUMNS: Column[] = [
  { key: 'id',       label: 'ID',        width: 55,  sortable: true,  tooltip: 'Trade sequence number. Partial exits share a base ID (e.g. 5.1, 5.2 = sub-exits of trade 5).' },
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

function partialDisplay(t: Trade): string {
  if (t.partialBreakdown) return t.partialBreakdown;
  if (!t.exitType) return '—';
  const u = t.exitType.toUpperCase();
  // exitPercentage is decimal 0–1 from engine; multiply × 100 for display.
  const pct = t.exitPercentage != null && t.exitPercentage > 0
    ? ` (${(t.exitPercentage * 100).toFixed(0)}%)`
    : '';
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Bars${pct}: ${formatMoney(t.pnl)}`;
  if (u === 'SL' || u === 'STOP_LOSS') return `SL${pct}: ${formatMoney(t.pnl)}`;
  if (/^TP[0-9]+$/.test(u)) return `${u}${pct}: ${formatMoney(t.pnl)}`;
  return '—';
}

// Short exit-type codes the backend sends via exit_condition_name — these need
// expansion into human-readable notes rather than being returned verbatim.
const EXIT_TYPE_CODES = new Set(['TP1','TP2','TP3','TP4','TP5','SL','STOP_LOSS','MAX_BARS','TIME_LIMIT']);

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

// Strip trailing .N or _N suffix to get base trade ID (e.g. "5.1" → "5").
// The registry assigns dot notation ("5.1"), so the regex accepts both separators.
function baseTradeId(id: string): string {
  return String(id).replace(/[._]\d+$/, '');
}

interface TradeGroup {
  baseId: string;
  trades: Trade[];
  totalPnl: number;
  totalPnlPct: number;
}

// Group individual partial-exit records by base trade ID.
// Preserves insertion order so Trade 5 (with partials 5.1, 5.2, 5.3) stays together.
function groupTradesById(raw: Trade[]): TradeGroup[] {
  const map = new Map<string, TradeGroup>();
  const order: string[] = [];
  for (const t of raw) {
    const b = baseTradeId(String(t.id));
    if (!map.has(b)) {
      map.set(b, { baseId: b, trades: [], totalPnl: 0, totalPnlPct: 0 });
      order.push(b);
    }
    const g = map.get(b)!;
    g.trades.push(t);
    g.totalPnl += t.pnl;
    g.totalPnlPct += t.pnlPercentage;
  }
  return order.map(b => map.get(b)!);
}

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

  if (trades.length === 0) {
    return (
      <div className="flex flex-col min-w-0">
        <PerformanceSummary summary={summary} hasTrades={false} />
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
      <PerformanceSummary summary={summary} hasTrades />

      <SectionShell title="Trade History">
        <div style={{ overflowX: 'auto', minWidth: 0 }}>
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
            <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
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
                return (
                  <Fragment key={group.baseId}>
                    {group.trades.map((trade, ti) => (
                      <TradeRow key={`${trade.id}-${ti}`} trade={trade} rowBg={rowBg} />
                    ))}
                    {group.trades.length > 1 && (
                      <TotalRow group={group} rowBg={rowBg} />
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
// title with a hairline divider underneath.
function SectionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="rounded-[4px]"
      style={{
        border: '1px solid var(--border)',
        background: 'rgb(28 61 76 / 2%)',
      }}
    >
      <h3
        className="text-xs font-semibold uppercase tracking-wider"
        style={{
          color: 'var(--text-secondary)',
          padding: '10px 14px',
          borderBottom: '1px solid var(--border)',
          margin: 0,
        }}
      >
        {title}
      </h3>
      {children}
    </section>
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

function TotalRow({ group, rowBg }: { group: TradeGroup; rowBg: string }) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? 'rgb(81 126 227 / 7%)' : rowBg;
  const pnlColor = group.totalPnl > 0 ? ACCENT.success : group.totalPnl < 0 ? ACCENT.error : 'var(--text-muted)';
  const pctColor = group.totalPnlPct > 0 ? ACCENT.success : group.totalPnlPct < 0 ? ACCENT.error : 'var(--text-muted)';

  const cellStyle: React.CSSProperties = {
    padding: '6px 8px',
    borderBottom: '2px solid var(--border)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
    fontSize: 11,
  };

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: bg, borderTop: '1px solid var(--border)' }}
    >
      <td style={{ ...cellStyle, color: 'var(--text-secondary)', fontWeight: 700, fontStyle: 'italic' }}>
        #{group.baseId} Total
      </td>
      <td colSpan={7} style={{ ...cellStyle, color: 'var(--text-muted)', fontStyle: 'italic' }}>
        {group.trades.length} partial exits
      </td>
      <td style={{ ...cellStyle, color: pnlColor, fontWeight: 700 }}>{formatMoney(group.totalPnl)}</td>
      <td style={{ ...cellStyle, color: pctColor, fontWeight: 700 }}>{`${group.totalPnlPct.toFixed(2)}%`}</td>
      <td style={{ ...cellStyle, color: 'var(--text-muted)', fontStyle: 'italic' }}>—</td>
      <td style={{ ...cellStyle, color: 'var(--text-muted)', fontStyle: 'italic' }}>—</td>
      <td style={{ ...cellStyle, color: 'var(--text-muted)', fontStyle: 'italic' }}>—</td>
    </tr>
  );
}

function TradeRow({ trade, rowBg }: { trade: Trade; rowBg: string }) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? 'rgb(81 126 227 / 9%)' : rowBg;
  const side = normalizeSide(trade.side);
  const status = normalizeStatus(trade.status);
  const pnlColor = trade.pnl > 0 ? ACCENT.success : trade.pnl < 0 ? ACCENT.error : 'var(--text-muted)';
  const pctColor = trade.pnlPercentage > 0 ? ACCENT.success : trade.pnlPercentage < 0 ? ACCENT.error : 'var(--text-muted)';
  const sideColor = side === 'LONG' ? ACCENT.success : side === 'SHORT' ? ACCENT.error : 'var(--text-muted)';
  const statusColor = status === 'OPEN' ? ACCENT.success : status === 'PARTIAL' ? ACCENT.warning : 'var(--text-muted)';
  const partial = partialDisplay(trade);

  const cellStyle: React.CSSProperties = {
    padding: '10px 8px',
    borderBottom: '1px solid var(--border)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  };

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: bg }}
    >
      <td style={cellStyle}>{trade.id}</td>
      <td style={cellStyle} title={trade.entryTime}>{formatTime(trade.entryTime)}</td>
      <td style={cellStyle}>{trade.symbol ?? 'BTC.P/USDT'}</td>
      <td style={{ ...cellStyle, color: sideColor, fontWeight: 600 }}>{side}</td>
      <td style={cellStyle}>{trade.quantity > 0 ? trade.quantity.toFixed(4) : '—'}</td>
      <td style={cellStyle}>{formatMoney(trade.entryPrice)}</td>
      <td style={cellStyle}>{trade.exitPrice ? formatMoney(trade.exitPrice) : '—'}</td>
      <td style={cellStyle}>{formatDuration(trade.bars)}</td>
      <td style={{ ...cellStyle, color: pnlColor, fontWeight: 600 }}>{formatMoney(trade.pnl)}</td>
      <td style={{ ...cellStyle, color: pctColor, fontWeight: 600 }}>
        {`${trade.pnlPercentage.toFixed(2)}%`}
      </td>
      <td style={{ ...cellStyle, color: statusColor, fontWeight: 600 }}>{status}</td>
      <td style={{ ...cellStyle, color: pnlColor }}>{partial}</td>
      <td style={{ ...cellStyle, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 170 }} title={notesDisplay(trade)}>{notesDisplay(trade)}</td>
    </tr>
  );
}
