'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { PositionsMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';

interface Props {
  wsBaseUrl: string;
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function pnlColor(n: number) {
  if (n > 0) return 'text-emerald-400';
  if (n < 0) return 'text-red-400';
  return 'text-zinc-400';
}

export function B2PositionPanel({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<PositionsMessage>(`${wsBaseUrl}/ws/positions`);

  return (
    <PanelShell
      title="B2 · Position Panel"
      subtitle="Open positions, SL/TP levels"
      status={status}
      className="h-full"
    >
      {!data ? (
        <p className="text-xs text-zinc-500">Awaiting positions data…</p>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between">
            <Tooltip tip="Sum of unrealized PnL across all open positions in account currency.">
              <span className="text-xs text-zinc-400">Total Unrealized PnL</span>
            </Tooltip>
            <span className={`text-sm font-semibold ${pnlColor(data.total_unrealized_pnl)}`}>
              {data.total_unrealized_pnl >= 0 ? '+' : ''}
              {fmt(data.total_unrealized_pnl)}
            </span>
          </div>

          {data.positions.length === 0 ? (
            <p className="text-xs text-zinc-500">No open positions.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500">
                  <th className="pb-1 text-left font-medium">
                    <Tooltip tip="Trading instrument identifier (e.g. BTC-USDT-PERP).">
                      Instrument
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-center font-medium">
                    <Tooltip tip="LONG = expecting price to rise; SHORT = expecting price to fall.">
                      Side
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-right font-medium">
                    <Tooltip tip="Volume held in base asset units.">
                      Qty
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-right font-medium">
                    <Tooltip tip="Volume-weighted average entry price.">
                      Avg Price
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-right font-medium">
                    <Tooltip tip="Unrealized profit/loss at current mid price.">
                      Unreal PnL
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-right font-medium">
                    <Tooltip tip="Stop-loss trigger price. NULL if not set.">
                      SL
                    </Tooltip>
                  </th>
                  <th className="pb-1 text-right font-medium">
                    <Tooltip tip="Take-profit trigger price. NULL if not set.">
                      TP
                    </Tooltip>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.positions.map((pos) => (
                  <tr
                    key={`${pos.instrument_id}-${pos.side}`}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors"
                  >
                    <td className="py-1.5 font-mono text-zinc-200">{pos.instrument_id}</td>
                    <td className="py-1.5 text-center">
                      <span
                        className={`rounded px-1 py-0.5 font-semibold ${
                          pos.side === 'LONG' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'
                        }`}
                      >
                        {pos.side}
                      </span>
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-300">{fmt(pos.quantity, 4)}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-300">{fmt(pos.avg_open_price)}</td>
                    <td className={`py-1.5 text-right font-mono ${pnlColor(pos.unrealized_pnl)}`}>
                      {pos.unrealized_pnl >= 0 ? '+' : ''}{fmt(pos.unrealized_pnl)}
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">
                      {pos.stop_loss != null ? fmt(pos.stop_loss) : '—'}
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">
                      {pos.take_profit != null ? fmt(pos.take_profit) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </PanelShell>
  );
}
