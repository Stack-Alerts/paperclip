import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StepperRibbon } from '@/components/strategy-builder/StepperRibbon';
import { Providers } from '@/components/strategy-builder/Providers';

function renderRibbon(props = {}) {
  const defaults = { currentStep: 0, onStepClick: jest.fn() };
  return render(
    <Providers tooltips={{}}>
      <StepperRibbon {...defaults} {...props} />
    </Providers>
  );
}

describe('StepperRibbon', () => {
  it('renders all four step labels', () => {
    renderRibbon();
    expect(screen.getByText(/Design/)).toBeInTheDocument();
    expect(screen.getByText(/Validate/)).toBeInTheDocument();
    expect(screen.getByText(/Test\/Optimize/)).toBeInTheDocument();
    expect(screen.getByText(/Publish/)).toBeInTheDocument();
  });

  it('renders three arrow separators', () => {
    renderRibbon();
    expect(screen.getAllByText('→')).toHaveLength(3);
  });

  it('marks current step as active via aria-current', () => {
    renderRibbon({ currentStep: 1 });
    const buttons = screen.getAllByRole('button');
    expect(buttons[1]).toHaveAttribute('aria-current', 'step');
  });

  it('calls onStepClick with correct index', () => {
    const onStepClick = jest.fn();
    renderRibbon({ onStepClick });
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[2]);
    expect(onStepClick).toHaveBeenCalledWith(2);
  });

  it('shows ✓ mark for completed steps', () => {
    renderRibbon({ completedSteps: new Set([0]) });
    expect(screen.getByLabelText('complete')).toBeInTheDocument();
  });

  it('shows ✗ mark for error steps', () => {
    renderRibbon({ errorSteps: new Set([1]) });
    expect(screen.getByLabelText('error')).toBeInTheDocument();
  });

  it('defaults to no completed or error steps', () => {
    renderRibbon();
    expect(screen.queryByLabelText('complete')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('error')).not.toBeInTheDocument();
  });

  // BTCAAAAA-36689: the MainWindow uses `forceCompleteStepIds` to render the
  // Validate step green when the strategy is validated AND pristine (no edits
  // since validation passed). The ribbon must apply the override even when
  // the step is not in completedSteps.
  describe('forceCompleteStepIds (BTCAAAAA-36689)', () => {
    it('renders the forced step as complete when not in completedSteps', () => {
      renderRibbon({ forceCompleteStepIds: new Set([1]) });
      // Only one ✓ mark should exist (the forced Validate step).
      expect(screen.getAllByLabelText('complete')).toHaveLength(1);
      expect(screen.getByText(/Validate/)).toBeInTheDocument();
    });

    it('errorSteps still take precedence over forceCompleteStepIds', () => {
      renderRibbon({
        forceCompleteStepIds: new Set([1]),
        errorSteps: new Set([1]),
      });
      expect(screen.getByLabelText('error')).toBeInTheDocument();
      expect(screen.queryByLabelText('complete')).not.toBeInTheDocument();
    });

    it('multiple forced IDs each render as complete', () => {
      renderRibbon({ forceCompleteStepIds: new Set([0, 1, 2]) });
      expect(screen.getAllByLabelText('complete')).toHaveLength(3);
    });
  });

  // BTCAAAAA-37756: pulseStepIds gives the named steps an amber glow (mirrors
  // the Save button's pulse) to signal "needs action". Used by the MainWindow
  // to glow the Validate step when the strategy is dirty / unvalidated.
  describe('pulseStepIds (BTCAAAAA-37756)', () => {
    it('marks pulsed pending step with data-pulse=true', () => {
      renderRibbon({ pulseStepIds: new Set([1]) });
      const buttons = screen.getAllByRole('button');
      expect(buttons[1]).toHaveAttribute('data-pulse', 'true');
      expect(buttons[1].className).toMatch(/button-amber-pulse/);
    });

    it('does NOT pulse a step that is already complete', () => {
      renderRibbon({
        pulseStepIds: new Set([1]),
        forceCompleteStepIds: new Set([1]),
      });
      const buttons = screen.getAllByRole('button');
      expect(buttons[1]).not.toHaveAttribute('data-pulse');
      expect(buttons[1].className).not.toMatch(/button-amber-pulse/);
    });

    it('does NOT pulse a step that is in error', () => {
      renderRibbon({
        pulseStepIds: new Set([1]),
        errorSteps: new Set([1]),
      });
      const buttons = screen.getAllByRole('button');
      expect(buttons[1]).not.toHaveAttribute('data-pulse');
    });

    it('omitting pulseStepIds leaves no pulse markers', () => {
      renderRibbon();
      const buttons = screen.getAllByRole('button');
      buttons.forEach(b => expect(b).not.toHaveAttribute('data-pulse'));
    });
  });

  // BTCAAAAA-38259: the suppression logic lives in
  // StrategyBuilderMainWindow — the stepper itself does not need a new visual
  // state for this fix. The MainWindow captures a `validationPromptDismissedFor`
  // snapshot the first time the user closes the "Validation Required" alert
  // and refuses to re-open the alert while the strategy remains in that same
  // dirty state. Once the user edits the strategy (snapshot diverges) or
  // switches to a different strategy (id change), the dismissed flag is
  // cleared and the next test/optimize click re-prompts as before.
});
