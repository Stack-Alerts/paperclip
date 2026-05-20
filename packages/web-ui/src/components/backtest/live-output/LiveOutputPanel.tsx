'use client';

export interface LiveOutputPanelProps {
  disabled?: boolean;
}

export function LiveOutputPanel(_props: LiveOutputPanelProps = {}) {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      Live Output panel — scaffold. Owned by WebUI: Test/Optimize — Live Output.
    </div>
  );
}
