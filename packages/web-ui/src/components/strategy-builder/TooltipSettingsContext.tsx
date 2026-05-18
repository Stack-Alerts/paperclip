'use client';

import { useCallback, useEffect, useState } from 'react';
import React from 'react';

const LS_KEY = 'sb_tooltip_settings';

export interface TooltipSettings {
  enabled: boolean;
  delayMs: number;
}

const DEFAULT: TooltipSettings = { enabled: true, delayMs: 350 };

// Module-level singleton — all useTooltipSettings() instances on the same page
// share one state object and update together. This avoids React Context hierarchy
// issues (provider not found, wrong tree position, etc.).
let _current: TooltipSettings = { ...DEFAULT };
const _subs = new Set<(s: TooltipSettings) => void>();

function _publish(next: TooltipSettings) {
  _current = next;
  try { localStorage.setItem(LS_KEY, JSON.stringify(next)); } catch {}
  _subs.forEach(fn => fn({ ...next }));
}

export function useTooltipSettings() {
  const [settings, setSettings] = useState<TooltipSettings>({ ..._current });

  useEffect(() => {
    // Hydrate from localStorage on first mount and broadcast to all instances.
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const loaded: TooltipSettings = { ...DEFAULT, ...JSON.parse(raw) };
        _current = loaded;
        _subs.forEach(fn => fn({ ...loaded }));
      }
    } catch {}

    _subs.add(setSettings);
    return () => { _subs.delete(setSettings); };
  }, []);

  const update = useCallback((patch: Partial<TooltipSettings>) => {
    _publish({ ..._current, ...patch });
  }, []);

  return { settings, update };
}

// Kept for backward-compat with page.tsx import — now a simple pass-through.
export function TooltipSettingsProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
