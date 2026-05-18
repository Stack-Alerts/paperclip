'use client';

import { useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockSearchPanel } from './BlockSearchPanel';
import { StrategyBlocksPanel } from './StrategyBlocksPanel';
import { StrategyInfoPanel } from './StrategyInfoPanel';

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
      <div className="flex items-center justify-center h-full bg-zinc-950">
        <div className="text-zinc-50">Loading strategy...</div>
      </div>
    );
  }

  if (strategyError) {
    return (
      <div className="flex items-center justify-center h-full bg-zinc-950">
        <div className="text-red-500">Error: {strategyError}</div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-zinc-950 overflow-hidden">
      {/* LEFT PANEL ~40%: Strategy Info (top) + Strategy Building Blocks (bottom) */}
      <div className="flex flex-col border-r border-zinc-800 overflow-hidden" style={{ width: '40%', minWidth: 0 }}>
        {/* Section 1: Strategy Information — compact, scrollable if tall */}
        <div className="flex-shrink-0 border-b border-zinc-800 overflow-y-auto" style={{ maxHeight: '45%' }}>
          <StrategyInfoPanel />
        </div>
        {/* Section 2+3: Strategy Building Blocks + Exit Conditions */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <StrategyBlocksPanel />
        </div>
      </div>

      {/* RIGHT PANEL ~60%: Available Building Blocks library */}
      <div className="flex-1 min-w-0 overflow-hidden">
        <BlockSearchPanel />
      </div>
    </div>
  );
}
