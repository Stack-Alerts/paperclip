'use client';

import { BacktestResult } from '@/lib/strategy-builder/types';

export interface MetricsPanelProps {
  result?: BacktestResult | null;
}

export function MetricsPanel({ result }: MetricsPanelProps) {
  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-12" style={{ color: 'var(--text-faint)' }}>
        <p className="text-sm">No results yet.</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Run a backtest to see performance metrics.</p>
      </div>
    );
  }

  const winPct = (result.winRate * 100).toFixed(1);
  const returnPct = result.returnPercentage.toFixed(2);
  const drawdownPct = result.maxDrawdown.toFixed(2);

  const rows: Array<{ label: string; value: string; color?: string }> = [
    { label: 'Total Trades', value: String(result.totalTrades) },
    { label: 'Winning Trades', value: String(result.winningTrades), color: 'var(--accent-green)' },
    { label: 'Losing Trades', value: String(result.losingTrades), color: 'var(--accent-red)' },
    {
      label: 'Win Rate',
      value: `${winPct}%`,
      color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)',
    },
    {
      label: 'Total Return',
      value: `${result.returnPercentage >= 0 ? '+' : ''}${returnPct}%`,
      color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
    },
    { label: 'Profit Factor', value: result.profitFactor.toFixed(2) },
    { label: 'Sharpe Ratio', value: result.sharpeRatio.toFixed(2) },
    { label: 'Sortino Ratio', value: result.sortino_ratio.toFixed(2) },
    { label: 'Max Drawdown', value: `${drawdownPct}%`, color: 'var(--accent-orange)' },
    { label: 'Avg Win', value: `$${result.averageWin.toFixed(2)}`, color: 'var(--accent-green)' },
    { label: 'Avg Loss', value: `-$${Math.abs(result.averageLoss).toFixed(2)}`, color: 'var(--accent-red)' },
    { label: 'Initial Capital', value: `$${result.initialCapital.toLocaleString()}` },
    { label: 'Final Capital', value: `$${result.finalCapital.toLocaleString()}` },
  ];

  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide mb-4" style={{ color: 'var(--text-muted)' }}>
        PERFORMANCE METRICS
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {rows.map(({ label, value, color }) => (
          <div
            key={label}
            className="rounded p-3"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
          >
            <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
            <p className="text-sm font-semibold" style={{ color: color || 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {result.equityCurve && result.equityCurve.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
            EQUITY CURVE
          </p>
          <div className="rounded p-3 text-xs" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            {result.equityCurve.length} data points available. Chart visualization coming in BTCAAAAA-31183.
          </div>
        </div>
      )}
    </div>
  );
}
