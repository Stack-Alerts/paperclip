/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyBrowserDialog } from '@/components/strategy-builder/StrategyBrowserDialog';
import { Providers } from '@/components/strategy-builder/Providers';
import { StrategyStatus } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/strategy-builder/useStrategyStore', () => ({ useStrategyStore: jest.fn() }));
jest.mock('@/lib/strategy-builder/api', () => ({
  listStrategies: jest.fn().mockResolvedValue([]),
  getStrategyVersions: jest.fn().mockResolvedValue([]),
  deleteStrategyScoped: jest.fn().mockResolvedValue({}),
  duplicateStrategyScoped: jest.fn().mockResolvedValue({}),
  createStrategy: jest.fn().mockResolvedValue({}),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const makeStrategy = (id: string, name: string, status: StrategyStatus = StrategyStatus.DRAFT) => ({
  id,
  name,
  description: `Desc for ${name}`,
  status,
  blocks: [],
  settings: {},
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
});

function renderDialog(props: Partial<React.ComponentProps<typeof StrategyBrowserDialog>> = {}, strategies = [makeStrategy('1', 'Alpha')]) {
  mockStore.mockReturnValue({ strategyList: strategies } as any);
  const defaults = { open: true, onSelect: jest.fn(), onClose: jest.fn() };
  const merged = { ...defaults, ...props };
  return { ...merged, ...render(<Providers tooltips={{}}><StrategyBrowserDialog {...merged} /></Providers>) };
}

describe('StrategyBrowserDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders nothing when closed', () => {
    renderDialog({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    renderDialog();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Strategy Browser/)).toBeInTheDocument();
  });

  it('shows empty state when no strategies', () => {
    renderDialog({}, []);
    expect(screen.getByText('No strategies yet')).toBeInTheDocument();
  });

  it('lists strategies', () => {
    renderDialog({}, [makeStrategy('1', 'Alpha'), makeStrategy('2', 'Beta')]);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('filters strategies by search text', () => {
    renderDialog({}, [makeStrategy('1', 'Alpha'), makeStrategy('2', 'Beta')]);
    fireEvent.change(screen.getByPlaceholderText(/Search strategies/), { target: { value: 'alp' } });
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.queryByText('Beta')).not.toBeInTheDocument();
  });

  it('shows no-match message when search finds nothing', () => {
    renderDialog({}, [makeStrategy('1', 'Alpha')]);
    fireEvent.change(screen.getByPlaceholderText(/Search strategies/), { target: { value: 'xyz' } });
    expect(screen.getByText('No matching strategies')).toBeInTheDocument();
  });

  it('calls onClose when Cancel clicked', () => {
    const { onClose } = renderDialog();
    fireEvent.click(screen.getByRole('button', { name: /Cancel/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on backdrop click', () => {
    const { onClose } = renderDialog();
    fireEvent.click(document.querySelector('.absolute.inset-0')!);
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape key', () => {
    const { onClose } = renderDialog();
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('Open button disabled when nothing selected', () => {
    renderDialog();
    expect(screen.getByRole('button', { name: /Open/ })).toBeDisabled();
  });

  it('selects strategy and calls onSelect on Load', () => {
    const strat = makeStrategy('1', 'Alpha');
    const { onSelect, onClose } = renderDialog({}, [strat]);
    fireEvent.click(screen.getByText('Alpha'));
    fireEvent.click(screen.getByRole('button', { name: /Open/ }));
    expect(onSelect).toHaveBeenCalledWith(strat);
    expect(onClose).toHaveBeenCalled();
  });

  it('triggers Open on Enter when item selected', () => {
    const strat = makeStrategy('1', 'Alpha');
    const { onSelect } = renderDialog({}, [strat]);
    fireEvent.click(screen.getByText('Alpha'));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith(strat);
  });
});
