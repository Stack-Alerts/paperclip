/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { StrategyBuilder } from '@/components/strategy-builder/StrategyBuilder';
import { Providers } from '@/components/strategy-builder/Providers';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/useStrategyStore';

const mockUseStrategyStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const mockStore = {
  currentStrategy: null,
  isLoadingStrategy: false,
  strategyError: null,
  blockLibrary: [],
  blockCategories: [],
  isLoadingLibrary: false,
  selectedBlockIndex: null,
  validationMessages: [],
  isValidating: false,
  backTestInProgress: false,
  backTestProgress: 0,
  backTestResult: null,
  strategyList: [],
  loadStrategy: jest.fn().mockResolvedValue(undefined),
  createStrategy: jest.fn().mockResolvedValue(undefined),
  saveStrategy: jest.fn(),
  deleteBlock: jest.fn(),
  addBlock: jest.fn(),
  updateBlock: jest.fn(),
  reorderBlocks: jest.fn(),
  validateStrategy: jest.fn(),
  runBacktest: jest.fn(),
  loadBlockLibrary: jest.fn().mockResolvedValue(undefined),
  clearValidation: jest.fn(),
  selectBlock: jest.fn(),
  setCurrentStrategy: jest.fn(),
  updateStrategySettings: jest.fn(),
  pollBacktestResult: jest.fn(),
};

function renderBuilder(props = {}) {
  return render(
    <Providers tooltips={{}}>
      <StrategyBuilder {...props} />
    </Providers>
  );
}

describe('StrategyBuilder', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseStrategyStore.mockReturnValue(mockStore as any);
  });

  it('shows loading state', () => {
    mockUseStrategyStore.mockReturnValue({ ...mockStore, isLoadingStrategy: true } as any);
    renderBuilder();
    expect(screen.getByText('Loading strategy...')).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockUseStrategyStore.mockReturnValue({ ...mockStore, strategyError: 'Not found' } as any);
    renderBuilder();
    expect(screen.getByText(/Not found/)).toBeInTheDocument();
  });

  it('renders three-panel layout when loaded', () => {
    renderBuilder();
    expect(screen.getByText('Block Library')).toBeInTheDocument();
    expect(screen.getByText('Strategy Blocks')).toBeInTheDocument();
    // StrategyInfoPanel renders "No strategy loaded" when currentStrategy is null
    expect(screen.getByText('No strategy loaded')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderBuilder();
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    // ActionBar Validate button (not the stepper Validate button — use exact aria-label match)
    const validateBtns = screen.getAllByRole('button', { name: /Validate/ });
    // stepper has one, action bar has one — at least 2 total
    expect(validateBtns.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('button', { name: 'Backtest' })).toBeInTheDocument();
  });

  it('calls loadStrategy when strategyId is provided', () => {
    renderBuilder({ strategyId: 'strat-123' });
    expect(mockStore.loadStrategy).toHaveBeenCalledWith('strat-123');
  });

  it('calls loadBlockLibrary on mount', () => {
    renderBuilder();
    expect(mockStore.loadBlockLibrary).toHaveBeenCalled();
  });
});
