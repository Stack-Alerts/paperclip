'use client';

import { LogViewerPanel } from '@/components/log-viewer/LogViewerPanel';

export default function LogViewerPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Log Viewer</h1>
      <LogViewerPanel />
    </div>
  );
}
