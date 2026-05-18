'use client';

import { useCallback, useEffect, useState } from 'react';
import React from 'react';

const LS_KEY = 'app_theme';
export type ThemeName = 'dark' | 'ocean';

const DEFAULT_THEME: ThemeName = 'dark';

let _current: ThemeName = DEFAULT_THEME;
const _subs = new Set<(t: ThemeName) => void>();

function _applyTheme(name: ThemeName) {
  _current = name;
  try { localStorage.setItem(LS_KEY, name); } catch {}
  try { document.documentElement.setAttribute('data-theme', name); } catch {}
  _subs.forEach(fn => fn(name));
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemeName>(_current);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(LS_KEY) as ThemeName | null;
      if (saved === 'dark' || saved === 'ocean') {
        _applyTheme(saved);
      } else {
        try { document.documentElement.setAttribute('data-theme', _current); } catch {}
      }
    } catch {}

    _subs.add(setTheme);
    return () => { _subs.delete(setTheme); };
  }, []);

  const set = useCallback((name: ThemeName) => { _applyTheme(name); }, []);

  return { theme, setTheme: set };
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    try {
      const saved = localStorage.getItem(LS_KEY) as ThemeName | null;
      const name: ThemeName = (saved === 'dark' || saved === 'ocean') ? saved : DEFAULT_THEME;
      _current = name;
      document.documentElement.setAttribute('data-theme', name);
    } catch {}
  }, []);

  return <>{children}</>;
}
