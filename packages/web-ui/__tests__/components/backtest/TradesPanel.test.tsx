import React from 'react';
import { render, screen } from '@testing-library/react';
import { TradesPanel } from '@/components/backtest/trades/TradesPanel';
import type { Trade } from '@/lib/strategy-builder/types';

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: '1.1',
    entryTime: '2026-03-15T08:00:00Z',
    exitTime: '2026-03-15T10:30:00Z',
    entryPrice: 62816.9,
    exitPrice: 61540.32,
    quantity: 0.0001,
    pnl: 203.22,
    pnlPercentage: 2.03,
    bars: 10,
    exitType: 'SL',
    side: 'SHORT',
    symbol: 'BTC.P/USDT',
    status: 'CLOSED',
    ...overrides,
  };
}

describe('TradesPanel — BTCAAAAA-36001 date display', () => {
  it('renders a Date/Time column header instead of the legacy Time header', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    expect(screen.getByRole('columnheader', { name: /Date\/Time/i })).toBeInTheDocument();
  });

  it('shows both the calendar date and the time for a trade', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    // entryTime is "2026-03-15T08:00:00Z". Whatever the test-runner timezone, the
    // formatter uses local getMonth/getDate, so we assert the *displayed* date
    // by reading it back from the rendered <td>.
    const cell = screen.getByTitle('2026-03-15T08:00:00Z');
    expect(cell).toBeInTheDocument();
    // Cell text must contain a slash-separated date and an HH:MM:SS time.
    expect(cell.textContent).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}/);
  });

  it('exposes the full ISO entryTime as a title attribute on the cell', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    expect(screen.getByTitle('2026-03-15T08:00:00Z')).toBeInTheDocument();
  });

  it('renders the em-dash placeholder when entryTime is empty', () => {
    const trade = makeTrade({ entryTime: '' });
    const { container } = render(<TradesPanel trades={[trade]} />);
    const tds = container.querySelectorAll('tbody td');
    // 2nd cell is the time cell (index 1).
    expect(tds[1]?.textContent).toBe('—');
  });
});
