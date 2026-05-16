import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyInfoPanel } from '@/components/StrategyInfoPanel';
import { Providers } from '@/components/Providers';
import { BlockType, StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const mockStrategy = {
  id: 'strat-1',
  name: 'Test Strategy',
  description: 'A test strategy',
  status: StrategyStatus.DRAFT,
  blocks: [
    { id: 'b1', type: BlockType.ENTRY_CONDITION, index: 0, data: {} },
    { id: 'b2', type: BlockType.EXIT_CONDITION, index: 1, data: {} },
    { id: 'b3', type: BlockType.INDICATOR, index: 2, data: {} },
  ],
  settings: {
    timeframe: '1h',
    targetMarket: 'BTC/USD',
    riskParameters: { maxLossPerTrade: 2, maxDrawdown: 10, maxAllocation: 25 },
  },
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-05-16T00:00:00Z',
};

const defaultStore = {
  currentStrategy: mockStrategy,
  updateStrategySettings: jest.fn(),
  saveStrategy: jest.fn().mockResolvedValue(mockStrategy),
};

function renderPanel(overrides = {}) {
  mockStore.mockReturnValue({ ...defaultStore, ...overrides } as any);
  return render(
    <Providers tooltips={{}}>
      <StrategyInfoPanel />
    </Providers>
  );
}

describe('StrategyInfoPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders Strategy Info header', () => {
    renderPanel();
    expect(screen.getByText('Strategy Info')).toBeInTheDocument();
  });

  it('shows status badge', () => {
    renderPanel();
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('shows valid status badge for valid strategy', () => {
    renderPanel({ currentStrategy: { ...mockStrategy, status: StrategyStatus.VALID } });
    expect(screen.getByText('Valid')).toBeInTheDocument();
  });

  it('shows strategy name in input', () => {
    renderPanel();
    const input = screen.getByDisplayValue('Test Strategy');
    expect(input).toBeInTheDocument();
  });

  it('shows description', () => {
    renderPanel();
    expect(screen.getByText('A test strategy')).toBeInTheDocument();
  });

  it('shows block counts', () => {
    renderPanel();
    // 3 total, 1 entry, 1 exit — use getAllByText since both counts are "1"
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getAllByText('1')).toHaveLength(2); // entry=1, exit=1
  });

  it('shows timeframe select with current value', () => {
    renderPanel();
    const select = screen.getByDisplayValue('1h');
    expect(select).toBeInTheDocument();
  });

  it('calls updateStrategySettings on timeframe change', () => {
    renderPanel();
    const select = screen.getByDisplayValue('1h');
    fireEvent.change(select, { target: { value: '4h' } });
    expect(defaultStore.updateStrategySettings).toHaveBeenCalledWith({ timeframe: '4h' });
  });

  it('shows target market', () => {
    renderPanel();
    expect(screen.getByText('BTC/USD')).toBeInTheDocument();
  });

  it('shows risk parameters', () => {
    renderPanel();
    expect(screen.getByText(/Max loss\/trade/i)).toBeInTheDocument();
    expect(screen.getByText('2%')).toBeInTheDocument();
  });

  it('shows null strategy message when no strategy', () => {
    renderPanel({ currentStrategy: null });
    expect(screen.getByText(/No strategy loaded/)).toBeInTheDocument();
  });

  it('shows formatted dates', () => {
    renderPanel();
    // Jan 1, 2026 formatted
    expect(screen.getByText(/Jan/)).toBeInTheDocument();
  });
});
