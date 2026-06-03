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
