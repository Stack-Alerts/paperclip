import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BacktestConfigDialog } from '@/components/strategy-builder/BacktestConfigDialog';
import { Providers } from '@/components/strategy-builder/Providers';
import { StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
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

  it('shows date, capital, and commission inputs', () => {
    renderDialog();
    expect(screen.getByLabelText(/Start Date/)).toBeInTheDocument();
    expect(screen.getByLabelText(/End Date/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Capital/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Commission/)).toBeInTheDocument();
  });

  it('shows preset day buttons', () => {
    renderDialog();
    expect(screen.getByRole('button', { name: '30d' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '90d' })).toBeInTheDocument();
  });

  it('calls runBacktest and closes on Run click', async () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.click(screen.getByRole('button', { name: /Run Backtest/ }));
    await waitFor(() => {
      expect(defaultStore.runBacktest).toHaveBeenCalledWith(
        expect.objectContaining({ strategyId: 'strat-1' }),
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error when dates are invalid', async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText(/Start Date/), { target: { value: '2026-06-01' } });
    fireEvent.change(screen.getByLabelText(/End Date/), { target: { value: '2026-01-01' } });
    fireEvent.click(screen.getByRole('button', { name: /Run Backtest/ }));
    await waitFor(() => expect(screen.getByText(/Start date must be before/)).toBeInTheDocument());
  });

  it('disables Run Backtest when backtest is in progress', () => {
    mockStore.mockReturnValue({ ...defaultStore, backTestInProgress: true } as any);
    render(
      <Providers tooltips={{}}>
        <BacktestConfigDialog open onClose={jest.fn()} />
      </Providers>
    );
    expect(screen.getByRole('button', { name: /Running/ })).toBeDisabled();
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
