'use client';

import React, { useMemo } from 'react';

export interface PhaseData {
  name: string;
  startUs: number;
  durationUs: number;
  outcome?: string;
}

export interface PerPhaseTimingChartProps {
  phases: PhaseData[];
  totalCycleDurationUs?: number;
  className?: string;
}

const PHASE_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ef4444', // red
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
  '#14b8a6', // teal
];

const formatUs = (us: number): string => {
  if (us >= 1_000_000) return `${(us / 1_000_000).toFixed(2)}s`;
  if (us >= 1_000) return `${(us / 1_000).toFixed(1)}ms`;
  return `${us}µs`;
};

export const PerPhaseTimingChart: React.FC<PerPhaseTimingChartProps> = ({
  phases,
  totalCycleDurationUs,
  className = '',
}) => {
  const maxUs = useMemo(() => {
    if (totalCycleDurationUs) return totalCycleDurationUs;
    if (phases.length === 0) return 1;
    return Math.max(...phases.map((p) => p.startUs + p.durationUs));
  }, [phases, totalCycleDurationUs]);

  if (phases.length === 0) {
    return (
      <div
        className={`flex items-center justify-center h-48 rounded ${className}`}
        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}
      >
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Waiting for phase events…</p>
      </div>
    );
  }

  const LABEL_W = 140;
  const VALUE_W = 72;
  const BAR_GAP = 4;
  const ROW_H = 28;
  const AXIS_H = 24;
  const PAD = 8;

  const chartH = phases.length * (ROW_H + BAR_GAP) + AXIS_H + PAD * 2;

  return (
    <div
      className={`rounded overflow-x-auto ${className}`}
      style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', minHeight: chartH }}
      style={{ minHeight: chartH }}
    >
      <div className="relative" style={{ height: chartH }}>
        <svg width="100%" height={chartH} style={{ position: 'absolute', inset: 0 }}>
          {/* Axis line */}
          <line
            x1={LABEL_W}
            y1={PAD}
            x2={LABEL_W}
            y2={chartH - AXIS_H}
            stroke="#52525b"
            strokeWidth={1}
          />

          {/* Tick marks */}
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const x = `calc(${LABEL_W}px + (100% - ${LABEL_W + VALUE_W}px) * ${t})`;
            return (
              <g key={t}>
                <line
                  x1={x}
                  y1={PAD}
                  x2={x}
                  y2={chartH - AXIS_H}
                  stroke="#3f3f46"
                  strokeWidth={1}
                  strokeDasharray="2 4"
                />
              </g>
            );
          })}

          {/* Phase rows */}
          {phases.map((phase, i) => {
            const y = PAD + i * (ROW_H + BAR_GAP);
            const color = PHASE_COLORS[i % PHASE_COLORS.length];
            const startPct = (phase.startUs / maxUs) * 100;
            const widthPct = (phase.durationUs / maxUs) * 100;

            return (
              <g key={phase.name}>
                {/* Phase label */}
                <text
                  x={LABEL_W - 6}
                  y={y + ROW_H / 2 + 4}
                  textAnchor="end"
                  fill="#a1a1aa"
                  fontSize={11}
                  fontFamily="monospace"
                >
                  {phase.name.length > 14 ? phase.name.slice(0, 13) + '…' : phase.name}
                </text>

                {/* Bar background */}
                <rect
                  x={LABEL_W}
                  y={y + 2}
                  width="100%"
                  height={ROW_H - 4}
                  fill="#27272a"
                  rx={3}
                />

                {/* Bar */}
                <rect
                  x={`calc(${LABEL_W}px + (100% - ${LABEL_W + VALUE_W}px) * ${startPct / 100})`}
                  y={y + 2}
                  width={`calc((100% - ${LABEL_W + VALUE_W}px) * ${widthPct / 100})`}
                  height={ROW_H - 4}
                  fill={color}
                  rx={3}
                  opacity={0.85}
                />

                {/* Duration label */}
                <text
                  x={`calc(100% - ${VALUE_W / 2}px)`}
                  y={y + ROW_H / 2 + 4}
                  textAnchor="middle"
                  fill="#d4d4d8"
                  fontSize={10}
                  fontFamily="monospace"
                >
                  {formatUs(phase.durationUs)}
                </text>
              </g>
            );
          })}

          {/* Axis labels */}
          {[0, 0.5, 1].map((t) => (
            <text
              key={t}
              x={`calc(${LABEL_W}px + (100% - ${LABEL_W + VALUE_W}px) * ${t})`}
              y={chartH - 4}
              textAnchor="middle"
              fill="#71717a"
              fontSize={9}
              fontFamily="monospace"
            >
              {formatUs(maxUs * t)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
};

export default PerPhaseTimingChart;
