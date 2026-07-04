'use client';

import { useMemo, useState } from 'react';
import { AlertOctagon } from 'lucide-react';

// Interactive underwater-drawdown chart (BTCAAAAA-38780).
//
// Extends the plain drawdown sparkline with two things the board asked for:
//   1. A **liquidation line** — the ~1/leverage adverse move that would wipe a
//      leveraged position (10× → −10%). Plotting it on the same axis as the
//      drawdown curve shows at a glance how close the account came to it.
//   2. **Pivot popovers** — the local drawdown troughs are marked with dots;
//      hovering one reveals drawdown amount ($ and %), its date, and how much
//      headroom was left before liquidation at that point.
//
// Webui-only: everything is derived from data already on the client (the
// reconstructed equity curve + the run's max leverage), matching the approach
// in LiquidationRiskMeter.tsx (BTCAAAAA-38748).

export interface DrawdownChartProps {
  /** Drawdown-from-peak percent at each point (≤ 0), aligned to `timestamps`. */
  drawdownPcts: number[];
  /** Drawdown-from-peak dollars at each point (≤ 0), aligned to `timestamps`. */
  drawdownDollars: number[];
  /** ISO timestamp for each point, aligned to the series above. */
  timestamps: string[];
  /** Max leverage for the run — draws the liquidation line when > 0. */
  leverage?: number;
}

interface Pivot {
  index: number;
  ddPct: number;
  ddDollar: number;
  timestamp: string;
  isWorst: boolean;
}

const W = 200;
const H = 100;

/** Local drawdown troughs (points at least as deep as both neighbours). The
 *  deepest is flagged `isWorst`. Plateaus contribute a single pivot (first
 *  index of the run). At most `limit` troughs are kept, deepest first, so the
 *  chart stays readable on long runs. */
function findTroughs(dd: number[], limit = 7): number[] {
  if (dd.length < 3) {
    // Degenerate series: mark the single deepest underwater point if any.
    let worst = -1;
    let worstVal = 0;
    dd.forEach((v, i) => { if (v < worstVal) { worstVal = v; worst = i; } });
    return worst >= 0 ? [worst] : [];
  }
  const troughs: number[] = [];
  for (let i = 1; i < dd.length - 1; i++) {
    const v = dd[i];
    if (v >= -0.01) continue; // not meaningfully underwater
    const prev = dd[i - 1];
    const next = dd[i + 1];
    // Local minimum; on a flat run only the first index qualifies (v < prev).
    if (v <= prev && v <= next && v < prev) troughs.push(i);
  }
  if (troughs.length <= limit) return troughs.sort((a, b) => a - b);
  return troughs
    .sort((a, b) => dd[a] - dd[b]) // most negative first
    .slice(0, limit)
    .sort((a, b) => a - b);
}

function fmtDate(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function fmtUsd(v: number): string {
  const sign = v < 0 ? '−$' : '$';
  return `${sign}${Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function DrawdownChart({ drawdownPcts, drawdownDollars, timestamps, leverage }: DrawdownChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);

  const liquidationMovePct = leverage != null && leverage > 0 ? 100 / leverage : null;

  const { pivots, worstDd, axisMin } = useMemo(() => {
    const troughIdx = findTroughs(drawdownPcts);
    const minDd = drawdownPcts.length ? Math.min(0, ...drawdownPcts) : 0;
    // Keep both the deepest trough and the liquidation line on-axis so the
    // "how close did it get" comparison is always visible.
    const magnitude = Math.max(Math.abs(minDd), liquidationMovePct ?? 0, 0.5);
    const worst = drawdownPcts.indexOf(minDd);
    const ps: Pivot[] = troughIdx.map(i => ({
      index: i,
      ddPct: drawdownPcts[i],
      ddDollar: drawdownDollars[i] ?? 0,
      timestamp: timestamps[i] ?? '',
      isWorst: i === worst,
    }));
    return { pivots: ps, worstDd: minDd, axisMin: -magnitude * 1.1 };
  }, [drawdownPcts, drawdownDollars, timestamps, liquidationMovePct]);

  if (drawdownPcts.length < 2) return null;

  const n = drawdownPcts.length;
  const xPct = (i: number) => (i / (n - 1)) * 100;
  // 0% drawdown sits at the top (0), axisMin at the bottom (100).
  const topPct = (v: number) => (Math.max(axisMin, Math.min(0, v)) / axisMin) * 100;

  // SVG polyline/area for the drawdown curve.
  const linePts = drawdownPcts
    .map((v, i) => `${((i / (n - 1)) * W).toFixed(2)},${((topPct(v) / 100) * H).toFixed(2)}`)
    .join(' ');
  const areaPts = `0,0 ${linePts} ${W},0`;

  const liqTop = liquidationMovePct != null ? topPct(-liquidationMovePct) : null;
  const worstPct = worstDd;
  const worstShare = liquidationMovePct != null && liquidationMovePct > 0
    ? Math.min(100, (Math.abs(worstPct) / liquidationMovePct) * 100)
    : null;

  return (
    <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <AlertOctagon size={13} style={{ color: 'var(--accent-orange)' }} aria-hidden="true" />
          <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Drawdown vs Liquidation</p>
        </div>
        <p className="text-xs font-semibold" style={{ color: 'var(--accent-orange)', fontVariantNumeric: 'tabular-nums' }}>
          {worstPct.toFixed(2)}%
        </p>
      </div>

      {/* Chart body — relative so pivot markers + popovers position over the SVG. */}
      <div className="relative" style={{ height: 96, width: '100%' }}>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: '100%', display: 'block' }}>
          <polygon points={areaPts} fill="var(--accent-orange)" fillOpacity="0.14" />
          <polyline points={linePts} fill="none" stroke="var(--accent-orange)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          {liqTop != null && (
            <line
              x1="0" y1={(liqTop / 100) * H} x2={W} y2={(liqTop / 100) * H}
              stroke="var(--accent-red)" strokeWidth="1" strokeDasharray="4 3"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>

        {/* Liquidation-line label, pinned to the right edge at its y-position. */}
        {liqTop != null && liquidationMovePct != null && (
          <span
            className="absolute text-[9px] px-1 rounded pointer-events-none"
            style={{
              top: `${liqTop}%`, right: 0, transform: 'translateY(-50%)',
              color: 'var(--accent-red)', background: 'var(--bg-card)',
              fontVariantNumeric: 'tabular-nums', lineHeight: 1.2,
            }}
          >
            Liquidation −{liquidationMovePct.toFixed(1)}%
          </span>
        )}

        {/* Pivot markers — hoverable dots at each local trough. */}
        {pivots.map(p => {
          const left = xPct(p.index);
          const top = topPct(p.ddPct);
          const alignRight = left > 78;
          const alignLeft = left < 22;
          const below = top < 42; // popover goes below when the pivot sits high
          return (
            <div key={p.index} className="absolute" style={{ left: `${left}%`, top: `${top}%`, transform: 'translate(-50%, -50%)' }}>
              <button
                type="button"
                aria-label={`Drawdown ${p.ddPct.toFixed(2)} percent on ${fmtDate(p.timestamp)}`}
                onMouseEnter={() => setHovered(p.index)}
                onMouseLeave={() => setHovered(h => (h === p.index ? null : h))}
                onFocus={() => setHovered(p.index)}
                onBlur={() => setHovered(h => (h === p.index ? null : h))}
                className="block rounded-full cursor-pointer"
                style={{
                  width: p.isWorst ? 9 : 7,
                  height: p.isWorst ? 9 : 7,
                  background: p.isWorst ? 'var(--accent-red)' : 'var(--accent-orange)',
                  border: '1.5px solid var(--bg-card)',
                  boxShadow: hovered === p.index ? '0 0 0 3px color-mix(in srgb, var(--accent-orange) 35%, transparent)' : 'none',
                }}
              />
              {hovered === p.index && (
                <div
                  className="absolute z-10 rounded p-2 text-[10px] pointer-events-none"
                  style={{
                    minWidth: 168,
                    [below ? 'top' : 'bottom']: 'calc(100% + 6px)',
                    left: alignRight ? 'auto' : alignLeft ? 0 : '50%',
                    right: alignRight ? 0 : 'auto',
                    transform: alignRight || alignLeft ? 'none' : 'translateX(-50%)',
                    background: 'var(--bg-elevated, var(--bg-card))',
                    border: '1px solid var(--border)',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
                    color: 'var(--text-secondary)',
                    fontVariantNumeric: 'tabular-nums',
                    lineHeight: 1.5,
                  }}
                >
                  <p className="font-semibold mb-1" style={{ color: p.isWorst ? 'var(--accent-red)' : 'var(--accent-orange)' }}>
                    {p.isWorst ? 'Worst drawdown' : 'Drawdown pivot'}
                  </p>
                  <div className="flex justify-between gap-3">
                    <span style={{ color: 'var(--text-faint)' }}>Date</span>
                    <span>{fmtDate(p.timestamp)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span style={{ color: 'var(--text-faint)' }}>Drawdown</span>
                    <span style={{ color: 'var(--accent-orange)' }}>{p.ddPct.toFixed(2)}% · {fmtUsd(p.ddDollar)}</span>
                  </div>
                  {liquidationMovePct != null ? (
                    <div className="flex justify-between gap-3">
                      <span style={{ color: 'var(--text-faint)' }}>To liquidation</span>
                      {(() => {
                        const headroom = liquidationMovePct - Math.abs(p.ddPct);
                        const share = Math.min(100, (Math.abs(p.ddPct) / liquidationMovePct) * 100);
                        return headroom <= 0 ? (
                          <span style={{ color: 'var(--accent-red)' }}>breached liq. line</span>
                        ) : (
                          <span style={{ color: share >= 66 ? 'var(--accent-red)' : share >= 33 ? 'var(--accent-orange)' : 'var(--accent-green)' }}>
                            {headroom.toFixed(1)}% left ({share.toFixed(0)}% used)
                          </span>
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="flex justify-between gap-3">
                      <span style={{ color: 'var(--text-faint)' }}>To liquidation</span>
                      <span style={{ color: 'var(--text-faint)' }}>set leverage</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-faint)' }}>
        {liquidationMovePct != null
          ? `Percent below the running peak. Dashed line = ${leverage}× liquidation (−${liquidationMovePct.toFixed(1)}%); worst drawdown used ${worstShare != null ? worstShare.toFixed(0) : '—'}% of that budget. Hover a dot for details.`
          : 'Percent below the running peak. Hover a dot for drawdown amount and date — set a leverage to see the liquidation line.'}
      </p>
    </div>
  );
}
