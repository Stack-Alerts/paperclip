'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { CycleMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';

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

  const phases = ['bar_close', 'feature_extraction', 'model_inference', 'decision'] as const;
  const totalMs = phases.reduce(
    (acc, p) => acc + (data?.phase_durations[p] ?? 0),
    0,
  );

  return (
    <PanelShell
      title="B1 · Decision Cycle Monitor"
      subtitle="Aggregate bar-close timing + current processing state"
      status={status}
      className="h-full"
    >
      {!data ? (
        <p className="text-xs text-zinc-500">Awaiting first cycle message…</p>
      ) : (
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

          <div className="flex items-center justify-between">
            <Tooltip tip="Elapsed time in the current phase (ms).">
              <span className="text-xs text-zinc-400">Elapsed</span>
            </Tooltip>
            <span className="text-sm font-mono text-zinc-200">{data.elapsed_ms} ms</span>
          </div>

          <div className="flex items-center justify-between">
            <Tooltip tip="Decision cycle index since strategy start.">
              <span className="text-xs text-zinc-400">Cycle #</span>
            </Tooltip>
            <span className="text-sm font-mono text-zinc-200">{data.cycle_number}</span>
          </div>

          <div className="flex items-center justify-between">
            <Tooltip tip="Timestamp of the triggering bar.">
              <span className="text-xs text-zinc-400">Bar Timestamp</span>
            </Tooltip>
            <span className="text-xs font-mono text-zinc-300">
              {new Date(data.bar_ts).toISOString().replace('T', ' ').slice(0, 19)} UTC
            </span>
          </div>

          <div>
            <Tooltip tip="Phase breakdown for the most-recently completed cycle.">
              <p className="mb-2 text-xs text-zinc-400">Phase Durations (last cycle)</p>
            </Tooltip>
            <div className="space-y-1.5">
              {phases.map((p) => {
                const ms = data.phase_durations[p] ?? 0;
                const pct = totalMs > 0 ? (ms / totalMs) * 100 : 0;
                return (
                  <div key={p} className="flex items-center gap-2">
                    <Tooltip tip={PHASE_TIPS[p]}>
                      <span className="w-36 text-xs text-zinc-400 truncate">
                        {PHASE_LABELS[p]}
                      </span>
                    </Tooltip>
                    <div className="flex-1 h-2 rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${PHASE_COLOR[p]}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-16 text-right text-xs font-mono text-zinc-300">
                      {ms} ms
                    </span>
                  </div>
                );
              })}
              <div className="flex items-center justify-end gap-2 pt-1 border-t border-zinc-800">
                <span className="text-xs text-zinc-500">Total</span>
                <span className="text-xs font-mono text-zinc-300">{totalMs} ms</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </PanelShell>
  );
}
