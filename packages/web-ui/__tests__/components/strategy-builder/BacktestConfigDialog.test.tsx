/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BacktestConfigDialog } from '@/components/strategy-builder/BacktestConfigDialog';
import { Providers } from '@/components/strategy-builder/Providers';
import { StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/strategy-builder/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const mockStrategy = {
  id: 'strat-1',
  name: 'Test',
  status: StrategyStatus.DRAFT,
  blocks: [],
  settings: { timeframe: '1h' },
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

const defaultStore = {
  currentStrategy: mockStrategy,
  runBacktest: jest.fn().mockResolvedValue({}),
  backTestInProgress: false,
  backTestProgress: 0,
  backTestResult: null,
};

function renderDialog(open = true, onClose = jest.fn()) {
  mockStore.mockReturnValue(defaultStore as any);
  return { onClose, ...render(
    <Providers tooltips={{}}>
      <BacktestConfigDialog open={open} onClose={onClose} />
    </Providers>
  )};
}

describe('BacktestConfigDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders nothing when closed', () => {
    renderDialog(false);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    renderDialog();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Backtest Configuration/)).toBeInTheDocument();
  });

  it('shows chip rows for Lookback, Training, Testing with preset day buttons', () => {
    renderDialog();
    // Chip text is the bare number (thick-client parity); the unit is shown on the spinbox.
    const thirtyButtons = screen.getAllByRole('button', { name: '30' });
    const ninetyButtons = screen.getAllByRole('button', { name: '90' });
    expect(thirtyButtons.length).toBeGreaterThanOrEqual(1);
    expect(ninetyButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('shows 3-column structure: Configuration, Adaptive SL v2.0, Risk/Reward', () => {
    renderDialog();
    // Column headers — use getAllByText to handle 'Configuration' appearing in header+title
    expect(screen.getAllByText(/Configuration/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Adaptive SL v2\.0/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Risk \/ Reward/i).length).toBeGreaterThanOrEqual(1);
  });

  it('calls runBacktest on Run Test click', async () => {
    renderDialog();
    fireEvent.click(screen.getByRole('button', { name: /Run Test/ }));
    await waitFor(() => {
      expect(defaultStore.runBacktest).toHaveBeenCalledWith(
        expect.objectContaining({ strategyId: 'strat-1' }),
      );
    });
  });

  it('shows Running button and disables it when backtest is in progress', () => {
    mockStore.mockReturnValue({ ...defaultStore, backTestInProgress: true } as any);
    render(
      <Providers tooltips={{}}>
        <BacktestConfigDialog open onClose={jest.fn()} />
      </Providers>
    );
    // Find the "Running…" button in the footer (not any status text elsewhere)
    const runningBtns = screen.getAllByText(/Running/);
    const runningBtn = runningBtns.find(el => el.closest('button'));
    expect(runningBtn).toBeDefined();
    expect(runningBtn!.closest('button')).toBeDisabled();
  });

  it('shows progress bar when running', () => {
    mockStore.mockReturnValue({ ...defaultStore, backTestInProgress: true, backTestProgress: 42 } as any);
    render(
      <Providers tooltips={{}}>
        <BacktestConfigDialog open onClose={jest.fn()} />
      </Providers>
    );
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('calls onClose on Cancel', () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.click(screen.getByRole('button', { name: /Cancel/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape', () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
