'use client';

import React from 'react';
import { Pencil, CheckCircle, Zap, Upload } from 'lucide-react';
import { InfoTooltip } from './InfoTooltip';

export type StepStatus = 'pending' | 'active' | 'complete' | 'error';

export interface Step {
  id: number;
  name: string;
  icon: React.ReactNode;
  tooltip: string;
}

const ICON_PROPS = { size: 14, strokeWidth: 1.5 } as const;

const STEPS: Step[] = [
  { id: 0, name: 'Design',        icon: <Pencil {...ICON_PROPS} />,       tooltip: 'Design your trading strategy' },
  { id: 1, name: 'Validate',      icon: <CheckCircle {...ICON_PROPS} />,   tooltip: 'Validate strategy configuration' },
  { id: 2, name: 'Test/Optimize', icon: <Zap {...ICON_PROPS} />,           tooltip: 'Run backtest and optimize parameters' },
  { id: 3, name: 'Publish',       icon: <Upload {...ICON_PROPS} />,        tooltip: 'Set publish status' },
];

const BASE_CLASSES =
  'flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-all border select-none';

const ACTIVE_STYLE: React.CSSProperties = {
  background: 'rgba(46, 140, 255, 0.12)',
  borderColor: 'rgba(46, 140, 255, 0.6)',
  boxShadow: '0 0 12px rgba(46, 140, 255, 0.25), inset 0 0 8px rgba(46, 140, 255, 0.08)',
  color: '#2e8cff',
};

function stepClasses(status: StepStatus, clickable: boolean): string {
  const cursor = clickable ? 'cursor-pointer' : 'cursor-default';
  switch (status) {
    case 'active':
      return `${BASE_CLASSES} ${cursor}`;
    case 'complete':
      return `${BASE_CLASSES} ${cursor} bg-emerald-900 border-emerald-700 text-emerald-300 hover:bg-emerald-800`;
    case 'error':
      return `${BASE_CLASSES} ${cursor} bg-red-950 border-red-800 text-red-400 hover:bg-red-900`;
    default:
      return `${BASE_CLASSES} ${cursor} bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] text-[var(--text-secondary)] hover:bg-[rgba(255,255,255,0.08)] hover:text-[var(--text-primary)] hover:border-[rgba(255,255,255,0.15)]`;
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
            style={status === 'active' ? ACTIVE_STYLE : undefined}
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
          <span className="text-sm" style={{ color: 'var(--text-muted)' }} aria-hidden="true">→</span>
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
