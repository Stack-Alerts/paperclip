'use client';

import { GeneralSettingsPanel } from '@/components/settings/GeneralSettingsPanel';
import { StatusBarSettingsPanel } from '@/components/settings/StatusBarSettingsPanel';
import { WindowBreadcrumb } from '@/components/shared/WindowBreadcrumb';

export default function SettingsPage() {
  return (
    <>
      <div
        className="flex items-center border-b px-3 py-1.5 flex-shrink-0"
        style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}
      >
        <WindowBreadcrumb page="Settings" />
      </div>
      <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
        <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Settings</h1>
        <div className="space-y-6">
          <GeneralSettingsPanel />
          <StatusBarSettingsPanel />
        </div>
      </div>
    </>
  );
}
