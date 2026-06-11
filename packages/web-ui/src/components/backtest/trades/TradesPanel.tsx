'use client';

import { useMemo, useState } from 'react';
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

interface Column { key: ColumnKey; label: string; width: number; sortable: boolean; }

// Matches PyQt5 column order/widths from trades_panel.py:230,252.
// Widths trimmed (BTCAAAAA-35662) so total ~1185px fits 1280px+ screens.
const COLUMNS: Column[] = [
  { key: 'id',       label: 'ID',        width: 55,  sortable: true  },
  { key: 'time',     label: 'Time',      width: 85,  sortable: true  },
  { key: 'symbol',   label: 'Symbol',    width: 100, sortable: false },
  { key: 'side',     label: 'Side',      width: 65,  sortable: true  },
  { key: 'size',     label: 'Size',      width: 75,  sortable: true  },
  { key: 'entry',    label: 'Entry',     width: 95,  sortable: true  },
  { key: 'exit',     label: 'Exit',      width: 95,  sortable: true  },
  { key: 'duration', label: 'Duration',  width: 80,  sortable: false },
  { key: 'pnl',      label: 'P&L',       width: 95,  sortable: true  },
  { key: 'pnlPct',   label: 'P&L %',     width: 80,  sortable: true  },
  { key: 'status',   label: 'Status',    width: 75,  sortable: true  },
  { key: 'partial',  label: 'Partial %', width: 115, sortable: false },
  { key: 'notes',    label: 'Notes',     width: 170, sortable: false },
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
  return d.toLocaleTimeString(undefined, { hour12: false });
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
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Bars: ${formatMoney(t.pnl)}`;
  if (u === 'SL') return `SL: ${formatMoney(t.pnl)}`;
  if (/^TP[0-9]+$/.test(u)) return `${u}: ${formatMoney(t.pnl)}`;
  return '—';
}

// Short exit-type codes the backend sends via exit_condition_name — these need
// expansion into human-readable notes rather than being returned verbatim.
const EXIT_TYPE_CODES = new Set(['TP1','TP2','TP3','TP4','TP5','SL','STOP_LOSS','MAX_BARS','TIME_LIMIT']);

function notesDisplay(t: Trade): string {
  // Use raw notes only when they are a real descriptive string, not just a
  // bare exit-type abbreviation that the backend copies from exit_condition_name.
  const rawNotes = (t.notes ?? '').trim();
  const isAbbrev = rawNotes === '' || EXIT_TYPE_CODES.has(rawNotes.toUpperCase());

  if (!isAbbrev) return rawNotes;

  const u = ((t.exitType ?? rawNotes) as string).toUpperCase().trim();
  if (/^TP[0-9]+$/.test(u)) return `${u} Hit`;
  if (u === 'SL' || u === 'STOP_LOSS') return 'Stop Loss Hit (1 exits)';
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Hold Time (${t.bars ?? 0} bars)`;
  if (u) return u;
  return '—';
}

// Mirrors trades_panel.py:_aggregate_exits (lines 649-727).
// The web API sends individual partial-exit records; we group them here so
// each logical trade shows one row with combined partial_exit_breakdown/notes.
function aggregateTrades(raw: Trade[]): Trade[] {
  // Strip trailing _N suffix to get base trade ID (e.g. "5_1" → "5").
  const baseId = (id: string) => id.replace(/_\d+$/, '');

  // Preserve insertion order of first-seen base IDs.
  const order: string[] = [];
  const groups = new Map<string, Trade[]>();
  for (const t of raw) {
    const b = baseId(String(t.id));
    if (!groups.has(b)) { groups.set(b, []); order.push(b); }
    groups.get(b)!.push(t);
  }

  return order.map(b => {
    const exits = groups.get(b)!;
    if (exits.length === 1) {
      // Single exit — still run through partialDisplay/notesDisplay at render.
      return exits[0];
    }

    const base = { ...exits[0] };

    // Aggregate PnL.
    base.pnl = exits.reduce((s, e) => s + e.pnl, 0);
    base.pnlPercentage = exits.reduce((s, e) => s + e.pnlPercentage, 0);

    // Build breakdown tracking (mirrors tp_counts dict in Python).
    const tpCounts: Record<string, number> = { TP1: 0, TP2: 0, TP3: 0, SL: 0, MAX_BARS: 0 };
    const breakdown: string[] = [];
    let maxBarsPnl = 0;

    for (const e of exits) {
      const ec = (e.exitType ?? '').toUpperCase().trim();
      const pnl = e.pnl;
      if (ec === 'TP1' || ec === 'TP2' || ec === 'TP3') {
        breakdown.push(`${ec}: $${pnl.toFixed(2)}`);
        tpCounts[ec] = (tpCounts[ec] ?? 0) + 1;
      } else if (ec === 'SL' || ec === 'STOP_LOSS') {
        breakdown.push(`SL: $${pnl.toFixed(2)}`);
        tpCounts['SL'] += 1;
      } else if (ec === 'MAX_BARS' || ec === 'TIME_LIMIT') {
        if (tpCounts['MAX_BARS'] === 0) {
          maxBarsPnl = pnl;
          breakdown.push(`Max Bars: $${pnl.toFixed(2)}`);
          tpCounts['MAX_BARS'] = 1;
        }
      }
    }

    let partialBreakdown: string;
    let notes: string;

    if (tpCounts['MAX_BARS'] > 0) {
      partialBreakdown = `Max Bars: $${maxBarsPnl.toFixed(2)}`;
      notes = 'Max Bars Exit';
    } else if (tpCounts['SL'] > 0) {
      partialBreakdown = breakdown.filter(s => s.startsWith('SL:')).join(' | ');
      notes = `Stop Loss Hit (${tpCounts['SL']} exits)`;
    } else {
      partialBreakdown = breakdown.length > 0 ? breakdown.join(' | ') : '-';
      if (tpCounts['TP1'] > 0 && tpCounts['TP2'] > 0 && tpCounts['TP3'] > 0) {
        notes = 'ALL TP Exits';
      } else if (exits.length > 1) {
        const hitTps = ['TP1','TP2','TP3'].filter(tp => tpCounts[tp] > 0);
        notes = hitTps.length > 0 ? `Partial Exits: ${hitTps.join(', ')}` : (exits[0].notes ?? '');
      } else {
        notes = exits[0].notes ?? '';
      }
    }

    base.partialBreakdown = partialBreakdown;
    base.notes = notes;

    // Use last exit's exit price, bars, status.
    const last = exits[exits.length - 1];
    base.exitPrice = last.exitPrice;
    base.bars = last.bars;
    base.status = last.status;

    return base;
  });
}

function sortValue(t: Trade, key: ColumnKey): number | string {
  switch (key) {
    case 'id':     return Number(t.id) || 0;
    case 'time':   return new Date(t.entryTime).getTime() || 0;
    case 'side':   return normalizeSide(t.side);
    case 'size':   return t.quantity;
    case 'entry':  return t.entryPrice;
    case 'exit':   return t.exitPrice;
    case 'pnl':    return t.pnl;
    case 'pnlPct': return t.pnlPercentage;
    case 'status': return normalizeStatus(t.status);
    default:       return 0;
  }
}

export function TradesPanel({ trades = [] }: TradesPanelProps) {
  const [sortKey, setSortKey] = useState<ColumnKey>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  // Aggregate partial exits into single rows (mirrors thick-client _aggregate_exits).
  const aggregated = useMemo(() => aggregateTrades(trades), [trades]);

  const summary = useMemo(() => {
    const total = aggregated.length;
    const wins = aggregated.filter(t => t.pnl > 0).length;
    const losses = aggregated.filter(t => t.pnl < 0).length;
    const longs = aggregated.filter(t => normalizeSide(t.side) === 'LONG').length;
    const shorts = aggregated.filter(t => normalizeSide(t.side) === 'SHORT').length;
    const totalPnl = aggregated.reduce((s, t) => s + t.pnl, 0);
    const winRate = total > 0 ? (wins / total) * 100 : 0;
    return { total, wins, losses, longs, shorts, totalPnl, winRate };
  }, [aggregated]);

  const sortedTrades = useMemo(() => {
    if (aggregated.length === 0) return aggregated;
    const arr = [...aggregated];
    arr.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [aggregated, sortKey, sortDir]);

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
              color: 'var(--text-secondary)',
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
              {sortedTrades.map((trade, i) => {
                // Alternate row dimming preserved from cycle 29C — softened to a
                // subtle white tint so the panel reads as part of the dialog.
                const rowBg = i % 2 === 0 ? 'transparent' : 'rgb(81 126 227 / 4%)';
                return <TradeRow key={`${trade.id}-${i}`} trade={trade} rowBg={rowBg} />;
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
          Showing: <b style={{ color: 'var(--text-secondary)' }}>All Trades ({aggregated.length})</b>
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
        background: 'rgba(255, 255, 255, 0.02)',
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
      <SummaryItem label="Total P&L" value={formatMoney(summary.totalPnl)} valueColor={totalPnlColor} />
      <SummaryItem label="Win Rate" value={`${summary.winRate.toFixed(2)}%`} valueColor={winRateColored} />
      <SummaryItem label="Long Trades" value={String(summary.longs)} valueColor={longColor} />
      <SummaryItem label="Short Trades" value={String(summary.shorts)} valueColor={shortColor} />
      <SummaryItem label="Winning Trades" value={String(summary.wins)} />
      <SummaryItem label="Losing Trades" value={String(summary.losses)} />
    </div>
  );
}

function SummaryItem({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <span>
      {label}:{' '}
      <b style={{ color: valueColor ?? 'var(--text-secondary)' }}>{value}</b>
    </span>
  );
}

function TradeRow({ trade, rowBg }: { trade: Trade; rowBg: string }) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? 'rgba(255, 255, 255, 0.04)' : rowBg;
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
      <td style={cellStyle}>{formatTime(trade.entryTime)}</td>
      <td style={cellStyle}>{trade.symbol ?? 'BTC.P/USDT'}</td>
      <td style={{ ...cellStyle, color: sideColor, fontWeight: 600 }}>{side}</td>
      <td style={cellStyle}>{trade.quantity.toFixed(4)}</td>
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
