import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StepperRibbon } from '@/components/StepperRibbon';
import { Providers } from '@/components/Providers';

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
});
