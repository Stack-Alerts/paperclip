import React from 'react';
import { render, screen } from '@testing-library/react';
import { LiveOutputPanel } from '@/components/backtest/live-output/LiveOutputPanel';
import type { BacktestResult, BacktestStatusMessage } from '@/lib/strategy-builder/types';

function makeResult(overrides: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: 'r1',
    strategyId: 's1',
    runId: 'r1',
    status: 'completed',
    startDate: '2026-01-01',
    endDate: '2026-02-01',
    initialCapital: 10000,
    finalCapital: 11000,
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalReturn: 0,
    returnPercentage: 0,
    maxDrawdown: 0,
    sharpeRatio: 0,
    sortino_ratio: 0,
    profitFactor: 0,
    averageWin: 0,
    averageLoss: 0,
    trades: [],
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

// Cycle-13 board revision 2026-06-03: the idle Status checklist lives on
// the Config tab; Live Output keeps its separate streaming role + run
// counters. These tests lock that contract.
describe('LiveOutputPanel — streaming output + run counters (cycle-13)', () => {
  it('shows the natural "no output yet" placeholder when idle (no idle checklist)', () => {
    render(<LiveOutputPanel logs={[]} isRunning={false} />);
    expect(screen.getByText(/No output yet/)).toBeInTheDocument();
    // The thick-client checklist must NOT render here — it now lives on the
    // Config tab as the StatusColumn right rail.
    expect(screen.queryByText(/Status updates will appear here when backtest starts/)).toBeNull();
    expect(screen.queryByText(/Data loading progress from Unified Data Manager/)).toBeNull();
  });

  it('tallies TP/SL adjustments from completed trades in the header counter row', () => {
    const result = makeResult({
      totalTrades: 4,
      trades: [
        { id: 't1', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP1' },
        { id: 't2', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP2' },
        { id: 't3', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'SL' },
        { id: 't4', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'SL' },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    expect(screen.getByText('(TP1: 1, TP2: 1, TP3: 0, SL: 2)')).toBeInTheDocument();
  });

  it('streams log lines when active', () => {
    const logs: BacktestStatusMessage[] = [
      { message: 'Loading bars from Binance…', level: 'SYSTEM', timestamp: '2026-06-03T10:15:23Z' },
    ];
    render(<LiveOutputPanel logs={logs} isRunning={true} />);
    expect(screen.getByText(/Loading bars from Binance/)).toBeInTheDocument();
    expect(screen.getByText(/RUNNING/)).toBeInTheDocument();
  });
});

// BTCAAAAA-33591 cycle-33: per-trade synthesis safety net (frontend side).
// The backend now emits ORDER / FILL / POSITION / PERFORMANCE lines for each
// trade (src/api/app.py), but when the panel is fed a result whose trades
// are not yet represented in `logs` (e.g. result arrived via a separate
// poll and the engine's messages list was empty for that pass), the panel
// synthesizes the thick-client-equivalent line set locally so the web log
// has the same density the board is asking for.
describe('LiveOutputPanel — per-trade synthesis (cycle-33, BTCAAAAA-33591)', () => {
  it('synthesizes ORDER / FILL / POSITION / PERFORMANCE lines from a result with trades', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't1',
          entryTime: '2026-01-01T10:00:00Z',
          exitTime: '2026-01-01T11:00:00Z',
          entryPrice: 100,
          exitPrice: 110,
          quantity: 1,
          pnl: 10,
          pnlPercentage: 10,
          bars: 4,
          exitType: 'TP1',
          side: 'LONG',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    // ORDER line for trade #1
    expect(screen.getByText(/ORDER #1:.*LONG.*1.*BTC\.P\/USDT.*BUY @ 100\.00/)).toBeInTheDocument();
    // BUY FILL line
    expect(screen.getByText(/BUY FILL #1:.*1.*BTC\.P\/USDT @ 100\.00/)).toBeInTheDocument();
    // POSITION OPEN line
    expect(screen.getByText(/POSITION OPEN #1:.*LONG.*1.*BTC\.P\/USDT @ 100\.00 \| bars=4/)).toBeInTheDocument();
    // PERFORMANCE line
    expect(screen.getByText(/PERFORMANCE #1:.*WIN.*TP1.*110\.00.*Total PnL: \$10\.00.*10\.00%.*bars=4/)).toBeInTheDocument();
  });

  it('renders SELL FILL (not BUY FILL) for SHORT trades', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't2',
          entryTime: '2026-01-01T10:00:00Z',
          exitTime: '2026-01-01T11:00:00Z',
          entryPrice: 100,
          exitPrice: 90,
          quantity: 1,
          pnl: -10,
          pnlPercentage: -10,
          bars: 4,
          exitType: 'SL',
          side: 'SHORT',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    expect(screen.getByText(/SELL FILL #1:.*1.*BTC\.P\/USDT @ 100\.00/)).toBeInTheDocument();
    // BUY FILL must NOT be present for a SHORT
    expect(screen.queryByText(/BUY FILL #1:/)).toBeNull();
    expect(screen.getByText(/PERFORMANCE #1:.*LOSS/)).toBeInTheDocument();
  });

  it('skips synthesis when the backend log already covers each trade (Entry/Exit present)', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't3',
          entryTime: '',
          exitTime: '',
          entryPrice: 100,
          exitPrice: 110,
          quantity: 1,
          pnl: 10,
          pnlPercentage: 10,
          bars: 4,
          exitType: 'TP1',
          side: 'LONG',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    // Backend log already has Entry #1 / Exit #1 — the panel should NOT
    // append synthesized ORDER / FILL / POSITION / PERFORMANCE lines.
    const logs: BacktestStatusMessage[] = [
      { message: 'Entry #1: LONG @ 100.00', level: 'INFO', timestamp: '2026-01-01T10:00:00Z' },
      { message: 'Exit #1: WIN | TP1 @ 110.00 | PnL: $10.00 (10.00%) | Bars: 4', level: 'INFO', timestamp: '2026-01-01T11:00:00Z' },
    ];
    render(<LiveOutputPanel logs={logs} isRunning={false} result={result} />);
    expect(screen.queryByText(/ORDER #1:/)).toBeNull();
    expect(screen.queryByText(/BUY FILL #1:/)).toBeNull();
    expect(screen.queryByText(/POSITION OPEN #1:/)).toBeNull();
    expect(screen.queryByText(/PERFORMANCE #1:/)).toBeNull();
  });
});
