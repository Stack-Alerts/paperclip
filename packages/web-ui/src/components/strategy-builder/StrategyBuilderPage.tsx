'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { StrategyBuilder } from './StrategyBuilder';
import { AiRecommendationsPanel } from '@/components/backtest/ai-recommendations/AiRecommendationsPanel';

type WorkspaceTab = 'build' | 'recommendations';

function isWorkspaceTab(value: string | null): value is WorkspaceTab {
  return value === 'build' || value === 'recommendations';
}

function StrategyBuilderContent() {
  const searchParams = useSearchParams();
  const strategyId = searchParams.get('id');
  const tabParam = searchParams.get('tab');
  const tab: WorkspaceTab = isWorkspaceTab(tabParam) ? tabParam : 'build';

  return (
    <div className="flex h-full min-h-0 flex-col" style={{ background: 'var(--shell-bg)' }}>
      <div className="flex-1 min-h-0 overflow-auto">
        {tab === 'recommendations' ? (
          <AiRecommendationsPanel />
        ) : (
          <StrategyBuilder strategyId={strategyId ?? undefined} />
        )}
      </div>
    </div>
  );
}

export function StrategyBuilderPageWrapper() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full" style={{ background: 'var(--bg-deep)' }}>Loading...</div>}>
      <StrategyBuilderContent />
    </Suspense>
  );
}
