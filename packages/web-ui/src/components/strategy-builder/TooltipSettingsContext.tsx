'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

const LS_KEY = 'sb_tooltip_settings';

export interface TooltipSettings {
  enabled: boolean;
  delayMs: number;
}

const DEFAULT: TooltipSettings = { enabled: true, delayMs: 350 };

interface TooltipSettingsCtx {
  settings: TooltipSettings;
  update: (patch: Partial<TooltipSettings>) => void;
}

export const TooltipSettingsContext = createContext<TooltipSettingsCtx>({
  settings: DEFAULT,
  update: () => {},
});

export function useTooltipSettings(): TooltipSettingsCtx {
  return useContext(TooltipSettingsContext);
}

export function TooltipSettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<TooltipSettings>(DEFAULT);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) setSettings({ ...DEFAULT, ...JSON.parse(raw) });
    } catch {}
  }, []);

  const update = useCallback((patch: Partial<TooltipSettings>) => {
    setSettings(prev => {
      const next = { ...prev, ...patch };
      try { localStorage.setItem(LS_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  return (
    <TooltipSettingsContext.Provider value={{ settings, update }}>
      {children}
    </TooltipSettingsContext.Provider>
  );
}
