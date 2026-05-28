'use client';

import React, { useMemo } from 'react';
import { useStatus } from '@/contexts/StatusContext';

export function StatusBar() {
  const entries = useStatus();

  const displayEntry = useMemo(() => {
    if (entries.length === 0) return null;
    return entries[entries.length - 1];
  }, [entries]);

  const displayText = displayEntry?.text ?? 'Ready';

  return (
    <div className="h-6 border-t px-3 flex items-center flex-shrink-0 min-h-6" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{displayText}</span>
    </div>
  );
}
