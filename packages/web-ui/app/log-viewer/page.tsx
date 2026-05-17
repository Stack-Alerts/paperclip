'use client';

import { LogViewerPanel } from '@/components/log-viewer/LogViewerPanel';

export default function LogViewerPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-zinc-950">
      <h1 className="text-xl font-semibold text-zinc-100 mb-6">Log Viewer</h1>
      <LogViewerPanel />
    </div>
  );
}
