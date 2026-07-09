'use client';

// BTCAAAAA-39021 — Storybook harness for the institutional-grade Notes
// tooltip uplift on TradesPanel. State is locked; the page renders the
// TradesPanel with a fixed trade dataset (BULLISH_BREAKOUT entry + SL exit)
// and auto-hovers the Notes cell on mount so screenshots are byte-stable.
// NO data files, NO API calls, NO fetch — all fixtures are inlined.

import { useEffect, useRef } from 'react';
import { TradesPanel } from '@/components/backtest/trades/TradesPanel';
import type { Trade } from '@/lib/strategy-builder/types';

// Anchored to the BTC-39021 acceptance criteria: "Tooltip copy references real
// building blocks / metrics (not placeholder lorem)." The trade below uses
// the BULLISH_BREAKOUT entry signal (which maps to "Initial Balance Breakout",
// weight=30, category=PATTERNS) and an SL exit (which surfaces the RiskEnforcer
// STOP_LOSS_PCT=0.02 / DAILY_LOSS_LIMIT=$500 guard text in the Position section).
const SAMPLE_TRADES: Trade[] = [
  {
    id: '1',
    entryTime: '2026-03-15T08:00:00Z',
    exitTime: '2026-03-15T10:30:00Z',
    entryPrice: 62816.9,
    exitPrice: 61540.32,
    quantity: 0.0001,
    pnl: -127.66,
    pnlPercentage: -2.03,
    bars: 10,
    exitType: 'SL',
    side: 'SHORT',
    symbol: 'BTC.P/USDT',
    status: 'CLOSED',
    notes: 'Stop Loss Hit',
    entrySignals: ['BULLISH_BREAKOUT'],
    exitPercentage: 1,
  },
  {
    id: '2',
    entryTime: '2026-03-15T12:00:00Z',
    exitTime: '2026-03-15T15:30:00Z',
    entryPrice: 61400.0,
    exitPrice: 62150.0,
    quantity: 0.0001,
    pnl: 75.0,
    pnlPercentage: 1.22,
    bars: 14,
    exitType: 'TP1',
    side: 'LONG',
    symbol: 'BTC.P/USDT',
    status: 'CLOSED',
    notes: 'TP1 Hit',
    entrySignals: ['BULLISH_BREAKOUT'],
    exitPercentage: 1,
  },
  {
    id: '3',
    entryTime: '2026-03-16T09:00:00Z',
    exitTime: '2026-03-16T11:15:00Z',
    entryPrice: 62200.0,
    exitPrice: 61800.0,
    quantity: 0.0001,
    pnl: -40.0,
    pnlPercentage: -0.64,
    bars: 9,
    exitType: 'MAX_BARS',
    side: 'LONG',
    symbol: 'BTC.P/USDT',
    status: 'CLOSED',
    notes: 'Max Bars (time-based exit)',
    entrySignals: ['BULLISH_BREAKOUT'],
    exitPercentage: 1,
  },
];

export default function TradesPanelTooltipStorybookPage() {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <main
      ref={containerRef}
      style={{
        minHeight: '100vh',
        background: 'var(--app-bg)',
        color: 'var(--text-primary)',
        padding: '24px 32px',
      }}
    >
      <h1 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
        BTCAAAAA-39021 — Notes Tooltip (Institutional-Grade)
      </h1>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 24 }}>
        Hover the Notes column on row #1 (SL exit) or row #2 (TP1 exit) to
        see the 4-section tooltip: Exit / Entry Signals / Position / Result.
        BULLISH_BREAKOUT cites the building block (Initial Balance Breakout,
        weight=30, category=PATTERNS); SL cites the RiskEnforcer guard.
      </p>

      <div
        style={{
          border: '1px solid var(--border)',
          borderRadius: 8,
          overflow: 'hidden',
          background: 'var(--panel-bg)',
        }}
      >
        <TradesPanel trades={SAMPLE_TRADES} />
      </div>

      <NotesHoverProbe />
    </main>
  );
}

// Stamps data-btcte-notes-cell on the first Notes cell (col 13) and dispatches
// a synthetic mouseenter so RichTooltip mounts for the screenshot capture.
function NotesHoverProbe() {
  useEffect(() => {
    const tryStamp = () => {
      const cells = document.querySelectorAll('table tbody tr td');
      for (const cell of Array.from(cells)) {
        if (cell.getAttribute('data-btcte-notes-cell') === '1') continue;
        const text = cell.textContent ?? '';
        if (
          text.includes('Stop Loss Hit') ||
          text.includes('TP1 Hit') ||
          text.includes('Max Bars')
        ) {
          cell.setAttribute('data-btcte-notes-cell', '1');
          cell.dispatchEvent(
            new MouseEvent('mouseenter', { bubbles: true, cancelable: true })
          );
          cell.dispatchEvent(
            new MouseEvent('mouseover', { bubbles: true, cancelable: true })
          );
          return true;
        }
      }
      return false;
    };
    if (!tryStamp()) {
      const t = window.setTimeout(tryStamp, 200);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, []);
  return null;
}