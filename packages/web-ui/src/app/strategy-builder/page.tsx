'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { StrategyBuilder } from '@/components/strategy-builder/StrategyBuilder';

function StrategyBuilderContent() {
  const searchParams = useSearchParams();
  const strategyId = searchParams.get('id');

  return <StrategyBuilder strategyId={strategyId ?? undefined} />;
}

export function StrategyBuilderPageWrapper() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full bg-zinc-950">Loading...</div>}>
      <StrategyBuilderContent />
    </Suspense>
  );
}

export default StrategyBuilderPageWrapper;
