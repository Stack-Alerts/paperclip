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
        <p className="text-xs text-zinc-500">Awaiting signal data…</p>
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
        <p className="text-xs text-zinc-500">No active signals.</p>
      ) : (
        <div className="space-y-3">
          {data.signals.map((sig) => (
            <div key={sig.id} className="rounded-lg border border-zinc-800 bg-zinc-800/30 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Tooltip tip="Trading instrument this signal applies to.">
                  <span className="text-xs font-mono text-zinc-200">{sig.instrument_id}</span>
                </Tooltip>
                <Tooltip tip="LONG = bullish; SHORT = bearish; FLAT = no directional bias.">
                  <Badge color={directionColor(sig.direction)} className="w-fit">
                    {sig.direction}
                  </Badge>
                </Tooltip>
              </div>

              <div className="flex items-center justify-between">
                <Tooltip tip="Name of the generating model or ensemble component.">
                  <span className="text-xs text-zinc-500">{sig.model}</span>
                </Tooltip>
                <Tooltip tip="ISO-8601 timestamp when this signal was generated.">
                  <span className="text-xs text-zinc-500 font-mono">
                    {new Date(sig.generated_at).toISOString().slice(11, 19)} UTC
                  </span>
                </Tooltip>
              </div>

              <div>
                <Tooltip tip="Directional strength: +1.0 = maximum bullish, -1.0 = maximum bearish.">
                  <p className="text-xs text-zinc-500 mb-1">Strength</p>
                </Tooltip>
                <ProgressBar
                  value={Math.abs(sig.strength) * 100}
                  color={sig.strength > 0 ? 'emerald' : sig.strength < 0 ? 'red' : 'zinc'}
                  className="mb-1"
                />
                <p className="text-xs font-mono text-zinc-300 text-right">{(sig.strength * 100).toFixed(0)}%</p>
              </div>

              {Object.keys(sig.features).length > 0 && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                    Features ({Object.keys(sig.features).length})
                  </summary>
                  <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                    {Object.entries(sig.features)
                      .slice(0, 10)
                      .map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between">
                          <Tooltip tip={`Raw feature value for "${k}" used in model inference.`}>
                            <span className="text-zinc-500 truncate max-w-[80px]">{k}</span>
                          </Tooltip>
                          <span className="font-mono text-zinc-300">{v.toFixed(4)}</span>
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
