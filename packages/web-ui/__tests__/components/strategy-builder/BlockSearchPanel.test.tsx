import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BlockSearchPanel } from '@/components/strategy-builder/BlockSearchPanel';
import { Providers } from '@/components/strategy-builder/Providers';
import { BlockType } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const mockBlock = {
  id: 'rsi',
  type: BlockType.INDICATOR,
  name: 'RSI',
  description: 'Relative Strength Index',
  category: 'indicators',
};

const mockCategory = {
  id: 'indicators',
  name: 'Indicators',
  blockTypes: [BlockType.INDICATOR],
};

const defaultStore = {
  blockLibrary: [mockBlock],
  blockCategories: [mockCategory],
  isLoadingLibrary: false,
  addBlock: jest.fn(),
  currentStrategy: null,
};

// useStrategyStore.getState is also called in BlockSearchPanel
(useStrategyStore as any).getState = jest.fn().mockReturnValue({ currentStrategy: null });

function renderPanel(overrides = {}) {
  mockStore.mockReturnValue({ ...defaultStore, ...overrides } as any);
  return render(
    <Providers tooltips={{}}>
      <BlockSearchPanel />
    </Providers>
  );
}

describe('BlockSearchPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders block library header', () => {
    renderPanel();
    expect(screen.getByText('Block Library')).toBeInTheDocument();
  });

  it('shows loading when isLoadingLibrary', () => {
    renderPanel({ isLoadingLibrary: true });
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('shows empty state when no blocks match', () => {
    renderPanel({ blockLibrary: [] });
    expect(screen.getByText('No blocks match filters')).toBeInTheDocument();
  });

  it('renders block cards from library', () => {
    renderPanel();
    expect(screen.getByText('RSI')).toBeInTheDocument();
  });

  it('filters by search text', () => {
    renderPanel();
    const input = screen.getByPlaceholderText('Search blocks…');
    fireEvent.change(input, { target: { value: 'nonexistent' } });
    expect(screen.getByText('No blocks match filters')).toBeInTheDocument();
  });

  it('shows count in footer', () => {
    renderPanel();
    expect(screen.getByText('1 / 1 blocks')).toBeInTheDocument();
  });

  it('expands block card on click and shows Add button', () => {
    renderPanel();
    const toggle = screen.getByRole('button', { name: /RSI/ });
    fireEvent.click(toggle);
    expect(screen.getByRole('button', { name: /Add to Strategy/ })).toBeInTheDocument();
  });

  it('calls addBlock when Add to Strategy is clicked', () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /RSI/ }));
    fireEvent.click(screen.getByRole('button', { name: /Add to Strategy/ }));
    expect(defaultStore.addBlock).toHaveBeenCalledWith(BlockType.INDICATOR, 0);
  });

  it('shows category options in select', () => {
    renderPanel();
    expect(screen.getByText('Indicators')).toBeInTheDocument();
  });

  it('filters by type', () => {
    renderPanel();
    const typeSelect = screen.getAllByRole('combobox')[1];
    fireEvent.change(typeSelect, { target: { value: BlockType.ENTRY_CONDITION } });
    expect(screen.getByText('No blocks match filters')).toBeInTheDocument();
  });
});
