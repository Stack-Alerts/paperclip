'use client';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { AlertsMessage, AlertSeverity } from '@/types/itm';
import { Tooltip } from './Tooltip';
import type { WsStatus } from '@/hooks/useWebSocket';

const SEV_STYLE: Record<AlertSeverity, string> = {
  INFO: 'border-sky-700 bg-sky-900/30 text-sky-300',
  WARN: 'border-amber-600 bg-amber-900/30 text-amber-300',
  CRITICAL: 'border-red-600 bg-red-900/40 text-red-300 animate-pulse',
};

const SEV_ICON: Record<AlertSeverity, string> = {
  INFO: 'ℹ',
  WARN: '⚠',
  CRITICAL: '🔴',
};

const SEV_TIP: Record<AlertSeverity, string> = {
  INFO: 'Informational alert — no immediate action required.',
  WARN: 'Warning alert — monitor closely; may require intervention.',
  CRITICAL: 'Critical alert — immediate action required. Strategy may be halted.',
};

interface Props {
  wsBaseUrl: string;
}

export function B5AlertBanner({ wsBaseUrl }: Props) {
  const { data, status } = useWebSocket<AlertsMessage>(`${wsBaseUrl}/ws/alerts`);

  const active = data?.active_alerts.filter((a) => !a.acknowledged) ?? [];
  const hasCritical = active.some((a) => a.severity === 'CRITICAL');

  return (
    <div
      role="region"
      aria-label="B5 Alert Banner"
      aria-live="assertive"
      className="w-full rounded-xl px-4 py-3 transition-colors"
      style={hasCritical
        ? { border: '1px solid rgb(185 28 28)', background: 'rgba(69, 10, 10, 0.4)' }
        : { border: '1px solid var(--border)', background: 'var(--surface-panel)' }}
    >
      <div className="flex items-center justify-between mb-2">
        <Tooltip tip="Displays all non-acknowledged alerts from the strategy engine, ordered by severity.">
          <h2 className="text-sm font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>B5 · Alert Banner</h2>
        </Tooltip>
        <div className="flex items-center gap-2">
          <Tooltip tip="Number of unacknowledged active alerts.">
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{active.length} active</span>
          </Tooltip>
          <WsStatusMini status={status} />
        </div>
      </div>

      {active.length === 0 ? (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No active alerts.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {active.map((alert) => (
            <div
              key={alert.id}
              role="alert"
              className={`flex items-start gap-1.5 rounded-lg border px-3 py-2 text-xs ${SEV_STYLE[alert.severity]}`}
            >
              <Tooltip tip={SEV_TIP[alert.severity]}>
                <span aria-label={alert.severity}>{SEV_ICON[alert.severity]}</span>
              </Tooltip>
              <div>
                <Tooltip tip={`Source: ${alert.source} · Raised: ${new Date(alert.raised_at).toISOString().replace('T', ' ').slice(0, 19)} UTC`}>
                  <p className="font-medium">{alert.message}</p>
                </Tooltip>
                <p className="mt-0.5" style={{ color: 'var(--text-muted)' }}>{alert.source}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WsStatusMini({ status }: { status: WsStatus }) {
  const color = status === 'open' ? 'bg-emerald-400' : status === 'connecting' ? 'bg-yellow-400' : 'bg-red-500';
  return (
    <Tooltip tip={`WebSocket status: ${status}`}>
      <span className={`h-2 w-2 rounded-full ${color} inline-block`} />
    </Tooltip>
  );
}
