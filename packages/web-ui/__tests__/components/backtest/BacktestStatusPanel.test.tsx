import React from 'react';
import { render, screen } from '@testing-library/react';
import { BacktestStatusPanel } from '@/components/backtest/status-panel';
import type { BacktestStatusMessage } from '@/lib/strategy-builder/types';

describe('BacktestStatusPanel', () => {
  it('renders the idle-state thick-client checklist when no logs and not running', () => {
    render(<BacktestStatusPanel logs={[]} isRunning={false} />);
    expect(screen.getByText(/Status updates will appear here when backtest starts/)).toBeInTheDocument();
    expect(screen.getByText(/Data loading progress from Unified Data Manager/)).toBeInTheDocument();
    expect(screen.getByText(/NautilusTrader initialization/)).toBeInTheDocument();
    expect(screen.getByText(/Bar aggregation status/)).toBeInTheDocument();
    expect(screen.getByText(/Hybrid data source routing \(LakeAPI \+ Binance\)/)).toBeInTheDocument();
    expect(screen.getByText(/Real-time processing updates/)).toBeInTheDocument();
    expect(screen.getByText(/All terminal output will be captured and displayed here/)).toBeInTheDocument();
    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('streams log lines and shows the running indicator when active', () => {
    const logs: BacktestStatusMessage[] = [
      { message: 'Loading bars from Binance…', level: 'SYSTEM', timestamp: '2026-06-03T10:15:23Z' },
      { message: 'Aggregating 1h bars', level: 'INFO', timestamp: '2026-06-03T10:15:24Z' },
    ];
    render(<BacktestStatusPanel logs={logs} isRunning={true} />);
    expect(screen.getByText('Running…')).toBeInTheDocument();
    expect(screen.getByText(/Loading bars from Binance/)).toBeInTheDocument();
    expect(screen.getByText(/Aggregating 1h bars/)).toBeInTheDocument();
    // Idle checklist should not be shown
    expect(screen.queryByText(/Status updates will appear here when backtest starts/)).toBeNull();
  });

  it('shows the last-run state once a run completes and logs remain', () => {
    const logs: BacktestStatusMessage[] = [
      { message: 'Backtest completed.', level: 'SYSTEM', timestamp: '2026-06-03T10:20:00Z' },
    ];
    render(<BacktestStatusPanel logs={logs} isRunning={false} />);
    expect(screen.getByText('Last run')).toBeInTheDocument();
    expect(screen.getByText(/Backtest completed/)).toBeInTheDocument();
  });
});
