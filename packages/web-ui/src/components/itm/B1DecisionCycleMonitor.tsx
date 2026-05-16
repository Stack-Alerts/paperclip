'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { CycleMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';
import { ProgressBar, AreaChart } from '@tremor/react';

const PHASE_LABELS: Record<string, string> = {
  bar_close: 'Bar Close',
  feature_extraction: 'Feature Extraction',
  model_inference: 'Model Inference',
  decision: 'Decision',
  idle: 'Idle',
};

const PHASE_COLOR: Record<string, string> = {
  bar_close: 'bg-sky-500',
  feature_extraction: 'bg-violet-500',
  model_inference: 'bg-amber-500',
  decision: 'bg-emerald-500',
  idle: 'bg-zinc-600',
};

const TREMOR_COLOR: Record<string, string> = {
  bar_close: 'sky',
  feature_extraction: 'violet',
  model_inference: 'amber',
  decision: 'emerald',
  idle: 'zinc',
};

const PHASE_TIPS: Record<string, string> = {
  bar_close: 'Time to process bar-close event and persist OHLCV data.',
  feature_extraction: 'Duration to compute all technical features from raw OHLCV bars.',
  model_inference: 'Time for the ML model to produce a probability score from features.',
  decision: 'Time to evaluate signal thresholds and emit a trading decision.',
  idle: 'Waiting for next bar-close trigger.',
};

interface Props {
  wsBaseUrl: string;
}

export function B1DecisionCycleMonitor({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<CycleMessage>(`${wsBaseUrl}/ws/cycle`);

  if (!data) {
    return (
      <PanelShell
        title="B1 · Decision Cycle Monitor"
        subtitle="Aggregate bar-close timing + current processing state"
        status={status}
        className="h-full"
      >
        <p className="text-xs text-zinc-500">Awaiting first cycle message…</p>
      </PanelShell>
    );
  }

  const phases = ['bar_close', 'feature_extraction', 'model_inference', 'decision'] as const;
  const totalMs = phases.reduce((acc, p) => acc + (data.phase_durations[p] ?? 0), 0);

  const chartData = phases.map((p) => ({
    phase: PHASE_LABELS[p],
    'Duration (ms)': data.phase_durations[p] ?? 0,
  }));

  return (
    <PanelShell
      title="B1 · Decision Cycle Monitor"
      subtitle="Aggregate bar-close timing + current processing state"
      status={status}
      className="h-full"
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Tooltip tip="Current phase of the decision pipeline.">
            <span className="text-xs text-zinc-400">Current Phase</span>
          </Tooltip>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold text-white ${PHASE_COLOR[data.phase]}`}
          >
            {PHASE_LABELS[data.phase] ?? data.phase}
          </span>
        </div>

        <div>
          <Tooltip tip="Elapsed time in the current phase (ms).">
            <p className="text-xs text-zinc-500 mb-1">Elapsed</p>
          </Tooltip>
          <p className="text-lg font-semibold text-zinc-100">{data.elapsed_ms} ms</p>
        </div>

        <div>
          <Tooltip tip="Decision cycle index since strategy start.">
            <p className="text-xs text-zinc-500 mb-1">Cycle #</p>
          </Tooltip>
          <p className="text-lg font-semibold text-zinc-100">{data.cycle_number}</p>
        </div>

        <div>
          <Tooltip tip="Phase breakdown for the most-recently completed cycle.">
            <p className="mb-3 text-xs text-zinc-400">Phase Durations (stacked bar)</p>
          </Tooltip>
          <div className="space-y-2">
            {phases.map((p) => {
              const ms = data.phase_durations[p] ?? 0;
              const pct = totalMs > 0 ? (ms / totalMs) * 100 : 0;
              return (
                <div key={p} className="flex items-center gap-2">
                  <Tooltip tip={PHASE_TIPS[p]}>
                    <span className="w-32 text-xs text-zinc-400 truncate">
                      {PHASE_LABELS[p]}
                    </span>
                  </Tooltip>
                  <ProgressBar value={pct} color={TREMOR_COLOR[p] as any} className="flex-1" />
                  <span className="text-xs font-mono text-zinc-300 w-12 text-right">{ms} ms</span>
                </div>
              );
            })}
            <div className="flex items-center justify-between pt-1 border-t border-zinc-800 mt-1">
              <span className="text-xs text-zinc-500">Total</span>
              <span className="text-xs font-mono text-zinc-300">{totalMs} ms</span>
            </div>
          </div>
        </div>

        {chartData.length > 0 && (
          <div className="pt-2">
            <Tooltip tip="Phase duration distribution.">
              <p className="mb-2 text-xs text-zinc-400">Duration Chart</p>
            </Tooltip>
            <AreaChart
              data={chartData}
              index="phase"
              categories={['Duration (ms)']}
              colors={['sky']}
              showAnimation={false}
              className="h-24"
              yAxisWidth={40}
            />
          </div>
        )}
      </div>
    </PanelShell>
  );
}
