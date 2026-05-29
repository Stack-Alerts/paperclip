'use client';

import { Trade } from '@/lib/strategy-builder/types';

export interface TradesPanelProps {
  trades?: Trade[];
}

export function TradesPanel({ trades = [] }: TradesPanelProps) {
  if (trades.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12" style={{ color: 'var(--text-faint)' }}>
        <p className="text-sm">No trades yet.</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Run a backtest to see the trade log.</p>
      </div>
    );
  }

  return (
    <div className="overflow-auto">
      <p className="text-xs font-medium uppercase tracking-wide mb-3" style={{ color: 'var(--text-muted)' }}>
        TRADES ({trades.length})
      </p>
      <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)' }}>
            {['Entry Time', 'Exit Time', 'Entry', 'Exit', 'PnL', 'PnL %', 'Bars', 'Exit Type'].map(h => (
              <th
                key={h}
                className="text-left py-2 px-3 font-medium"
                style={{ color: 'var(--text-muted)', background: 'var(--bg-card)' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            const pnlColor = trade.pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            return (
              <tr
                key={trade.id}
                style={{ borderBottom: '1px solid var(--bg-card)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = '')}
              >
                <td className="py-2 px-3" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                  {new Date(trade.entryTime).toLocaleString()}
                </td>
                <td className="py-2 px-3" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                  {trade.exitTime ? new Date(trade.exitTime).toLocaleString() : '—'}
                </td>
                <td className="py-2 px-3" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                  ${trade.entryPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="py-2 px-3" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                  {trade.exitPrice ? `$${trade.exitPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                </td>
                <td className="py-2 px-3 font-medium" style={{ color: pnlColor, fontVariantNumeric: 'tabular-nums' }}>
                  {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                </td>
                <td className="py-2 px-3 font-medium" style={{ color: pnlColor, fontVariantNumeric: 'tabular-nums' }}>
                  {trade.pnlPercentage >= 0 ? '+' : ''}{trade.pnlPercentage.toFixed(2)}%
                </td>
                <td className="py-2 px-3" style={{ color: 'var(--text-muted)' }}>
                  {trade.bars}
                </td>
                <td className="py-2 px-3" style={{ color: 'var(--text-muted)' }}>
                  {trade.exitType || '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
