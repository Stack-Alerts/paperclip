'use client';

import { useState } from 'react';
import { AlertOctagon } from 'lucide-react';
import { RichTooltip } from '@/components/strategy-builder/RichTooltip';
import { TT_LIQUIDATION_RISK_METER } from './MetricsPanelTooltips';

// Liquidation Risk Meter (BTCAAAAA-38748, BTCAAAAA-38724) — a risk-over-time view
// of how close the account came to a leveraged liquidation at every point in the
// run.
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
// liquidation threshold and the position would have been wiped. The chart draws
// an explicit Liquidation Line at that 100% level so the operator can see how
// close the worst drawdown came, and pivot points expose a hover popover with the
// dollar/percent drawdown, the date, and the remaining buffer to liquidation.

export interface LiquidationRiskMeterProps {
  /** Running-capital equity curve (initial capital point, then one per exit). */
  equityCurve: Array<{ timestamp: string; value: number }>;
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

// Turning points of the risk series — the local maxima/minima an operator would
// actually care about — plus the worst-risk point and the final point, with a
// small prominence filter so jagged curves do not litter the chart with dots.
function findPivots(series: number[]): number[] {
  const n = series.length;
  if (n < 2) return n === 1 ? [0] : [];
  const turns: number[] = [];
  let lastDir = 0;
  for (let i = 1; i < n; i++) {
    const d = series[i] - series[i - 1];
    const dir = d > 0 ? 1 : d < 0 ? -1 : 0;
    if (dir !== 0 && lastDir !== 0 && dir !== lastDir) turns.push(i - 1);
    if (dir !== 0) lastDir = dir;
  }
  let maxI = 0;
  for (let i = 1; i < n; i++) if (series[i] > series[maxI]) maxI = i;
  const candidates = [...new Set([0, ...turns, maxI, n - 1])].sort((a, b) => a - b);
  const kept: number[] = [];
  for (const i of candidates) {
    const forced = i === maxI || i === n - 1;
    if (forced || kept.length === 0 || Math.abs(series[i] - series[kept[kept.length - 1]]) >= 2) {
      kept.push(i);
    }
  }
  return kept;
}

function formatSignedCurrency(v: number): string {
  const sign = v < 0 ? '−' : v > 0 ? '+' : '';
  return `${sign}$${Math.round(Math.abs(v)).toLocaleString()}`;
}

function formatDate(ts: string): string {
  if (!ts) return '—';
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleDateString();
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
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }}>
      <polygon points={areaPts} fill={color} fillOpacity="0.14" />
      <polyline points={linePts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function LiquidationRiskMeter({ equityCurve, leverage }: LiquidationRiskMeterProps) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (!(leverage != null && leverage > 0) || !equityCurve || equityCurve.length < 2) return null;

  const values = equityCurve.map(p => p.value);
  const series = computeLiquidationRiskSeries(values, leverage);
  if (series.length < 2) return null;

  const peakRisk = Math.max(...series);
  const currentRisk = series[series.length - 1];
  const peakZone = zoneFor(peakRisk);
  const color = zoneColor(peakZone);
  const liquidationMovePct = 100 / leverage;

  // Running equity peak per point → dollar/percent drawdown for the popover.
  const peaks: number[] = [];
  {
    let pk = values[0];
    for (const v of values) { if (v > pk) pk = v; peaks.push(pk); }
  }
  const pivots = findPivots(series);
  const n = series.length;
  const CHART_H = 72;

  return (
    <div className="rounded p-3 cursor-default" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-1.5">
        <RichTooltip content={TT_LIQUIDATION_RISK_METER}>
          <div className="flex items-center gap-1.5">
            <AlertOctagon size={13} style={{ color }} aria-hidden="true" />
            <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Liquidation Risk Meter</p>
          </div>
        </RichTooltip>
        <p className="text-xs font-semibold" style={{ color, fontVariantNumeric: 'tabular-nums' }}>
          {peakRisk.toFixed(0)}% peak
        </p>
      </div>

      {/* Chart: risk area + an explicit Liquidation Line at the 100% level, with
          hoverable pivot-point markers. */}
      <div className="relative" style={{ height: CHART_H }}>
        <RiskArea values={series} color={color} />

        {/* Liquidation Line — the 100%-risk threshold at the top of the chart. */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute', top: 0, left: 0, right: 0,
            borderTop: '1px dashed var(--accent-red)', opacity: 0.7,
          }}
        />
        <span
          className="text-[9px] font-semibold"
          style={{ position: 'absolute', top: 1, right: 2, color: 'var(--accent-red)', lineHeight: 1, background: 'var(--bg-card)', padding: '0 2px' }}
        >
          Liquidation (−{liquidationMovePct.toFixed(1)}%)
        </span>

        {/* Pivot-point markers. */}
        {pivots.map(i => {
          const x = n > 1 ? (i / (n - 1)) * 100 : 0;
          const yTop = (1 - Math.max(0, Math.min(100, series[i])) / 100) * 100;
          const dotZone = zoneFor(series[i]);
          const isHover = hovered === i;
          return (
            <div
              key={i}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(h => (h === i ? null : h))}
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${yTop}%`,
                width: 14, height: 14,
                transform: 'translate(-50%, -50%)',
                borderRadius: '50%',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <span
                style={{
                  width: isHover ? 8 : 6, height: isHover ? 8 : 6,
                  borderRadius: '50%',
                  background: zoneColor(dotZone),
                  border: '1.5px solid var(--bg-card)',
                  boxShadow: isHover ? '0 0 0 2px color-mix(in srgb, var(--text-faint) 40%, transparent)' : 'none',
                  transition: 'width 0.08s, height 0.08s',
                }}
              />
            </div>
          );
        })}

        {/* Hover popover for the active pivot. */}
        {hovered != null && (() => {
          const i = hovered;
          const x = Math.max(6, Math.min(94, n > 1 ? (i / (n - 1)) * 100 : 0));
          const ddDollar = values[i] - peaks[i];
          const ddPct = peaks[i] > 0 ? (ddDollar / peaks[i]) * 100 : 0;
          const risk = series[i];
          const buffer = Math.max(0, liquidationMovePct - Math.abs(ddPct));
          const z = zoneFor(risk);
          return (
            <div
              style={{
                position: 'absolute',
                left: `${x}%`,
                bottom: `calc(100% + 8px)`,
                transform: 'translateX(-50%)',
                zIndex: 20,
                pointerEvents: 'none',
                minWidth: 150,
                background: 'var(--tooltip-bg, var(--bg-card))',
                border: '1px solid var(--tooltip-border, var(--border))',
                borderRadius: 6,
                padding: '7px 9px',
                boxShadow: '0 6px 20px rgba(0,0,0,0.5)',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              <div className="text-[10px] font-semibold mb-1" style={{ color: 'var(--tooltip-title, var(--text-primary))' }}>
                {formatDate(equityCurve[i].timestamp)}
              </div>
              <div className="flex items-center justify-between gap-3 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                <span>Liq. risk</span>
                <span style={{ color: zoneColor(z), fontWeight: 600 }}>{risk.toFixed(0)}% · {zoneLabel(z)}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                <span>Drawdown</span>
                <span style={{ color: 'var(--text-primary)' }}>{formatSignedCurrency(ddDollar)} ({ddPct.toFixed(1)}%)</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                <span>To liquidation</span>
                <span style={{ color: 'var(--text-primary)' }}>{buffer.toFixed(1)}% move left</span>
              </div>
            </div>
          );
        })()}
      </div>

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
        Share of the ~1/leverage liquidation budget consumed by drawdown at each point in the run. Hover a marker for that point&apos;s drawdown and buffer to the Liquidation Line.
      </p>
    </div>
  );
}
