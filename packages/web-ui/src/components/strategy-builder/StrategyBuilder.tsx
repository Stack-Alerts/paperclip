'use client';

import { useEffect, useState, useCallback } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { InfoTooltip } from './InfoTooltip';
import { BlockSearchPanel } from './BlockSearchPanel';
import { StrategyBlocksPanel } from './StrategyBlocksPanel';
import { StepperRibbon } from './StepperRibbon';
import { StrategyInfoPanel } from './StrategyInfoPanel';
import { ValidationPanel } from './ValidationPanel';

function ActionBar() {
  const { saveStrategy, validateStrategy, runBacktest, currentStrategy } = useStrategyStore();

  const handleSave = useCallback(() => saveStrategy().catch(console.error), [saveStrategy]);
  const handleValidate = useCallback(() => validateStrategy().catch(console.error), [validateStrategy]);
  const handleBacktest = useCallback(() => {
    if (!currentStrategy) return;
    runBacktest({
      strategyId: currentStrategy.id,
      startDate: '',
      endDate: '',
      initialCapital: 10000,
      commissionPercentage: 0.001,
    }).catch(console.error);
  }, [currentStrategy, runBacktest]);

  return (
    <div className="border-t border-zinc-800 bg-zinc-900 px-6 py-3 flex gap-2 flex-shrink-0">
      <InfoTooltip id="save-strategy-btn">
        <button
          onClick={handleSave}
          className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Save
        </button>
      </InfoTooltip>
      <InfoTooltip id="validate-btn">
        <button
          onClick={handleValidate}
          className="px-4 py-2 rounded bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
        >
          Validate
        </button>
      </InfoTooltip>
      <InfoTooltip id="backtest-btn">
        <button
          onClick={handleBacktest}
          disabled={!currentStrategy}
          className="px-4 py-2 rounded bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
        >
          Backtest
        </button>
      </InfoTooltip>
    </div>
  );
}

export interface StrategyBuilderProps {
  strategyId?: string;
}

export function StrategyBuilder({ strategyId }: StrategyBuilderProps) {
  const {
    currentStrategy,
    isLoadingStrategy,
    strategyError,
    loadStrategy,
    createStrategy,
    loadBlockLibrary,
  } = useStrategyStore();

  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps] = useState<Set<number>>(new Set());
  const [errorSteps] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (strategyId) {
      loadStrategy(strategyId).catch(console.error);
    } else {
      if (!currentStrategy) {
        createStrategy('Untitled Strategy', 'New strategy').catch(console.error);
      }
    }
    loadBlockLibrary().catch(console.error);
  }, [strategyId, currentStrategy, loadStrategy, createStrategy, loadBlockLibrary]);

  if (isLoadingStrategy) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-950">
        <div className="text-zinc-50">Loading strategy...</div>
      </div>
    );
  }

  if (strategyError) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-950">
        <div className="text-red-500">Error: {strategyError}</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-950">
      {/* Stepper Ribbon */}
      <StepperRibbon
        currentStep={currentStep}
        completedSteps={completedSteps}
        errorSteps={errorSteps}
        onStepClick={setCurrentStep}
      />

      {/* Main Content Area - Three Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel: Block Search */}
        <div className="w-64 flex-shrink-0">
          <BlockSearchPanel />
        </div>

        {/* Center Panel: Strategy Blocks */}
        <div className="flex-1 min-w-0">
          <StrategyBlocksPanel />
        </div>

        {/* Right Panel: Strategy Info */}
        <div className="w-72 flex-shrink-0">
          <StrategyInfoPanel />
        </div>
      </div>

      {/* Validation Panel */}
      <ValidationPanel />

      {/* Action Bar */}
      <ActionBar />
    </div>
  );
}
