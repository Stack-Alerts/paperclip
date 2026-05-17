'use client';

import { useState, useCallback } from 'react';
import { AppLayout } from '@/components/shared/AppLayout';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import type { AppSettings } from '@/types';

const INITIAL_SETTINGS: AppSettings = {
  general: {
    theme: {
      key: 'theme',
      label: 'Theme',
      value: 'dark',
      type: 'select',
      options: [
        { label: 'Light', value: 'light' },
        { label: 'Dark', value: 'dark' },
      ],
    },
    autoSave: {
      key: 'autoSave',
      label: 'Auto Save',
      value: 'true',
      type: 'toggle',
      description: 'Automatically save settings and configurations',
    },
  },
  api: {
    nautilusApiUrl: {
      key: 'nautilusApiUrl',
      label: 'NautilusTrader API URL',
      value: 'http://localhost:8000',
      type: 'text',
      required: true,
    },
    timeout: {
      key: 'timeout',
      label: 'API Timeout (seconds)',
      value: '30',
      type: 'number',
    },
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(INITIAL_SETTINGS);

  const handleSave = useCallback((updated: AppSettings) => {
    setSettings(updated);
  }, []);

  return (
    <AppLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Settings</h2>
          <p className="text-gray-600 mt-1">Configure application and API settings</p>
        </div>
        <SettingsPanel settings={settings} onSave={handleSave} />
      </div>
    </AppLayout>
  );
}
