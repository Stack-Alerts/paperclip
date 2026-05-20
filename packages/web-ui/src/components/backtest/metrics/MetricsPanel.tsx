'use client';

export interface MetricsPanelProps {
  disabled?: boolean;
}

export function MetricsPanel(_props: MetricsPanelProps = {}) {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      Metrics panel — scaffold. Owned by WebUI: Test/Optimize — Metrics.
    </div>
  );
}
