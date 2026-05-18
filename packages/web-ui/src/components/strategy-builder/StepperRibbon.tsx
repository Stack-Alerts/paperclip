'use client';

import { InfoTooltip } from './InfoTooltip';

export type StepStatus = 'pending' | 'active' | 'complete' | 'error';

export interface Step {
  id: number;
  name: string;
  icon: string;
  tooltip: string;
}

const STEPS: Step[] = [
  { id: 0, name: 'Design',        icon: '📝', tooltip: 'Design your trading strategy' },
  { id: 1, name: 'Validate',      icon: '✓',  tooltip: 'Validate strategy configuration' },
  { id: 2, name: 'Test/Optimize', icon: '🧪', tooltip: 'Run backtest and optimize parameters' },
  { id: 3, name: 'Publish',       icon: '🚀', tooltip: 'Set publish status' },
];

function stepClasses(status: StepStatus, clickable: boolean): string {
  const base =
    'flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-colors border select-none';
  const cursor = clickable ? 'cursor-pointer' : 'cursor-default';
  switch (status) {
    case 'active':
      return `${base} ${cursor} bg-blue-600 border-blue-500 text-white`;
    case 'complete':
      return `${base} ${cursor} bg-emerald-900 border-emerald-700 text-emerald-300 hover:bg-emerald-800`;
    case 'error':
      return `${base} ${cursor} bg-red-950 border-red-800 text-red-400 hover:bg-red-900`;
    default:
      return `${base} ${cursor} bg-zinc-800 border-zinc-700 text-zinc-400 hover:bg-zinc-700`;
  }
}

export interface StepperRibbonProps {
  currentStep: number;
  completedSteps?: Set<number>;
  errorSteps?: Set<number>;
  onStepClick?: (step: number) => void;
  inline?: boolean;
}

export function StepperRibbon({
  currentStep,
  completedSteps = new Set(),
  errorSteps = new Set(),
  onStepClick,
  inline = false,
}: StepperRibbonProps) {
  const getStatus = (id: number): StepStatus => {
    if (errorSteps.has(id)) return 'error';
    if (completedSteps.has(id)) return 'complete';
    if (id === currentStep) return 'active';
    return 'pending';
  };

  const stepButtons = STEPS.map((step, idx) => {
    const status = getStatus(step.id);
    const clickable = !!onStepClick;
    return (
      <div key={step.id} className="flex items-center gap-2">
        <InfoTooltip id={`stepper-step-${step.id}`}>
          <button
            className={stepClasses(status, clickable)}
            onClick={() => onStepClick?.(step.id)}
            aria-current={status === 'active' ? 'step' : undefined}
            title={step.tooltip}
          >
            <span aria-hidden="true">{step.icon}</span>
            {step.name}
            {status === 'complete' && <span className="ml-1 text-emerald-400" aria-label="complete">✓</span>}
            {status === 'error' && <span className="ml-1 text-red-400" aria-label="error">✗</span>}
          </button>
        </InfoTooltip>
        {idx < STEPS.length - 1 && (
          <span className="text-zinc-600 text-sm" aria-hidden="true">→</span>
        )}
      </div>
    );
  });

  if (inline) {
    return <>{stepButtons}</>;
  }

  return (
    <div className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-900 px-6 py-2 flex-shrink-0">
      {stepButtons}
    </div>
  );
}
