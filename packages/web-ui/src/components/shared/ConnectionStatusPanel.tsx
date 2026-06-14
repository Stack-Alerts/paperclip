'use client';

import { useBackendHealth } from '@/hooks/useBackendHealth';
import { useNextCandleCountdown } from '@/hooks/useNextCandleCountdown';

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

interface Props {
  collapsed: boolean;
}

export function ConnectionStatusPanel({ collapsed }: Props) {
  const { connectionState, health, error } = useBackendHealth();
  const candleSecondsLeft = useNextCandleCountdown();

  const isConnected = connectionState === 'connected';
  const isChecking = connectionState === 'checking';

  const dotColor = isConnected
    ? 'var(--status-connected)'
    : isChecking
    ? 'var(--text-muted)'
    : 'var(--color-red, #ef4444)';

  const labelColor = dotColor;
  const label = isConnected ? 'CONNECTED' : isChecking ? 'CHECKING…' : 'DISCONNECTED';

  if (collapsed) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
        <span
          title={label}
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: dotColor,
            display: 'inline-block',
          }}
        />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {/* Connection indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: dotColor,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontSize: 10,
            color: labelColor,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            fontWeight: 600,
          }}
        >
          {label}
        </span>
      </div>

      {/* Health details — only when connected */}
      {isConnected && health && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, paddingLeft: 13 }}>
          <StatusRow
            label="API"
            value={health.status === 'ok' ? 'OK' : 'DEGRADED'}
            valueColor={health.status === 'ok' ? 'var(--status-connected)' : 'var(--color-amber, #f59e0b)'}
          />
          <StatusRow
            label="Redis"
            value={health.redis ? 'OK' : 'DOWN'}
            valueColor={health.redis ? 'var(--status-connected)' : 'var(--color-red, #ef4444)'}
          />
          <StatusRow
            label="Uptime"
            value={formatUptime(health.uptime_seconds)}
          />
          {health.branch && (
            <StatusRow label="Branch" value={health.branch} mono />
          )}
        </div>
      )}

      {/* Error hint when disconnected */}
      {!isConnected && !isChecking && error && (
        <div
          style={{
            fontSize: 9,
            color: 'var(--text-muted)',
            paddingLeft: 13,
            wordBreak: 'break-word',
          }}
        >
          {error.length > 40 ? error.slice(0, 40) + '…' : error}
        </div>
      )}

      {/* Candle countdown — always visible */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          paddingLeft: 13,
          marginTop: 2,
        }}
      >
        <span style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
          Next candle
        </span>
        <span
          suppressHydrationWarning
          style={{
            fontSize: 10,
            color: 'var(--text-primary)',
            fontVariantNumeric: 'tabular-nums',
            fontFamily: 'monospace',
          }}
        >
          {formatCountdown(candleSecondsLeft)}
        </span>
      </div>
    </div>
  );
}

function StatusRow({
  label,
  value,
  valueColor,
  mono,
}: {
  label: string;
  value: string;
  valueColor?: string;
  mono?: boolean;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 9, color: 'var(--text-muted)', minWidth: 36 }}>{label}</span>
      <span
        style={{
          fontSize: 9,
          color: valueColor ?? 'var(--text-primary)',
          fontFamily: mono ? 'monospace' : undefined,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 100,
        }}
      >
        {value}
      </span>
    </div>
  );
}
