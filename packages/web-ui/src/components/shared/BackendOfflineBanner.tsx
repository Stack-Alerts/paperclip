'use client';

import { useBackendHealth } from '@/hooks/useBackendHealth';

export function BackendOfflineBanner() {
  const { connectionState, error, lastChecked, recheck } = useBackendHealth();

  if (connectionState !== 'disconnected') return null;

  const hint = error
    ? error.length > 80
      ? error.slice(0, 80) + '…'
      : error
    : 'Backend unreachable';

  const lastCheckedStr = lastChecked
    ? lastChecked.toLocaleTimeString()
    : null;

  function retry() {
    // Trigger an immediate health probe via the shared hook. Avoids a full
    // page reload (which would wipe any in-flight UI state and add latency).
    void recheck();
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 16px',
        background: 'var(--color-red, #ef4444)',
        color: '#fff',
        fontSize: 13,
        fontWeight: 500,
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: '#fff',
          flexShrink: 0,
          opacity: 0.9,
        }}
      />
      <span style={{ flex: 1 }}>
        <strong>Backend offline</strong>
        {' — '}
        {hint}
        {lastCheckedStr && (
          <span style={{ opacity: 0.8, marginLeft: 8, fontSize: 11 }}>
            (last checked {lastCheckedStr})
          </span>
        )}
      </span>
      <button
        onClick={retry}
        style={{
          background: 'rgba(255,255,255,0.2)',
          border: '1px solid rgba(255,255,255,0.5)',
          borderRadius: 4,
          color: '#fff',
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 600,
          padding: '3px 10px',
          flexShrink: 0,
        }}
      >
        Retry
      </button>
    </div>
  );
}
