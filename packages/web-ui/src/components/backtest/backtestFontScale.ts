'use client';

import { createContext, useContext } from 'react';

// ─── Backtest font scaling (BTCAAAAA-34264 → 34312 → 38790) ───────────────────
//
// The dialog header Aa−/Aa+ control drives a three-step scale (Compact / Normal
// / Large). Historically it only resized the Config-tab STATUS section text.
// BTCAAAAA-38790 extends it so the *small text data* on other tabs (e.g. the
// Metrics tab's Recent Runs cards) also responds — while section headers and the
// larger stat-card blocks keep their fixed sizes. `smallScale` is the multiplier
// consumers apply (via CSS zoom / font-size) to their small-text blocks only.
export type FontScale = 'Compact' | 'Normal' | 'Large';

export type BacktestFontSizes = {
  /** Status section monospace lines (the idle checklist / live event stream). */
  statusText: string;
  /** Status section "Status" header label. */
  statusLabel: string;
  /**
   * Multiplier for small-text data blocks that opt into the header control
   * (Recent Runs cards, stale-discovery note). 1 = current/default sizing.
   */
  smallScale: number;
};

export const FONT_SCALES: Record<FontScale, BacktestFontSizes> = {
  Compact: { statusText: '11px', statusLabel: '10px', smallScale: 0.9 },
  Normal: { statusText: '13px', statusLabel: '11px', smallScale: 1 },
  Large: { statusText: '14px', statusLabel: '12px', smallScale: 1.15 },
};

export const FONT_SCALE_ORDER: FontScale[] = ['Compact', 'Normal', 'Large'];

export const FONT_SCALE_STORAGE_KEY = 'backtestConfigDialog.fontScale';

export function readStoredFontScale(): FontScale {
  if (typeof window === 'undefined') return 'Normal';
  try {
    const raw = window.localStorage.getItem(FONT_SCALE_STORAGE_KEY);
    if (raw === 'Compact' || raw === 'Normal' || raw === 'Large') return raw;
  } catch {
    // localStorage may be unavailable (private mode, SSR hydration); fall back silently.
  }
  return 'Normal';
}

// Threaded via context so tab panels can read the active scale without prop
// drilling from the dialog root.
export const FontSizesContext = createContext<BacktestFontSizes>(FONT_SCALES.Normal);
export const useFontSizes = () => useContext(FontSizesContext);
