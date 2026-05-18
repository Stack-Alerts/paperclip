import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExitConditionDialog } from '@/components/strategy-builder/ExitConditionDialog';
import { Providers } from '@/components/strategy-builder/Providers';

function renderDialog(props: Partial<React.ComponentProps<typeof ExitConditionDialog>> = {}) {
  const defaults = {
    open: true,
    onSave: jest.fn(),
    onCancel: jest.fn(),
  };
  const merged = { ...defaults, ...props };
  return { ...merged, ...render(<Providers tooltips={{}}><ExitConditionDialog {...merged} /></Providers>) };
}

describe('ExitConditionDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders nothing when closed', () => {
    renderDialog({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    renderDialog();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Exit Condition/ })).toBeInTheDocument();
  });

  it('shows signal name when provided', () => {
    renderDialog({ signalName: 'RSI Cross' });
    expect(screen.getByText('(RSI Cross)')).toBeInTheDocument();
  });

  it('initialises from existing', () => {
    renderDialog({ existing: { percentage: 0.75, exitMode: 'FLEXIBLE', signalName: '', bindingLevel: 'SIGNAL', tpProximityThreshold: 1, reversalTrigger: 0.5, recheckEnabled: false, recheckBarDelay: 3 } });
    expect((screen.getByLabelText(/Exit Percentage/) as HTMLInputElement).value).toBe('75');
    // FLEXIBLE radio should be checked when existingConfig has exitMode FLEXIBLE
    expect(screen.getByLabelText(/TP Proximity/)).toBeInTheDocument();
  });

  it('calls onCancel when Cancel clicked', () => {
    const { onCancel } = renderDialog();
    fireEvent.click(screen.getByRole('button', { name: /Cancel/ }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('calls onCancel on backdrop click', () => {
    const { onCancel } = renderDialog();
    fireEvent.click(document.querySelector('.absolute.inset-0')!);
    expect(onCancel).toHaveBeenCalled();
  });

  it('calls onCancel on Escape key', () => {
    const { onCancel } = renderDialog();
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onCancel).toHaveBeenCalled();
  });

  it('shows error when percentage is out of range', () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText(/Exit Percentage/), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /Save Exit Condition/ }));
    expect(screen.getByText(/Percentage must be between 1 and 100/)).toBeInTheDocument();
  });

  it('calls onSave and onCancel with valid data', () => {
    const { onSave, onCancel } = renderDialog();
    fireEvent.click(screen.getByRole('button', { name: /Save Exit Condition/ }));
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ percentage: 0.5, exitMode: 'ABSOLUTE' }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('shows FLEXIBLE mode parameters when FLEXIBLE selected', () => {
    renderDialog();
    fireEvent.click(screen.getByRole('radio', { name: 'FLEXIBLE' }));
    expect(screen.getByLabelText(/TP Proximity/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Reversal Trigger/)).toBeInTheDocument();
  });

  it('shows recheck bar delay when recheck enabled', () => {
    renderDialog();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByLabelText(/Bar Delay/)).toBeInTheDocument();
  });
});
