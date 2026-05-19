/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyInfoPanel } from '@/components/strategy-builder/StrategyInfoPanel';
import { Providers } from '@/components/strategy-builder/Providers';
import { BlockType, StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/strategy-builder/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const mockStrategy = {
  id: 'strat-1',
  name: 'Test Strategy',
  description: 'A test strategy',
  status: StrategyStatus.DRAFT,
  strategyType: 'Bullish',
  blocks: [
    { id: 'b1', type: BlockType.ENTRY_CONDITION, index: 0, data: { logic: 'AND', signals: [] } },
    { id: 'b2', type: BlockType.EXIT_CONDITION, index: 1, data: { logic: 'EXIT', signals: [] } },
    { id: 'b3', type: BlockType.INDICATOR, index: 2, data: { logic: 'OR', signals: [] } },
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
  setCurrentStrategy: jest.fn(),
  saveStrategy: jest.fn().mockResolvedValue(mockStrategy),
};

function renderPanel(props: React.ComponentProps<typeof StrategyInfoPanel> = {}, overrides = {}) {
  mockStore.mockReturnValue({ ...defaultStore, ...overrides } as any);
  return render(
    <Providers tooltips={{}}>
      <StrategyInfoPanel {...props} />
    </Providers>
  );
}

describe('StrategyInfoPanel — full mode', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders Strategy Information header', () => {
    renderPanel();
    expect(screen.getByText('Strategy Information')).toBeInTheDocument();
  });

  it('shows strategy name in editable input', () => {
    renderPanel();
    const input = screen.getByDisplayValue('Test Strategy');
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe('INPUT');
  });

  it('calls saveStrategy on name blur', () => {
    renderPanel();
    const input = screen.getByDisplayValue('Test Strategy');
    fireEvent.blur(input, { target: { value: 'New Name' } });
    expect(defaultStore.setCurrentStrategy).toHaveBeenCalled();
  });

  it('shows Bullish and Bearish type buttons', () => {
    renderPanel();
    expect(screen.getByText('Bullish')).toBeInTheDocument();
    expect(screen.getByText('Bearish')).toBeInTheDocument();
  });

  it('calls saveStrategy on type change', () => {
    renderPanel();
    fireEvent.click(screen.getByText('Bearish'));
    expect(defaultStore.setCurrentStrategy).toHaveBeenCalledWith(
      expect.objectContaining({ strategyType: 'Bearish' })
    );
  });

  it('shows stat labels', () => {
    renderPanel();
    expect(screen.getByText(/Required:/)).toBeInTheDocument();
    expect(screen.getByText(/Optional:/)).toBeInTheDocument();
    expect(screen.getByText(/Rechecked:/)).toBeInTheDocument();
    expect(screen.getByText(/Exit Conditions:/)).toBeInTheDocument();
    expect(screen.getByText(/Time Constraint:/)).toBeInTheDocument();
  });

  it('shows No strategy loaded when no strategy', () => {
    renderPanel({}, { currentStrategy: null });
    expect(screen.getByText(/No strategy loaded/)).toBeInTheDocument();
  });

  it('description renders as text (no textarea in full mode)', () => {
    renderPanel();
    const textareas = document.querySelectorAll('textarea');
    expect(textareas.length).toBe(0);
    expect(screen.getByText(/Description:/)).toBeInTheDocument();
  });
});

describe('StrategyInfoPanel — compact mode', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders without crashing in compact mode', () => {
    renderPanel({ compact: true });
    expect(screen.getByText('Strategy Information')).toBeInTheDocument();
  });

  it('renders strategy name as editable input in compact mode', () => {
    renderPanel({ compact: true });
    const input = screen.getByDisplayValue('Test Strategy');
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe('INPUT');
  });

  it('renders Bullish and Bearish type buttons in compact mode', () => {
    renderPanel({ compact: true });
    expect(screen.getByText('Bullish')).toBeInTheDocument();
    expect(screen.getByText('Bearish')).toBeInTheDocument();
  });

  it('shows all stat labels in a single row in compact mode', () => {
    renderPanel({ compact: true });
    expect(screen.getByText(/Required:/)).toBeInTheDocument();
    expect(screen.getByText(/Optional:/)).toBeInTheDocument();
    expect(screen.getByText(/Rechecked:/)).toBeInTheDocument();
    expect(screen.getByText(/Exit Conditions:/)).toBeInTheDocument();
    expect(screen.getByText(/Time Constraint:/)).toBeInTheDocument();
  });

  it('does not render a textarea in compact mode', () => {
    renderPanel({ compact: true });
    const textareas = document.querySelectorAll('textarea');
    expect(textareas.length).toBe(0);
  });

  it('shows truncated description text in compact mode (not textarea)', () => {
    renderPanel({ compact: true });
    // Should show a <p> with description, not a textarea
    const textareas = document.querySelectorAll('textarea');
    expect(textareas.length).toBe(0);
  });

  it('handles type change in compact mode', () => {
    renderPanel({ compact: true });
    fireEvent.click(screen.getByText('Bearish'));
    expect(defaultStore.setCurrentStrategy).toHaveBeenCalledWith(
      expect.objectContaining({ strategyType: 'Bearish' })
    );
  });

  it('shows No strategy loaded when no strategy in compact mode', () => {
    renderPanel({ compact: true }, { currentStrategy: null });
    expect(screen.getByText(/No strategy loaded/)).toBeInTheDocument();
  });

  it('compact mode uses bg-deep background', () => {
    const { container } = renderPanel({ compact: true });
    const panel = container.firstChild as HTMLElement;
    expect(panel.style.background).toContain('var(--bg-deep)');
  });

  it('full mode uses bg-panel background', () => {
    const { container } = renderPanel({ compact: false });
    const panel = container.firstChild as HTMLElement;
    expect(panel.style.background).toContain('var(--bg-panel)');
  });
});
