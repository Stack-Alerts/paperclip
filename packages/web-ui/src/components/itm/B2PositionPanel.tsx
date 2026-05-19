'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { PositionsMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';
import { Table, TableHead, TableRow, TableCell, TableBody, Badge } from '@tremor/react';

interface Props {
  wsBaseUrl: string;
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function pnlColor(n: number) {
  if (n > 0) return 'emerald';
  if (n < 0) return 'red';
  return 'zinc';
}

export function B2PositionPanel({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<PositionsMessage>(`${wsBaseUrl}/ws/positions`);

  if (!data) {
    return (
      <PanelShell
        title="B2 · Position Panel"
        subtitle="Open positions, SL/TP levels"
        status={status}
        className="h-full"
      >
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Awaiting positions data…</p>
      </PanelShell>
    );
  }

  return (
    <PanelShell
      title="B2 · Position Panel"
      subtitle="Open positions, SL/TP levels"
      status={status}
      className="h-full"
    >
      <div className="space-y-4">
        <div>
          <Tooltip tip="Sum of unrealized PnL across all open positions in account currency.">
            <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Total Unrealized PnL</p>
          </Tooltip>
          <p
            className={`text-lg font-semibold ${
              pnlColor(data.total_unrealized_pnl) === 'emerald'
                ? 'text-emerald-400'
                : pnlColor(data.total_unrealized_pnl) === 'red'
                ? 'text-red-400'
                : ''
            }`}
            style={pnlColor(data.total_unrealized_pnl) === 'zinc' ? { color: 'var(--text-secondary)' } : undefined}
          >
            {data.total_unrealized_pnl >= 0 ? '+' : ''}${fmt(data.total_unrealized_pnl)}
          </p>
        </div>

        {data.positions.length === 0 ? (
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No open positions.</p>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <Tooltip tip="Trading instrument identifier (e.g. BTC-USDT-PERP).">
                    <span>Instrument</span>
                  </Tooltip>
                </TableCell>
                <TableCell>
                  <Tooltip tip="LONG = expecting price to rise; SHORT = expecting price to fall.">
                    <span>Side</span>
                  </Tooltip>
                </TableCell>
                <TableCell className="text-right">
                  <Tooltip tip="Volume held in base asset units.">
                    <span>Qty</span>
                  </Tooltip>
                </TableCell>
                <TableCell className="text-right">
                  <Tooltip tip="Volume-weighted average entry price.">
                    <span>Avg Price</span>
                  </Tooltip>
                </TableCell>
                <TableCell className="text-right">
                  <Tooltip tip="Unrealized profit/loss at current mid price.">
                    <span>Unreal PnL</span>
                  </Tooltip>
                </TableCell>
                <TableCell className="text-right">
                  <Tooltip tip="Stop-loss trigger price. NULL if not set.">
                    <span>SL</span>
                  </Tooltip>
                </TableCell>
                <TableCell className="text-right">
                  <Tooltip tip="Take-profit trigger price. NULL if not set.">
                    <span>TP</span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.positions.map((pos) => (
                <TableRow key={`${pos.instrument_id}-${pos.side}`}>
                  <TableCell className="font-mono text-sm">{pos.instrument_id}</TableCell>
                  <TableCell>
                    <Badge color={pos.side === 'LONG' ? 'emerald' : 'red'} className="w-fit">
                      {pos.side}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">{fmt(pos.quantity, 4)}</TableCell>
                  <TableCell className="text-right font-mono text-sm">${fmt(pos.avg_open_price)}</TableCell>
                  <TableCell
                    className={`text-right font-mono text-sm ${
                      pos.unrealized_pnl > 0
                        ? 'text-emerald-400'
                        : pos.unrealized_pnl < 0
                        ? 'text-red-400'
                        : ''
                    }`}
                  >
                    {pos.unrealized_pnl >= 0 ? '+' : ''}${fmt(pos.unrealized_pnl)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {pos.stop_loss != null ? `$${fmt(pos.stop_loss)}` : '—'}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {pos.take_profit != null ? `$${fmt(pos.take_profit)}` : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </PanelShell>
  );
}
