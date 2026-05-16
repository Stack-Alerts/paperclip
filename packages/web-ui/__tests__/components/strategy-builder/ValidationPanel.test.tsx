import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ValidationPanel } from '@/components/strategy-builder/ValidationPanel';
import { Providers } from '@/components/strategy-builder/Providers';
import { ValidationLevel } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({
  useStrategyStore: jest.fn(),
}));

import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const makeMsg = (level: ValidationLevel, text: string, blockIndex?: number) => ({
  id: `msg-${Math.random()}`,
  level,
  text,
  blockIndex,
  timestamp: new Date().toISOString(),
});

const defaultStore = {
  validationMessages: [],
  isValidating: false,
  validateStrategy: jest.fn().mockResolvedValue(undefined),
  clearValidation: jest.fn(),
  selectBlock: jest.fn(),
};

function renderPanel(overrides = {}) {
  mockStore.mockReturnValue({ ...defaultStore, ...overrides } as any);
  return render(
    <Providers tooltips={{}}>
      <ValidationPanel />
    </Providers>
  );
}

describe('ValidationPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders validation header', () => {
    renderPanel();
    expect(screen.getByText('Validation')).toBeInTheDocument();
  });

  it('shows empty state when no messages', () => {
    renderPanel();
    expect(screen.getByText(/No validation results/)).toBeInTheDocument();
  });

  it('shows loading state when isValidating', () => {
    renderPanel({ isValidating: true });
    expect(screen.getByText(/Running validation/)).toBeInTheDocument();
  });

  it('shows Validate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /Validate/ })).toBeInTheDocument();
  });

  it('calls validateStrategy on Validate click', () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Validate/ }));
    expect(defaultStore.validateStrategy).toHaveBeenCalled();
  });

  it('renders error messages', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.ERROR, 'Missing entry block')] });
    expect(screen.getByText('Missing entry block')).toBeInTheDocument();
  });

  it('renders warning messages', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.WARNING, 'High risk ratio')] });
    expect(screen.getByText('High risk ratio')).toBeInTheDocument();
  });

  it('shows error/warning count summary', () => {
    renderPanel({
      validationMessages: [
        makeMsg(ValidationLevel.ERROR, 'e1'),
        makeMsg(ValidationLevel.WARNING, 'w1'),
      ],
    });
    expect(screen.getByText(/1 error/)).toBeInTheDocument();
    expect(screen.getByText(/1 warning/)).toBeInTheDocument();
  });

  it('shows Clear button when messages exist', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.INFO, 'info')] });
    expect(screen.getByRole('button', { name: /Clear/ })).toBeInTheDocument();
  });

  it('calls clearValidation on Clear click', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.INFO, 'info')] });
    fireEvent.click(screen.getByRole('button', { name: /Clear/ }));
    expect(defaultStore.clearValidation).toHaveBeenCalled();
  });

  it('calls selectBlock when message with blockIndex is clicked', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.ERROR, 'bad block', 2)] });
    fireEvent.click(screen.getByText('bad block'));
    expect(defaultStore.selectBlock).toHaveBeenCalledWith(2);
  });

  it('shows block index badge when blockIndex is set', () => {
    renderPanel({ validationMessages: [makeMsg(ValidationLevel.ERROR, 'err', 0)] });
    expect(screen.getByText('#1')).toBeInTheDocument();
  });
});
