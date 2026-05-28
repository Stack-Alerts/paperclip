'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { statusBus } from '@/lib/status/StatusBus';
import type { StatusEntry, StatusBarSettings } from '@/lib/status/types';

interface StatusContextType {
  entries: StatusEntry[];
  settings: StatusBarSettings;
  updateSettings: (settings: Partial<StatusBarSettings>) => void;
}

const StatusContext = createContext<StatusContextType | undefined>(undefined);

export function StatusBarProvider({ children }: { children: React.ReactNode }) {
  const [entries, setEntries] = useState<StatusEntry[]>([]);
  const [settings, setSettings] = useState<StatusBarSettings>({ tickerMode: false });

  useEffect(() => {
    const unsubscribeEmit = statusBus.on('emit', (entry: StatusEntry) => {
      setEntries(prev => [...prev, entry]);
    });

    const unsubscribeUpdate = statusBus.on('update', ({ id, text }: { id: string; text: string }) => {
      setEntries(prev =>
        prev.map(e => (e.id === id ? { ...e, text } : e))
      );
    });

    const unsubscribeDismiss = statusBus.on('dismiss', ({ id }: { id: string }) => {
      setEntries(prev => prev.filter(e => e.id !== id));
    });

    const unsubscribeClear = statusBus.on('clear', () => {
      setEntries([]);
    });

    return () => {
      unsubscribeEmit();
      unsubscribeUpdate();
      unsubscribeDismiss();
      unsubscribeClear();
    };
  }, []);

  const updateSettings = (newSettings: Partial<StatusBarSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  return (
    <StatusContext.Provider value={{ entries, settings, updateSettings }}>
      {children}
    </StatusContext.Provider>
  );
}

export function useStatus() {
  const context = useContext(StatusContext);
  if (!context) {
    throw new Error('useStatus must be used within StatusBarProvider');
  }
  return context.entries;
}

export function useStatusSettings() {
  const context = useContext(StatusContext);
  if (!context) {
    throw new Error('useStatusSettings must be used within StatusBarProvider');
  }
  return {
    settings: context.settings,
    update: context.updateSettings,
  };
}
