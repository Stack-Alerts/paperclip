import { Suspense } from 'react';
import { StrategyBuilderPageWrapper } from '@/components/strategy-builder/StrategyBuilderPage';

export default function StrategyBuilderRoute() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full bg-zinc-950">Loading…</div>}>
      <StrategyBuilderPageWrapper />
    </Suspense>
  );
}
