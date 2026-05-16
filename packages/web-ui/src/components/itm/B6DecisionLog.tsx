'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { DecisionsMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';

interface Props {
  wsBaseUrl: string;
}

const ACTION_STYLE: Record<string, string> = {
  ENTER_LONG: 'bg-emerald-900/50 text-emerald-400',
  ENTER_SHORT: 'bg-red-900/50 text-red-400',
  EXIT: 'bg-amber-900/50 text-amber-400',
  HOLD: 'bg-zinc-800 text-zinc-400',
};

const ACTION_TIPS: Record<string, string> = {
  ENTER_LONG: 'Strategy decided to open a new long position.',
  ENTER_SHORT: 'Strategy decided to open a new short position.',
  EXIT: 'Strategy decided to close the current position.',
  HOLD: 'Strategy decided to take no action this cycle.',
};

export function B6DecisionLog({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<DecisionsMessage>(`${wsBaseUrl}/ws/decisions`);

  return (
    <PanelShell
      title="B6 · Decision Log"
      subtitle="DecisionMade stream (SHAP nullable)"
      status={status}
      className="h-full"
    >
      {!data ? (
        <p className="text-xs text-zinc-500">Awaiting decision stream…</p>
      ) : data.decisions.length === 0 ? (
        <p className="text-xs text-zinc-500">No decisions recorded yet.</p>
      ) : (
        <div className="space-y-2 overflow-y-auto max-h-96">
          {[...data.decisions].reverse().map((dec) => (
            <div
              key={dec.id}
              className="rounded-lg border border-zinc-800 bg-zinc-800/30 p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Tooltip tip={ACTION_TIPS[dec.action] ?? 'Trading decision action.'}>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${ACTION_STYLE[dec.action] ?? 'text-zinc-400'}`}>
                      {dec.action}
                    </span>
                  </Tooltip>
                  <Tooltip tip="Trading instrument this decision was made for.">
                    <span className="text-xs font-mono text-zinc-300">{dec.instrument_id}</span>
                  </Tooltip>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono">
                  <Tooltip tip="Decision cycle index.">
                    <span>#{dec.cycle_number}</span>
                  </Tooltip>
                  <Tooltip tip="ISO-8601 timestamp when the decision was emitted.">
                    <span>{new Date(dec.decided_at).toISOString().slice(11, 19)} UTC</span>
                  </Tooltip>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Tooltip tip="Model confidence score (0–1). Values closer to 1.0 indicate higher conviction.">
                  <span className="text-xs text-zinc-500">Confidence</span>
                </Tooltip>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-violet-500 transition-all duration-300"
                      style={{ width: `${dec.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-zinc-300">
                    {(dec.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <Tooltip tip="Human-readable rationale produced by the decision engine for this cycle.">
                <p className="text-xs text-zinc-400 italic">{dec.rationale}</p>
              </Tooltip>

              {dec.shap_values && dec.shap_values.length > 0 && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                    SHAP values ({dec.shap_values.length} features)
                  </summary>
                  <div className="mt-1.5 space-y-1">
                    {dec.shap_values
                      .slice()
                      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                      .slice(0, 8)
                      .map((sv) => {
                        const pct = Math.min(Math.abs(sv.value) * 100, 100);
                        const color = sv.value > 0 ? 'bg-emerald-500' : 'bg-red-500';
                        return (
                          <div key={sv.feature} className="flex items-center gap-2">
                            <Tooltip
                              tip={`SHAP value for feature "${sv.feature}": ${sv.value.toFixed(4)}. Positive = pushes toward current action; negative = pushes away.`}
                            >
                              <span className="w-32 text-xs text-zinc-500 truncate">{sv.feature}</span>
                            </Tooltip>
                            <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${color} transition-all duration-300`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono text-zinc-300 w-16 text-right">
                              {sv.value.toFixed(4)}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </PanelShell>
  );
}
