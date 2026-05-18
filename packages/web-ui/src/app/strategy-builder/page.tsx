'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { StrategyBuilderMainWindow } from '@/components/strategy-builder/StrategyBuilderMainWindow';
import { TooltipSettingsProvider } from '@/components/strategy-builder/TooltipSettingsContext';

function StrategyBuilderContent() {
  const searchParams = useSearchParams();
  const strategyId = searchParams.get('id');

  return (
    <TooltipSettingsProvider>
      <StrategyBuilderMainWindow strategyId={strategyId ?? undefined} />
    </TooltipSettingsProvider>
  );
}

export function StrategyBuilderPageWrapper() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full bg-zinc-950">Loading...</div>}>
      <StrategyBuilderContent />
    </Suspense>
  );
}

export default StrategyBuilderPageWrapper;
