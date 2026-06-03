import React from 'react';
import { render, screen } from '@testing-library/react';
import { BacktestProgressMeter } from '@/components/backtest/progress-meter';

describe('BacktestProgressMeter (slim bar — board revision 2026-06-03)', () => {
  it('renders only a slim bar with inline % when no candle count is provided', () => {
    render(<BacktestProgressMeter progress={0} isRunning={false} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
    expect(screen.getByText('0%')).toBeInTheDocument();
    // No "PROGRESS" header, no Status section, no TP/SL counter row — board
    // explicitly rejected the framed widget. Confirm the chrome is gone.
    expect(screen.queryByText('Progress')).toBeNull();
    expect(screen.queryByText(/TP\/SL Adjustments/)).toBeNull();
    expect(screen.queryByText(/Candles:/)).toBeNull();
  });

  it('updates the bar fill and the inline percentage when running', () => {
    render(<BacktestProgressMeter progress={42} isRunning={true} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('shows a candle count instead of the percentage when caller supplies one', () => {
    render(
      <BacktestProgressMeter
        progress={50}
        isRunning={true}
        candles={{ current: 1234, total: 2500 }}
      />,
    );
    expect(screen.getByText('1,234 / 2,500')).toBeInTheDocument();
    // Percentage label suppressed when the more specific candle count is shown.
    expect(screen.queryByText('50%')).toBeNull();
  });

  it('clamps the bar between 0 and 100', () => {
    const { rerender } = render(<BacktestProgressMeter progress={-10} isRunning={false} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    rerender(<BacktestProgressMeter progress={150} isRunning={true} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });
});
