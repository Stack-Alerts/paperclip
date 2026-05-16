/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NewStrategyDialog } from '@/components/strategy-builder/NewStrategyDialog';
import { Providers } from '@/components/strategy-builder/Providers';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const defaultStore = {
  createStrategy: jest.fn().mockResolvedValue(undefined),
};

function renderDialog(open = true, onClose = jest.fn()) {
  mockStore.mockReturnValue(defaultStore as any);
  return { onClose, ...render(
    <Providers tooltips={{}}>
      <NewStrategyDialog open={open} onClose={onClose} />
    </Providers>
  )};
}

describe('NewStrategyDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders nothing when closed', () => {
    renderDialog(false);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    renderDialog();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Create New Strategy/)).toBeInTheDocument();
  });

  it('shows name and description fields', () => {
    renderDialog();
    expect(screen.getByLabelText(/Strategy Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
  });

  it('disables Create button when name is empty', () => {
    renderDialog();
    expect(screen.getByRole('button', { name: /Create Strategy/ })).toBeDisabled();
  });

  it('enables Create button when name is filled', () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText(/Strategy Name/), { target: { value: 'My Strat' } });
    expect(screen.getByRole('button', { name: /Create Strategy/ })).not.toBeDisabled();
  });

  it('calls createStrategy and closes on submit', async () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.change(screen.getByLabelText(/Strategy Name/), { target: { value: 'Test Strat' } });
    fireEvent.change(screen.getByLabelText(/Description/), { target: { value: 'Desc' } });
    fireEvent.click(screen.getByRole('button', { name: /Create Strategy/ }));
    await waitFor(() => {
      expect(defaultStore.createStrategy).toHaveBeenCalledWith('Test Strat', 'Desc');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error when createStrategy throws', async () => {
    defaultStore.createStrategy.mockRejectedValueOnce(new Error('Name taken'));
    renderDialog();
    fireEvent.change(screen.getByLabelText(/Strategy Name/), { target: { value: 'Bad' } });
    fireEvent.click(screen.getByRole('button', { name: /Create Strategy/ }));
    await waitFor(() => expect(screen.getByText('Name taken')).toBeInTheDocument());
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.click(screen.getByRole('button', { name: /Cancel/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when backdrop is clicked', () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    // click the backdrop (first div after the dialog wrapper)
    fireEvent.click(document.querySelector('.absolute.inset-0')!);
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape key', () => {
    const onClose = jest.fn();
    renderDialog(true, onClose);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
