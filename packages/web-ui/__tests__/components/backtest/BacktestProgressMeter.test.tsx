import React from 'react';
import { render, screen } from '@testing-library/react';
import { BacktestProgressMeter } from '@/components/backtest/progress-meter';
import type { BacktestResult } from '@/lib/strategy-builder/types';

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

describe('BacktestProgressMeter', () => {
  it('renders the thick-client idle layout with zeroed counters when no run is active', () => {
    render(<BacktestProgressMeter progress={0} isRunning={false} />);
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    // Candles "0 / 0", Trades "0", TP/SL Adjustments "0 (TP1: 0, TP2: 0, TP3: 0, SL: 0)"
    expect(screen.getByText(/Candles:/)).toBeInTheDocument();
    expect(screen.getByText('0 / 0')).toBeInTheDocument();
    expect(screen.getByText(/Trades:/)).toBeInTheDocument();
    expect(screen.getByText(/TP\/SL Adjustments:/)).toBeInTheDocument();
    expect(screen.getByText('(TP1: 0, TP2: 0, TP3: 0, SL: 0)')).toBeInTheDocument();
  });

  it('reflects progress percentage and running indicator', () => {
    render(<BacktestProgressMeter progress={42} isRunning={true} />);
    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
  });

  it('tallies TP1/TP2/TP3/SL counters from completed trades', () => {
    const result = makeResult({
      totalTrades: 5,
      trades: [
        { id: 't1', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP1' },
        { id: 't2', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP1' },
        { id: 't3', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP2' },
        { id: 't4', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP3' },
        { id: 't5', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'SL' },
      ],
    });
    render(<BacktestProgressMeter progress={100} isRunning={false} result={result} />);
    expect(screen.getByText('(TP1: 2, TP2: 1, TP3: 1, SL: 1)')).toBeInTheDocument();
    // Both totalTrades and adjustment total are 5 here, so check that two
    // separate boldface counters render the value (one for Trades, one for
    // TP/SL Adjustments).
    expect(screen.getAllByText('5')).toHaveLength(2);
  });

  it('honors candle counter overrides when caller passes them', () => {
    render(
      <BacktestProgressMeter
        progress={50}
        isRunning={true}
        candles={{ current: 1234, total: 2500 }}
      />,
    );
    expect(screen.getByText('1,234 / 2,500')).toBeInTheDocument();
  });
});
