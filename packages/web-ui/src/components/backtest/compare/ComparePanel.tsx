'use client';

export interface ComparePanelProps {
  disabled?: boolean;
}

export function ComparePanel(_props: ComparePanelProps = {}) {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      Compare panel — scaffold. Owned by WebUI: Test/Optimize — Compare.
    </div>
  );
}
