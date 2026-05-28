'use client';

import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { StatusBarSettingsPanel } from '@/components/settings/StatusBarSettingsPanel';

export default function SettingsPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Settings</h1>
      <div className="space-y-6">
        <StatusBarSettingsPanel />
        <SettingsPanel />
      </div>
    </div>
  );
}
