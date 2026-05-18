'use client';

import { useState } from 'react';
import { AppLayout } from '@/components/shared/AppLayout';
import { LogViewerPanel } from '@/components/log-viewer/LogViewerPanel';
import { LogLevel } from '@/types';
import type { LogEntry } from '@/types';

const INITIAL_LOGS: LogEntry[] = [
  { timestamp: new Date(), level: LogLevel.INFO, message: 'Application started successfully', source: 'System' },
  { timestamp: new Date(), level: LogLevel.INFO, message: 'NautilusTrader connection established', source: 'NautilusTrader' },
];

export default function LogViewerPage() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);

  return (
    <AppLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>Log Viewer</h2>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>Monitor system and strategy execution logs</p>
        </div>
        <LogViewerPanel logs={logs} onClear={() => setLogs([])} />
      </div>
    </AppLayout>
  );
}
