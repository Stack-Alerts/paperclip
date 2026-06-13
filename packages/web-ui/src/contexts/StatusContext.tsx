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

const DEFAULT_SETTINGS: StatusBarSettings = {
  tickerMode: false,
  maxVisible: 3,
  errorPersist: true,
  errorDuration: 10,
  successDuration: 4000,
  warningDuration: 6000,
};

export function StatusBarProvider({ children }: { children: React.ReactNode }) {
  const [entries, setEntries] = useState<StatusEntry[]>([]);
  const [settings, setSettings] = useState<StatusBarSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const stored = localStorage.getItem('status-bar-settings');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSettings(prev => ({ ...prev, ...parsed }));
      } catch {
        // Ignore parse errors
      }
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'status-bar-settings' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          setSettings(prev => ({ ...prev, ...parsed }));
        } catch {
          // Ignore parse errors
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

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

  useEffect(() => {
    if (!settings.tickerMode) return;

    const interval = setInterval(() => {
      const now = Date.now();
      setEntries(prev =>
        prev.filter(e => {
          if (e.pinned) return true;
          if (e.dismissed) return false;
          if (e.expiresAt && e.expiresAt <= now) return false;
          return true;
        })
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [settings.tickerMode]);

  const updateSettings = (newSettings: Partial<StatusBarSettings>) => {
    const updated = { ...settings, ...newSettings };
    setSettings(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('status-bar-settings', JSON.stringify(updated));
    }
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
