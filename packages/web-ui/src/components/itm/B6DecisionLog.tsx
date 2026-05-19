'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { DecisionsMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';
import { Badge, ProgressBar } from '@tremor/react';

interface Props {
  wsBaseUrl: string;
}

const ACTION_COLOR: Record<string, string> = {
  ENTER_LONG: 'emerald',
  ENTER_SHORT: 'red',
  EXIT: 'amber',
  HOLD: 'zinc',
};

const ACTION_TIPS: Record<string, string> = {
  ENTER_LONG: 'Strategy decided to open a new long position.',
  ENTER_SHORT: 'Strategy decided to open a new short position.',
  EXIT: 'Strategy decided to close the current position.',
  HOLD: 'Strategy decided to take no action this cycle.',
};

export function B6DecisionLog({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<DecisionsMessage>(`${wsBaseUrl}/ws/decisions`);

  if (!data) {
    return (
      <PanelShell
        title="B6 · Decision Log"
        subtitle="DecisionMade stream (SHAP nullable)"
        status={status}
        className="h-full"
      >
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Awaiting decision stream…</p>
      </PanelShell>
    );
  }

  return (
    <PanelShell
      title="B6 · Decision Log"
      subtitle="DecisionMade stream (SHAP nullable)"
      status={status}
      className="h-full"
    >
      {data.decisions.length === 0 ? (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No decisions recorded yet.</p>
      ) : (
        <div className="space-y-2 overflow-y-auto max-h-96">
          {[...data.decisions].reverse().map((dec) => (
            <div key={dec.id} className="rounded-lg p-3 space-y-2" style={{ border: '1px solid var(--border)', background: 'color-mix(in srgb, var(--surface-card) 30%, transparent)' }}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Tooltip tip={ACTION_TIPS[dec.action] ?? 'Trading decision action.'}>
                    <Badge color={ACTION_COLOR[dec.action] ?? 'zinc'} className="w-fit flex-shrink-0">
                      {dec.action}
                    </Badge>
                  </Tooltip>
                  <Tooltip tip="Trading instrument this decision was made for.">
                    <span className="text-xs font-mono truncate" style={{ color: 'var(--text-secondary)' }}>{dec.instrument_id}</span>
                  </Tooltip>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                  <Tooltip tip="Decision cycle index.">
                    <span>#{dec.cycle_number}</span>
                  </Tooltip>
                  <Tooltip tip="ISO-8601 timestamp when the decision was emitted.">
                    <span>{new Date(dec.decided_at).toISOString().slice(11, 19)} UTC</span>
                  </Tooltip>
                </div>
              </div>

              <div>
                <Tooltip tip="Model confidence score (0–1). Values closer to 1.0 indicate higher conviction.">
                  <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Confidence</p>
                </Tooltip>
                <ProgressBar value={dec.confidence * 100} color="violet" className="mb-1" />
                <p className="text-xs font-mono text-right" style={{ color: 'var(--text-secondary)' }}>{(dec.confidence * 100).toFixed(1)}%</p>
              </div>

              <Tooltip tip="Human-readable rationale produced by the decision engine for this cycle.">
                <p className="text-xs italic" style={{ color: 'var(--text-secondary)' }}>{dec.rationale}</p>
              </Tooltip>

              {dec.shap_values && dec.shap_values.length > 0 && (
                <details className="group">
                  <summary className="cursor-pointer text-xs transition-colors" style={{ color: 'var(--text-muted)' }}>
                    SHAP values ({dec.shap_values.length} features)
                  </summary>
                  <div className="mt-2 space-y-1.5">
                    {dec.shap_values
                      .slice()
                      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                      .slice(0, 8)
                      .map((sv) => {
                        const pct = Math.min(Math.abs(sv.value) * 100, 100);
                        const color = sv.value > 0 ? 'emerald' : 'red';
                        return (
                          <div key={sv.feature} className="flex items-center gap-2 text-xs">
                            <Tooltip
                              tip={`SHAP value for feature "${sv.feature}": ${sv.value.toFixed(4)}. Positive = pushes toward current action; negative = pushes away.`}
                            >
                              <span className="w-32 truncate" style={{ color: 'var(--text-muted)' }}>{sv.feature}</span>
                            </Tooltip>
                            <ProgressBar value={pct} color={color} className="flex-1" />
                            <span className="font-mono w-16 text-right" style={{ color: 'var(--text-secondary)' }}>{sv.value.toFixed(4)}</span>
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
