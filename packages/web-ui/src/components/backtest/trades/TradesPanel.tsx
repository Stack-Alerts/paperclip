'use client';

import { useMemo, useState } from 'react';
import { Trade } from '@/lib/strategy-builder/types';

export interface TradesPanelProps {
  trades?: Trade[];
}

// Exact PyQt5 thick-client values from src/strategy_builder/ui/styles.py
// (COLORS dict + get_table_stylesheet). Board called for matching the
// thick-client hex values rather than the web app's CSS variables.
const TC = {
  bgDark: '#0A0E15',
  bgMedium: '#12171F',
  border: '#2A3139',
  textMuted: '#9AA0A6',
  textPrimary: '#E8EAED',
  success: '#10B981',
  error: '#C35252',
  panelTitle: '#095983',
  rowHover: '#021a1e',
  headerHover: '#252b36',
} as const;

type ColumnKey =
  | 'id' | 'time' | 'symbol' | 'side' | 'size' | 'entry' | 'exit'
  | 'duration' | 'pnl' | 'pnlPct' | 'status' | 'partial' | 'notes';

interface Column { key: ColumnKey; label: string; width: number; sortable: boolean; }

// Matches PyQt5 column order/widths from trades_panel.py:230,252.
const COLUMNS: Column[] = [
  { key: 'id',       label: 'ID',        width: 80,  sortable: true  },
  { key: 'time',     label: 'Time',      width: 110, sortable: true  },
  { key: 'symbol',   label: 'Symbol',    width: 110, sortable: false },
  { key: 'side',     label: 'Side',      width: 80,  sortable: true  },
  { key: 'size',     label: 'Size',      width: 90,  sortable: true  },
  { key: 'entry',    label: 'Entry',     width: 110, sortable: true  },
  { key: 'exit',     label: 'Exit',      width: 110, sortable: true  },
  { key: 'duration', label: 'Duration',  width: 100, sortable: false },
  { key: 'pnl',      label: 'P&L',       width: 110, sortable: true  },
  { key: 'pnlPct',   label: 'P&L %',     width: 100, sortable: true  },
  { key: 'status',   label: 'Status',    width: 90,  sortable: true  },
  { key: 'partial',  label: 'Partial %', width: 240, sortable: false },
  { key: 'notes',    label: 'Notes',     width: 280, sortable: false },
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

function normalizeStatus(raw?: string): 'OPEN' | 'CLOSED' {
  if (!raw) return 'CLOSED';
  return raw.toUpperCase() === 'OPEN' ? 'OPEN' : 'CLOSED';
}

function normalizeSide(raw?: string): 'LONG' | 'SHORT' | '—' {
  if (!raw) return '—';
  const u = raw.toUpperCase();
  return u === 'LONG' || u === 'SHORT' ? u : '—';
}

function partialDisplay(t: Trade): string {
  if (!t.exitType) return '—';
  const u = t.exitType.toUpperCase();
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Bars: ${formatMoney(t.pnl)}`;
  if (u === 'SL') return `SL: ${formatMoney(t.pnl)}`;
  if (/^TP[0-9]+$/.test(u)) return `${u}: ${formatMoney(t.pnl)}`;
  return t.exitType;
}

function notesDisplay(t: Trade): string {
  if (!t.exitType) return '—';
  const u = t.exitType.toUpperCase();
  if (u === 'TP1' || u === 'TP2' || u === 'TP3') return `${u} Hit`;
  if (u === 'SL') return 'Stop Loss Hit';
  if (u === 'MAX_BARS' || u === 'TIME_LIMIT') return `Max Hold Time (${t.bars} bars)`;
  return t.exitType;
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

  const sortedTrades = useMemo(() => {
    if (trades.length === 0) return trades;
    const arr = [...trades];
    arr.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
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

  const totalPnlColor =
    summary.totalPnl > 0 ? TC.success
    : summary.totalPnl < 0 ? TC.error
    : TC.textMuted;

  if (trades.length === 0) {
    return (
      <div className="flex flex-col" style={{ gap: 16 }}>
        <PerformanceSummary summary={summary} totalPnlColor={TC.textMuted} />
        <div
          className="flex flex-col items-center justify-center py-12"
          style={{ color: TC.textMuted, background: TC.bgDark, border: `1px solid ${TC.border}` }}
        >
          <p className="text-sm">No trades yet.</p>
          <p className="text-xs mt-1">Run a backtest to see the trade log.</p>
        </div>
      </div>
    );
  }

  const totalWidth = COLUMNS.reduce((s, c) => s + c.width, 0);

  return (
    <div className="flex flex-col" style={{ gap: 16 }}>
      <PerformanceSummary summary={summary} totalPnlColor={totalPnlColor} />

      <div style={{ background: TC.bgDark, border: `1px solid ${TC.border}` }}>
        <div
          style={{
            color: TC.panelTitle,
            padding: '10px 14px',
            borderBottom: `1px solid ${TC.border}`,
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          Trade History
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              minWidth: totalWidth,
              width: '100%',
              borderCollapse: 'collapse',
              color: TC.textMuted,
              fontVariantNumeric: 'tabular-nums',
              fontSize: 12,
            }}
          >
            <colgroup>
              {COLUMNS.map(c => (<col key={c.key} style={{ width: c.width }} />))}
            </colgroup>
            <thead>
              <tr>
                {COLUMNS.map(col => {
                  const isSorted = col.sortable && sortKey === col.key;
                  return (
                    <th
                      key={col.key}
                      onClick={() => handleHeaderClick(col)}
                      onMouseEnter={e => {
                        if (col.sortable) {
                          (e.currentTarget as HTMLElement).style.background = TC.headerHover;
                        }
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.background = TC.bgMedium;
                      }}
                      style={{
                        background: TC.bgMedium,
                        color: TC.textMuted,
                        padding: '14px 12px',
                        border: `1px solid ${TC.border}`,
                        fontWeight: 600,
                        textAlign: 'center',
                        cursor: col.sortable ? 'pointer' : 'default',
                        userSelect: 'none',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {col.label}
                      {isSorted && (
                        <span style={{ marginLeft: 6, color: TC.textPrimary }}>
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
                // PyQt5 setAlternatingRowColors(True): row 0 = bg_dark, row 1 = bg_medium.
                const rowBg = i % 2 === 0 ? TC.bgDark : TC.bgMedium;
                return <TradeRow key={`${trade.id}-${i}`} trade={trade} rowBg={rowBg} />;
              })}
            </tbody>
          </table>
        </div>
        <div
          style={{
            padding: '10px 14px',
            borderTop: `1px solid ${TC.border}`,
            color: TC.textMuted,
            fontSize: 12,
          }}
        >
          Showing: <b style={{ color: TC.textPrimary }}>All Trades ({trades.length})</b>
        </div>
      </div>
    </div>
  );
}

function PerformanceSummary({
  summary,
  totalPnlColor,
}: {
  summary: { total: number; wins: number; losses: number; longs: number; shorts: number; totalPnl: number; winRate: number };
  totalPnlColor: string;
}) {
  return (
    <div style={{ background: TC.bgDark, border: `1px solid ${TC.border}` }}>
      <div
        style={{
          color: TC.panelTitle,
          padding: '10px 14px',
          borderBottom: `1px solid ${TC.border}`,
          fontWeight: 700,
          fontSize: 13,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}
      >
        Performance Summary
      </div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 30,
          padding: '20px 15px 15px 15px',
          color: TC.textMuted,
          fontSize: 13,
        }}
      >
        <SummaryItem label="Total P&L" value={formatMoney(summary.totalPnl)} valueColor={totalPnlColor} />
        <SummaryItem label="Win Rate" value={`${summary.winRate.toFixed(2)}%`} />
        <SummaryItem label="Long Trades" value={String(summary.longs)} />
        <SummaryItem label="Short Trades" value={String(summary.shorts)} />
        <SummaryItem label="Winning Trades" value={String(summary.wins)} />
        <SummaryItem label="Losing Trades" value={String(summary.losses)} />
      </div>
    </div>
  );
}

function SummaryItem({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <span>
      {label}:{' '}
      <b style={{ color: valueColor ?? TC.textPrimary }}>{value}</b>
    </span>
  );
}

function TradeRow({ trade, rowBg }: { trade: Trade; rowBg: string }) {
  const [hovered, setHovered] = useState(false);
  const bg = hovered ? TC.rowHover : rowBg;
  const side = normalizeSide(trade.side);
  const status = normalizeStatus(trade.status);
  const pnlColor = trade.pnl > 0 ? TC.success : trade.pnl < 0 ? TC.error : TC.textMuted;
  const pctColor = trade.pnlPercentage > 0 ? TC.success : trade.pnlPercentage < 0 ? TC.error : TC.textMuted;
  const sideColor = side === 'LONG' ? TC.success : side === 'SHORT' ? TC.error : TC.textMuted;
  const statusColor = status === 'OPEN' ? TC.success : TC.textMuted;
  const partial = partialDisplay(trade);

  const cellStyle: React.CSSProperties = {
    padding: '12px 8px',
    border: `1px solid ${TC.border}`,
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
      <td style={{ ...cellStyle, color: pnlColor, textAlign: 'left' }}>{partial}</td>
      <td style={{ ...cellStyle, textAlign: 'left' }}>{notesDisplay(trade)}</td>
    </tr>
  );
}
