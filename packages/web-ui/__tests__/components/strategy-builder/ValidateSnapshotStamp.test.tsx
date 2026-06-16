/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { StrategyBuilder } from '@/components/strategy-builder/StrategyBuilder';
import { Providers } from '@/components/strategy-builder/Providers';
import { BlockType, StrategyStatus, type Strategy, type Block } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/useStrategyStore';

const mockUseStrategyStore = useStrategyStore as unknown as jest.Mock;

const baseBlocks: Block[] = [
  {
    id: 'b1',
    type: BlockType.INDICATOR,
    index: 0,
    data: { name: 'RSI', enabled: true, params: { period: 14 } },
  },
];

const sampleStrategy: Strategy = {
  id: 'strat-1',
  name: 'Test Strategy',
  status: StrategyStatus.VALID,
  blocks: baseBlocks,
  settings: { timeframe: '1h', targetMarket: 'BTC/USDT' },
  createdAt: '2026-06-16T00:00:00Z',
  updatedAt: '2026-06-16T00:00:00Z',
};

function makeStore(overrides: any = {}) {
  return {
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
    ...overrides,
  };
}

function renderBuilder() {
  return render(
    <Providers tooltips={{}}>
      <StrategyBuilder />
    </Providers>
  );
}

describe('BTCAAAAA-36689 validate-snapshot stamping (round 2)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('stamps validationPassedSnapshot when isValidating transitions true->false with status=VALID', () => {
    // Round 1: loaded with a VALID strategy but no in-flight validation yet.
    mockUseStrategyStore.mockReturnValue(makeStore({
      currentStrategy: sampleStrategy,
    }) as any);
    const { rerender } = renderBuilder();

    // Round 2: validation in flight.
    mockUseStrategyStore.mockReturnValue(makeStore({
      currentStrategy: sampleStrategy,
      isValidating: true,
    }) as any);
    rerender(
      <Providers tooltips={{}}>
        <StrategyBuilder />
      </Providers>
    );

    // Round 3: validation resolved with status=VALID (unchanged) — the observer
    // useEffect should now stamp the snapshot so the stepper shows ✓.
    mockUseStrategyStore.mockReturnValue(makeStore({
      currentStrategy: sampleStrategy,
      isValidating: false,
    }) as any);
    rerender(
      <Providers tooltips={{}}>
        <StrategyBuilder />
      </Providers>
    );

    // StepperRibbon renders <span aria-label="complete">✓</span> for complete steps.
    const completeMarkers = screen.getAllByLabelText('complete');
    expect(completeMarkers.length).toBeGreaterThanOrEqual(1);
  });

  it('does NOT stamp when validation resolves with status=INVALID', () => {
    const invalidStrategy: Strategy = { ...sampleStrategy, status: StrategyStatus.INVALID };

    mockUseStrategyStore.mockReturnValue(makeStore({ currentStrategy: invalidStrategy }) as any);
    const { rerender } = renderBuilder();

    mockUseStrategyStore.mockReturnValue(makeStore({
      currentStrategy: invalidStrategy,
      isValidating: true,
    }) as any);
    rerender(
      <Providers tooltips={{}}>
        <StrategyBuilder />
      </Providers>
    );

    mockUseStrategyStore.mockReturnValue(makeStore({
      currentStrategy: invalidStrategy,
      isValidating: false,
    }) as any);
    rerender(
      <Providers tooltips={{}}>
        <StrategyBuilder />
      </Providers>
    );

    const completeMarkers = screen.queryAllByLabelText('complete');
    expect(completeMarkers.length).toBe(0);
  });
});
