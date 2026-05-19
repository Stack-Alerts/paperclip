'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { CapitalMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';
import { ProgressBar, DonutChart } from '@tremor/react';

interface Props {
  wsBaseUrl: string;
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function B3CapitalPanel({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<CapitalMessage>(`${wsBaseUrl}/ws/capital`);

  if (!data) {
    return (
      <PanelShell
        title="B3 · Capital Panel"
        subtitle="Capital state, risk snapshot"
        status={status}
        className="h-full"
      >
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Awaiting capital data…</p>
      </PanelShell>
    );
  }

  const riskColor = data.risk_utilization_pct >= 90 ? 'red' : data.risk_utilization_pct >= 70 ? 'amber' : 'emerald';
  const drawdownColor = data.drawdown_pct >= data.max_drawdown_limit_pct ? 'red' : data.drawdown_pct > data.max_drawdown_limit_pct * 0.7 ? 'amber' : 'emerald';

  const chartData = [
    {
      name: 'Free',
      value: Math.max(0, data.free_margin),
      color: 'emerald',
    },
    {
      name: 'Used',
      value: data.used_margin,
      color: 'blue',
    },
  ];

  return (
    <PanelShell
      title="B3 · Capital Panel"
      subtitle="Capital state, risk snapshot"
      status={status}
      className="h-full"
    >
      <div className="space-y-6">
        <div>
          <Tooltip tip="Total account equity (unrealized PnL included) in account currency.">
            <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Total Equity</p>
          </Tooltip>
          <p className="text-lg font-semibold text-emerald-400">${fmt(data.total_equity)}</p>
        </div>

        <div className="space-y-2">
          <Tooltip tip="Daily realized + unrealized PnL since 00:00 UTC.">
            <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Daily PnL</p>
          </Tooltip>
          <p className={`text-lg font-semibold ${data.daily_pnl < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {data.daily_pnl >= 0 ? '+' : ''}${fmt(data.daily_pnl)}
          </p>
        </div>

        <div className="space-y-2">
          <Tooltip tip="Fraction of maximum allowed risk budget currently in use.">
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Risk Utilization</p>
          </Tooltip>
          <ProgressBar
            value={Math.min(data.risk_utilization_pct, 100)}
            color={riskColor}
            className="text-xs"
          />
          <p className="text-xs text-right" style={{ color: 'var(--text-secondary)' }}>{fmt(data.risk_utilization_pct, 1)}%</p>
        </div>

        <div className="space-y-2">
          <Tooltip tip="Peak-to-trough equity decline as a percentage of peak equity.">
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Drawdown</p>
          </Tooltip>
          <ProgressBar
            value={Math.min(data.drawdown_pct, data.max_drawdown_limit_pct || 100)}
            color={drawdownColor}
            className="text-xs"
          />
          <p className="text-xs text-right" style={{ color: 'var(--text-secondary)' }}>
            {fmt(data.drawdown_pct, 1)}% / {fmt(data.max_drawdown_limit_pct, 1)}%
          </p>
        </div>

        <div className="space-y-2">
          <Tooltip tip="Free vs used margin allocation.">
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Margin Allocation</p>
          </Tooltip>
          <DonutChart
            data={chartData}
            category="value"
            index="name"
            valueFormatter={(v) => `$${fmt(v)}`}
            showAnimation={false}
            className="h-32"
          />
        </div>
      </div>
    </PanelShell>
  );
}
