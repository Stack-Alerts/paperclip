import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyBlocksPanel } from '@/components/strategy-builder/StrategyBlocksPanel';
import { Providers } from '@/components/strategy-builder/Providers';
import { BlockType, StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const makeBlock = (id: string, type: BlockType, index: number) => ({
  id,
  type,
  index,
  data: {},
});

const mockStrategy = {
  id: 'strat-1',
  name: 'Test Strategy',
  status: StrategyStatus.DRAFT,
  blocks: [
    makeBlock('block-aaa', BlockType.ENTRY_CONDITION, 0),
    makeBlock('block-bbb', BlockType.EXIT_CONDITION, 1),
  ],
  settings: { timeframe: '1h' },
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

const defaultStore = {
  currentStrategy: mockStrategy,
  selectedBlockIndex: null,
  selectBlock: jest.fn(),
  deleteBlock: jest.fn(),
  reorderBlocks: jest.fn(),
};

function renderPanel(overrides = {}) {
  mockStore.mockReturnValue({ ...defaultStore, ...overrides } as any);
  return render(
    <Providers tooltips={{}}>
      <StrategyBlocksPanel />
    </Providers>
  );
}

describe('StrategyBlocksPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders header with block count', () => {
    renderPanel();
    expect(screen.getByText('Strategy Blocks')).toBeInTheDocument();
    expect(screen.getByText('2 blocks')).toBeInTheDocument();
  });

  it('shows empty state when no blocks', () => {
    renderPanel({ currentStrategy: { ...mockStrategy, blocks: [] } });
    expect(screen.getByText('No blocks added yet')).toBeInTheDocument();
  });

  it('renders block items with position badges', () => {
    renderPanel();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('renders entry and exit condition type labels', () => {
    renderPanel();
    expect(screen.getByText('Entry Condition')).toBeInTheDocument();
    expect(screen.getByText('Exit Condition')).toBeInTheDocument();
  });

  it('calls selectBlock when block is clicked', () => {
    renderPanel();
    const block = screen.getByText('Entry Condition').closest('div[class*="rounded"]')!;
    fireEvent.click(block);
    expect(defaultStore.selectBlock).toHaveBeenCalledWith(0);
  });

  it('calls deleteBlock when remove button is clicked', () => {
    renderPanel();
    const removeButtons = screen.getAllByLabelText('Remove block');
    fireEvent.click(removeButtons[0]);
    expect(defaultStore.deleteBlock).toHaveBeenCalledWith(0);
  });

  it('disables move-up on first block', () => {
    renderPanel();
    const upButtons = screen.getAllByLabelText('Move block up');
    expect(upButtons[0]).toBeDisabled();
    expect(upButtons[1]).not.toBeDisabled();
  });

  it('disables move-down on last block', () => {
    renderPanel();
    const downButtons = screen.getAllByLabelText('Move block down');
    expect(downButtons[0]).not.toBeDisabled();
    expect(downButtons[1]).toBeDisabled();
  });

  it('calls reorderBlocks on move-up click', () => {
    renderPanel();
    const upButtons = screen.getAllByLabelText('Move block up');
    fireEvent.click(upButtons[1]);
    expect(defaultStore.reorderBlocks).toHaveBeenCalledWith(1, 0);
  });

  it('calls reorderBlocks on move-down click', () => {
    renderPanel();
    const downButtons = screen.getAllByLabelText('Move block down');
    fireEvent.click(downButtons[0]);
    expect(defaultStore.reorderBlocks).toHaveBeenCalledWith(0, 1);
  });

  it('highlights selected block', () => {
    renderPanel({ selectedBlockIndex: 0 });
    const blocks = screen.getAllByText(/#\d/).map((el) => el.closest('div[class*="rounded"]'));
    expect(blocks[0]?.className).toContain('ring-1');
  });

  it('handles null currentStrategy gracefully', () => {
    renderPanel({ currentStrategy: null });
    expect(screen.getByText('No blocks added yet')).toBeInTheDocument();
    expect(screen.getByText('0 blocks')).toBeInTheDocument();
  });
});
