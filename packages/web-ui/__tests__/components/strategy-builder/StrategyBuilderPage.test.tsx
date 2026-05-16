import React from 'react';
import { render, screen } from '@testing-library/react';
import { StrategyBuilderPageWrapper } from '@/components/StrategyBuilderPage';
import { Providers } from '@/components/Providers';

jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn().mockReturnValue({ get: () => null }),
}));

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn().mockReturnValue({
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
  }),
}));

describe('StrategyBuilderPageWrapper', () => {
  it('renders the strategy builder within Suspense', () => {
    render(
      <Providers tooltips={{}}>
        <StrategyBuilderPageWrapper />
      </Providers>
    );
    expect(screen.getByText('Block Library')).toBeInTheDocument();
  });
});
