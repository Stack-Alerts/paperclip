'use client';

export interface ConfigDiscoveryPanelProps {
  disabled?: boolean;
}

export function ConfigDiscoveryPanel() {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      Config Discovery panel — scaffold. Owned by WebUI: Test/Optimize — Config Discovery.
    </div>
  );
}
