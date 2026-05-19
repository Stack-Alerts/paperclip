'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { SignalsMessage } from '@/types/itm';
import { PanelShell } from './PanelShell';
import { Tooltip } from './Tooltip';
import { Badge, ProgressBar } from '@tremor/react';

interface Props {
  wsBaseUrl: string;
}

function directionColor(dir: string) {
  if (dir === 'LONG') return 'emerald';
  if (dir === 'SHORT') return 'red';
  return 'zinc';
}

export function B4SignalPanel({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<SignalsMessage>(`${wsBaseUrl}/ws/signals`);

  if (!data) {
    return (
      <PanelShell
        title="B4 · Signal Panel"
        subtitle="Live signal feed"
        status={status}
        className="h-full"
      >
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Awaiting signal data…</p>
      </PanelShell>
    );
  }

  return (
    <PanelShell
      title="B4 · Signal Panel"
      subtitle="Live signal feed"
      status={status}
      className="h-full"
    >
      {data.signals.length === 0 ? (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No active signals.</p>
      ) : (
        <div className="space-y-3">
          {data.signals.map((sig) => (
            <div key={sig.id} className="rounded-lg p-3 space-y-2" style={{ border: '1px solid var(--border)', background: 'color-mix(in srgb, var(--surface-card) 30%, transparent)' }}>
              <div className="flex items-center justify-between">
                <Tooltip tip="Trading instrument this signal applies to.">
                  <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{sig.instrument_id}</span>
                </Tooltip>
                <Tooltip tip="LONG = bullish; SHORT = bearish; FLAT = no directional bias.">
                  <Badge color={directionColor(sig.direction)} className="w-fit">
                    {sig.direction}
                  </Badge>
                </Tooltip>
              </div>

              <div className="flex items-center justify-between">
                <Tooltip tip="Name of the generating model or ensemble component.">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{sig.model}</span>
                </Tooltip>
                <Tooltip tip="ISO-8601 timestamp when this signal was generated.">
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    {new Date(sig.generated_at).toISOString().slice(11, 19)} UTC
                  </span>
                </Tooltip>
              </div>

              <div>
                <Tooltip tip="Directional strength: +1.0 = maximum bullish, -1.0 = maximum bearish.">
                  <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Strength</p>
                </Tooltip>
                <ProgressBar
                  value={Math.abs(sig.strength) * 100}
                  color={sig.strength > 0 ? 'emerald' : sig.strength < 0 ? 'red' : 'zinc'}
                  className="mb-1"
                />
                <p className="text-xs font-mono text-right" style={{ color: 'var(--text-secondary)' }}>{(sig.strength * 100).toFixed(0)}%</p>
              </div>

              {Object.keys(sig.features).length > 0 && (
                <details className="group">
                  <summary className="cursor-pointer text-xs transition-colors" style={{ color: 'var(--text-muted)' }}>
                    Features ({Object.keys(sig.features).length})
                  </summary>
                  <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                    {Object.entries(sig.features)
                      .slice(0, 10)
                      .map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between">
                          <Tooltip tip={`Raw feature value for "${k}" used in model inference.`}>
                            <span className="truncate max-w-[80px]" style={{ color: 'var(--text-muted)' }}>{k}</span>
                          </Tooltip>
                          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{v.toFixed(4)}</span>
                        </div>
                      ))}
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
