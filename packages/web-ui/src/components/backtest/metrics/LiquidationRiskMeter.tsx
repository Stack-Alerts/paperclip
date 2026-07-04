'use client';

import { AlertOctagon } from 'lucide-react';
import { RichTooltip } from '@/components/strategy-builder/RichTooltip';
import { TT_LIQUIDATION_RISK_METER } from './MetricsPanelTooltips';

// Liquidation Risk Meter (BTCAAAAA-38748) — a risk-over-time view of how close
// the account came to a leveraged liquidation at every point in the run.
//
// This is a webui-only approximation built from data already on the client: the
// running equity curve (reconstructed from the trade ledger in MetricsPanel) and
// the run's max leverage. A ~1/leverage adverse move liquidates a leveraged
// position (10× → ~10%), so at each equity point the fraction of that budget
// consumed by the drawdown-from-peak is the liquidation risk at that moment:
//
//   liquidationMove% = 100 / leverage
//   risk%_i          = min(100, |drawdown-from-peak%|_i / liquidationMove% * 100)
//
// 0% = sitting at an equity peak (safe); 100% = the drawdown reached the
// liquidation threshold and the position would have been wiped.

export interface LiquidationRiskMeterProps {
  /** Running-capital equity values, one per point (initial + one per trade exit). */
  equityValues: number[];
  /** Max leverage used for the run. The meter is only meaningful when > 0. */
  leverage?: number;
}

type Zone = 'safe' | 'caution' | 'danger';

function zoneFor(risk: number): Zone {
  if (risk >= 66) return 'danger';
  if (risk >= 33) return 'caution';
  return 'safe';
}

function zoneColor(zone: Zone): string {
  switch (zone) {
    case 'danger': return 'var(--accent-red)';
    case 'caution': return 'var(--accent-orange)';
    default: return 'var(--accent-green)';
  }
}

function zoneLabel(zone: Zone): string {
  switch (zone) {
    case 'danger': return 'Danger';
    case 'caution': return 'Caution';
    default: return 'Safe';
  }
}

/** Per-point liquidation risk (0–100%) from an equity curve and leverage. */
export function computeLiquidationRiskSeries(equityValues: number[], leverage: number): number[] {
  if (equityValues.length === 0 || !(leverage > 0)) return [];
  const liquidationMovePct = 100 / leverage;
  const out: number[] = [];
  let peak = equityValues[0];
  for (const v of equityValues) {
    if (v > peak) peak = v;
    const ddPct = peak > 0 ? Math.abs((v - peak) / peak) * 100 : 0;
    out.push(Math.min(100, (ddPct / liquidationMovePct) * 100));
  }
  return out;
}

function RiskArea({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const W = 200, H = 100;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    // Risk is a 0–100 scale; higher risk sits higher on the chart.
    const y = H - (Math.max(0, Math.min(100, v)) / 100) * H;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const linePts = pts.join(' ');
  const areaPts = `0,${H} ${linePts} ${W},${H}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 72, display: 'block' }}>
      <polygon points={areaPts} fill={color} fillOpacity="0.14" />
      <polyline points={linePts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function LiquidationRiskMeter({ equityValues, leverage }: LiquidationRiskMeterProps) {
  if (!(leverage != null && leverage > 0) || equityValues.length < 2) return null;

  const series = computeLiquidationRiskSeries(equityValues, leverage);
  if (series.length < 2) return null;

  const peakRisk = Math.max(...series);
  const currentRisk = series[series.length - 1];
  const peakZone = zoneFor(peakRisk);
  const color = zoneColor(peakZone);
  const liquidationMovePct = 100 / leverage;

  return (
    <RichTooltip content={TT_LIQUIDATION_RISK_METER}>
      <div className="rounded p-3 cursor-default" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <AlertOctagon size={13} style={{ color }} aria-hidden="true" />
            <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Liquidation Risk Meter</p>
          </div>
          <p className="text-xs font-semibold" style={{ color, fontVariantNumeric: 'tabular-nums' }}>
            {peakRisk.toFixed(0)}% peak
          </p>
        </div>

        <RiskArea values={series} color={color} />

        {/* Horizontal meter: peak risk against the safe/caution/danger zones. */}
        <div
          className="relative mt-2 rounded-full overflow-hidden"
          style={{
            height: 8,
            background: 'linear-gradient(to right, color-mix(in srgb, var(--accent-green) 30%, transparent) 0%, color-mix(in srgb, var(--accent-orange) 30%, transparent) 50%, color-mix(in srgb, var(--accent-red) 30%, transparent) 100%)',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              position: 'absolute', top: -2, bottom: -2,
              left: `calc(${Math.max(0, Math.min(100, peakRisk)).toFixed(1)}% - 1px)`,
              width: 2, background: color,
            }}
          />
        </div>

        <div className="flex items-center justify-between mt-1.5 text-[10px]" style={{ color: 'var(--text-faint)', fontVariantNumeric: 'tabular-nums' }}>
          <span>Now {currentRisk.toFixed(0)}%</span>
          <span style={{ color }}>{zoneLabel(peakZone)}</span>
          <span>{leverage}× → liq at −{liquidationMovePct.toFixed(1)}%</span>
        </div>
        <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-faint)' }}>
          Share of the ~1/leverage liquidation budget consumed by drawdown at each point in the run.
        </p>
      </div>
    </RichTooltip>
  );
}
