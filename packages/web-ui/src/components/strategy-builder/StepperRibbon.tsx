'use client';

import React from 'react';
import { Pencil, CheckCircle, Zap, Upload } from 'lucide-react';
import { RichTooltip, TooltipContent } from './RichTooltip';

export type StepStatus = 'pending' | 'active' | 'complete' | 'error';

export interface Step {
  id: number;
  name: string;
  icon: React.ReactNode;
  tooltip: TooltipContent;
}

const ICON_PROPS = { size: 14, strokeWidth: 1.5 } as const;

const STEPS: Step[] = [
  {
    id: 0,
    name: 'Design',
    icon: <Pencil {...ICON_PROPS} />,
    tooltip: {
      title: 'Design',
      body: 'Build your strategy using building blocks — entry conditions, signals, and exit rules.',
      sections: [
        {
          header: 'Available blocks:',
          items: [
            'Entry Conditions (AND / OR logic)',
            'Signals with optional RECHECK validation',
            'Timing constraints between signals',
            'Exit Conditions at Strategy, Block, or Signal level',
          ],
        },
        {
          header: 'Best practice:',
          items: ['Start with required AND blocks, then add optional OR boosters for confluence'],
        },
      ],
    },
  },
  {
    id: 1,
    name: 'Validate',
    icon: <CheckCircle {...ICON_PROPS} />,
    tooltip: {
      title: 'Validate',
      body: 'Run structural validation to confirm all required blocks, signals, and exit conditions are correctly configured.',
      sections: [
        {
          header: 'Checks performed:',
          items: [
            'Required AND blocks are present and fully configured',
            'All signals have valid parameters',
            'Exit conditions are bound to the correct level',
            'No conflicting logic or missing required fields',
          ],
        },
        {
          header: 'Status:',
          items: [
            'Green — validation passed, ready to backtest',
            'Red — errors found, resolve before testing',
          ],
        },
      ],
    },
  },
  {
    id: 2,
    name: 'Test/Optimize',
    icon: <Zap {...ICON_PROPS} />,
    tooltip: {
      title: 'Test / Optimize',
      body: 'Run a full historical backtest to evaluate strategy performance and tune parameters.',
      sections: [
        {
          header: 'Backtest options:',
          items: [
            'Full backtest over a configurable date range',
            'Quick Preview — 30-day snapshot',
          ],
        },
        {
          header: 'Key metrics reported:',
          items: [
            'Win rate and average return per trade',
            'Max drawdown and Sharpe ratio',
            'Signal distribution and total entry count',
          ],
        },
      ],
    },
  },
  {
    id: 3,
    name: 'Publish',
    icon: <Upload {...ICON_PROPS} />,
    tooltip: {
      title: 'Publish',
      body: 'Promote the strategy to Active status, making it available for live execution.',
      sections: [
        {
          header: 'Requirements:',
          items: [
            'Strategy must have passed validation (step 2)',
            'At least one full backtest must be complete (step 3)',
          ],
        },
        {
          header: 'Status options:',
          items: [
            'Active — live execution enabled',
            'Archived — disabled but preserved in history',
          ],
        },
      ],
    },
  },
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
        <RichTooltip content={step.tooltip}>
          <button
            className={stepClasses(status, clickable)}
            style={status === 'active' ? ACTIVE_STYLE : undefined}
            onClick={() => onStepClick?.(step.id)}
            aria-current={status === 'active' ? 'step' : undefined}
          >
            <span aria-hidden="true">{step.icon}</span>
            {step.name}
            {status === 'complete' && <span className="ml-1 text-emerald-400" aria-label="complete">✓</span>}
            {status === 'error' && <span className="ml-1 text-red-400" aria-label="error">✗</span>}
          </button>
        </RichTooltip>
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
