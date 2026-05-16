'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { CapitalMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';

interface Props {
  wsBaseUrl: string;
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

interface MetricRowProps {
  label: string;
  value: string;
  tip: string;
  warn?: boolean;
  danger?: boolean;
}

function MetricRow({ label, tip, value, warn, danger }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/50 last:border-0">
      <Tooltip tip={tip}>
        <span className="text-xs text-zinc-400">{label}</span>
      </Tooltip>
      <span
        className={`text-sm font-mono ${danger ? 'text-red-400 font-bold' : warn ? 'text-amber-400' : 'text-zinc-200'}`}
      >
        {value}
      </span>
    </div>
  );
}

export function B3CapitalPanel({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<CapitalMessage>(`${wsBaseUrl}/ws/capital`);

  return (
    <PanelShell
      title="B3 · Capital Panel"
      subtitle="Capital state, risk snapshot"
      status={status}
      className="h-full"
    >
      {!data ? (
        <p className="text-xs text-zinc-500">Awaiting capital data…</p>
      ) : (
        <div className="space-y-0">
          <MetricRow
            label="Total Equity"
            tip="Total account equity (unrealized PnL included) in account currency."
            value={`$${fmt(data.total_equity)}`}
          />
          <MetricRow
            label="Free Margin"
            tip="Available margin not pledged to any open position."
            value={`$${fmt(data.free_margin)}`}
          />
          <MetricRow
            label="Used Margin"
            tip="Margin currently pledged to open positions."
            value={`$${fmt(data.used_margin)}`}
          />
          <MetricRow
            label="Daily PnL"
            tip="Realized + unrealized PnL since 00:00 UTC."
            value={`${data.daily_pnl >= 0 ? '+' : ''}$${fmt(data.daily_pnl)}`}
            warn={data.daily_pnl < 0}
          />
          <MetricRow
            label="Drawdown"
            tip="Peak-to-trough equity decline as a percentage of peak equity."
            value={`${fmt(data.drawdown_pct, 1)}%`}
            warn={data.drawdown_pct > data.max_drawdown_limit_pct * 0.7}
            danger={data.drawdown_pct >= data.max_drawdown_limit_pct}
          />
          <MetricRow
            label="Risk Utilization"
            tip="Fraction of maximum allowed risk budget currently in use."
            value={`${fmt(data.risk_utilization_pct, 1)}%`}
            warn={data.risk_utilization_pct > 70}
            danger={data.risk_utilization_pct >= 90}
          />
          <MetricRow
            label="Max Drawdown Limit"
            tip="Hard drawdown limit defined in risk config. Breaching this triggers a circuit-breaker halt."
            value={`${fmt(data.max_drawdown_limit_pct, 1)}%`}
          />

          <div className="pt-3">
            <Tooltip tip="Visual risk utilization gauge. Amber > 70 %, red ≥ 90 %.">
              <p className="text-xs text-zinc-500 mb-1">Risk Gauge</p>
            </Tooltip>
            <div className="h-3 w-full rounded-full bg-zinc-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  data.risk_utilization_pct >= 90
                    ? 'bg-red-500'
                    : data.risk_utilization_pct >= 70
                    ? 'bg-amber-400'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(data.risk_utilization_pct, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </PanelShell>
  );
}
