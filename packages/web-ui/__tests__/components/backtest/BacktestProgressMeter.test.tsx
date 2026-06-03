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

describe('BacktestProgressMeter (cycle-12 inline-status row)', () => {
  it('idle state: shows `Idle` word, bar at 0%, and 0% inline', () => {
    render(<BacktestProgressMeter progress={0} isRunning={false} />);
    expect(screen.getByText('Idle')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    // No chrome: no "PROGRESS" header, no Status panel, no TP/SL counter row.
    // The detailed checklist + event stream live in Live Output now.
    expect(screen.queryByText('Progress')).toBeNull();
    expect(screen.queryByText(/TP\/SL Adjustments/)).toBeNull();
  });

  it('running state: shows `Running`, the active percentage, and a trade count', () => {
    const result = makeResult({ totalTrades: 7, trades: [] });
    render(<BacktestProgressMeter progress={42} isRunning={true} result={result} />);
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(screen.getByText('Trades 7')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
  });

  it('complete state: shows `Complete` with the final trade count and bar at 100%', () => {
    const result = makeResult({ totalTrades: 12 });
    render(<BacktestProgressMeter progress={100} isRunning={false} result={result} />);
    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('Trades 12')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('renders inline candle count next to the status word when caller supplies one', () => {
    render(
      <BacktestProgressMeter
        progress={50}
        isRunning={true}
        candles={{ current: 1234, total: 2500 }}
      />,
    );
    expect(screen.getByText('1,234 / 2,500')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('clamps the bar between 0 and 100', () => {
    const { rerender } = render(<BacktestProgressMeter progress={-10} isRunning={false} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    rerender(<BacktestProgressMeter progress={150} isRunning={true} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });
});
