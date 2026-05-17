'use client';

import { SettingsPanel } from '@/components/settings/SettingsPanel';

export default function SettingsPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-zinc-950">
      <h1 className="text-xl font-semibold text-zinc-100 mb-6">Settings</h1>
      <SettingsPanel />
    </div>
  );
}
