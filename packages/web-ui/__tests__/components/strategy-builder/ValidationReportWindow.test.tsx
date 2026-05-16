/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ValidationReportWindow } from '@/components/strategy-builder/ValidationReportWindow';
import { Providers } from '@/components/strategy-builder/Providers';
import { ValidationLevel } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useStrategyStore', () => ({ useStrategyStore: jest.fn() }));
import { useStrategyStore } from '@/hooks/useStrategyStore';
const mockStore = useStrategyStore as jest.MockedFunction<typeof useStrategyStore>;

const makeMsg = (id: string, level: ValidationLevel, text: string, blockIndex?: number) => ({
  id, level, text, blockIndex,
});

function renderWindow(messages = [] as ReturnType<typeof makeMsg>[], isValidating = false) {
  const validateStrategy = jest.fn().mockResolvedValue(undefined);
  mockStore.mockReturnValue({ validationMessages: messages, isValidating, validateStrategy } as any);
  const onClose = jest.fn();
  return { onClose, validateStrategy, ...render(<Providers tooltips={{}}><ValidationReportWindow open onClose={onClose} /></Providers>) };
}

describe('ValidationReportWindow', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders nothing when closed', () => {
    mockStore.mockReturnValue({ validationMessages: [], isValidating: false, validateStrategy: jest.fn() } as any);
    render(<Providers tooltips={{}}><ValidationReportWindow open={false} onClose={jest.fn()} /></Providers>);
    expect(screen.queryByText(/Validation Report/)).not.toBeInTheDocument();
  });

  it('renders header and empty state', () => {
    renderWindow();
    expect(screen.getByText(/Validation Report/)).toBeInTheDocument();
    expect(screen.getByText('No validation results')).toBeInTheDocument();
    expect(screen.getByText(/No validation messages/)).toBeInTheDocument();
  });

  it('shows message counts', () => {
    renderWindow([
      makeMsg('1', ValidationLevel.ERROR, 'Bad block'),
      makeMsg('2', ValidationLevel.WARNING, 'Watch out'),
      makeMsg('3', ValidationLevel.INFO, 'FYI'),
    ]);
    expect(screen.getByText('3 messages')).toBeInTheDocument();
    expect(screen.getByText(/1 error/)).toBeInTheDocument();
    expect(screen.getByText(/1 warning/)).toBeInTheDocument();
  });

  it('renders error messages with block index', () => {
    renderWindow([makeMsg('1', ValidationLevel.ERROR, 'Critical fail', 2)]);
    expect(screen.getByText('Critical fail')).toBeInTheDocument();
    expect(screen.getByText('Block #3')).toBeInTheDocument();
  });

  it('renders warning messages', () => {
    renderWindow([makeMsg('1', ValidationLevel.WARNING, 'Mild concern')]);
    expect(screen.getByText('Mild concern')).toBeInTheDocument();
  });

  it('renders info messages', () => {
    renderWindow([makeMsg('1', ValidationLevel.INFO, 'Just info')]);
    expect(screen.getByText('Just info')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const { onClose } = renderWindow();
    fireEvent.click(screen.getByRole('button', { name: /Close dialog/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows All Clear button when no messages', () => {
    renderWindow();
    expect(screen.getByRole('button', { name: /All Clear/ })).toBeInTheDocument();
  });

  it('shows warning close button when errors present', () => {
    renderWindow([makeMsg('1', ValidationLevel.ERROR, 'Error')]);
    expect(screen.getByRole('button', { name: /⚠ Close/ })).toBeInTheDocument();
  });

  it('calls validateStrategy on Re-validate click', () => {
    const { validateStrategy } = renderWindow();
    fireEvent.click(screen.getByRole('button', { name: /Re-validate/ }));
    expect(validateStrategy).toHaveBeenCalled();
  });

  it('disables Re-validate button while validating', () => {
    renderWindow([], true);
    expect(screen.getByRole('button', { name: /Validating/ })).toBeDisabled();
  });
});
