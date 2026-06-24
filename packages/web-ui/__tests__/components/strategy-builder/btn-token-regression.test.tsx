/**
 * Regression guard for BTCAAAAA-31088 / BTCAAAAA-37304:
 * All Cancel/Confirm action buttons must use board-locked CSS tokens
 * --btn-cancel-bg and --btn-confirm-bg instead of legacy accent-red/accent-green.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ExitConditionDialog } from '@/components/strategy-builder/ExitConditionDialog';
import { TimingConstraintDialog } from '@/components/strategy-builder/TimingConstraintDialog';
import { AutoFixConfirmDialog } from '@/components/strategy-builder/AutoFixConfirmDialog';
import { Providers } from '@/components/strategy-builder/Providers';

function renderExitDialog(props: Partial<React.ComponentProps<typeof ExitConditionDialog>> = {}) {
  return render(
    <Providers tooltips={{}}>
      <ExitConditionDialog open={true} onSave={jest.fn()} onCancel={jest.fn()} {...props} />
    </Providers>
  );
}

function renderTimingDialog(props: Partial<React.ComponentProps<typeof TimingConstraintDialog>> = {}) {
  return render(
    <TimingConstraintDialog
      open={true}
      blockName="TestBlock"
      signalName="TestSignal"
      availableReferences={[{ displayName: 'Ref A', referenceId: 'ref-a' }]}
      onSave={jest.fn()}
      onCancel={jest.fn()}
      {...props}
    />
  );
}

function renderAutoFixDialog(props: Partial<React.ComponentProps<typeof AutoFixConfirmDialog>> = {}) {
  return render(
    <AutoFixConfirmDialog
      open={true}
      fixType="DUPLICATE_BLOCK_NAME"
      fixDescription="Remove duplicate"
      impactAnalysis="No side effects"
      beforeState={{ name: 'Old Name', enabled: true }}
      afterState={{ name: 'New Name', enabled: true }}
      onConfirm={jest.fn()}
      onCancel={jest.fn()}
      {...props}
    />
  );
}

describe('Modal palette button token regression (BTCAAAAA-31088)', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('ExitConditionDialog', () => {
    it('Cancel button uses --btn-cancel-bg token', () => {
      renderExitDialog();
      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelBtn).toHaveStyle({ background: 'var(--btn-cancel-bg)' });
    });

    it('Add/Confirm button uses --btn-confirm-bg token', () => {
      renderExitDialog();
      const saveBtn = screen.getByRole('button', { name: /Add Exit Condition|Update Exit Condition/i });
      expect(saveBtn).toHaveStyle({ background: 'var(--btn-confirm-bg)' });
    });

    it('Cancel button does NOT use accent-red', () => {
      renderExitDialog();
      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelBtn).not.toHaveStyle({ background: 'var(--accent-red)' });
    });

    it('Confirm button does NOT use accent-green', () => {
      renderExitDialog();
      const saveBtn = screen.getByRole('button', { name: /Add Exit Condition|Update Exit Condition/i });
      expect(saveBtn).not.toHaveStyle({ background: 'var(--accent-green)' });
    });
  });

  describe('TimingConstraintDialog', () => {
    it('Cancel button uses --btn-cancel-bg token', () => {
      renderTimingDialog();
      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelBtn).toHaveStyle({ background: 'var(--btn-cancel-bg)' });
    });

    it('Save/OK button uses --btn-confirm-bg token', () => {
      renderTimingDialog();
      const okBtn = screen.getByRole('button', { name: /Save Constraint|OK/i });
      expect(okBtn).toHaveStyle({ background: 'var(--btn-confirm-bg)' });
    });
  });

  describe('AutoFixConfirmDialog', () => {
    it('Apply Fix button uses --btn-confirm-bg token', () => {
      renderAutoFixDialog();
      const applyBtn = screen.getByRole('button', { name: /Apply Fix/i });
      expect(applyBtn).toHaveStyle({ background: 'var(--btn-confirm-bg)' });
    });

    it('Cancel button does NOT use --btn-confirm-bg', () => {
      renderAutoFixDialog();
      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelBtn).not.toHaveStyle({ background: 'var(--btn-confirm-bg)' });
    });
  });
});
