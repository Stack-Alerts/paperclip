'use client';

import { Suspense, useCallback, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { StrategyBuilder } from './StrategyBuilder';
import { AiRecommendationsPanel } from '@/components/backtest/ai-recommendations/AiRecommendationsPanel';

type WorkspaceTab = 'build' | 'recommendations';

function isWorkspaceTab(value: string | null): value is WorkspaceTab {
  return value === 'build' || value === 'recommendations';
}

function StrategyBuilderContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const strategyId = searchParams.get('id');
  const tabParam = searchParams.get('tab');
  const tab: WorkspaceTab = isWorkspaceTab(tabParam) ? tabParam : 'build';

  const setTab = useCallback(
    (next: WorkspaceTab) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === 'build') {
        params.delete('tab');
      } else {
        params.set('tab', next);
      }
      const query = params.toString();
      router.push(query ? `${pathname}?${query}` : pathname);
    },
    [pathname, router, searchParams],
  );

  const tabs = useMemo(
    () =>
      [
        { id: 'build' as const, label: 'Build' },
        { id: 'recommendations' as const, label: 'AI Recommendations' },
      ],
    [],
  );

  return (
    <div className="flex h-full min-h-0 flex-col" style={{ background: 'var(--shell-bg)' }}>
      <div
        role="tablist"
        aria-label="Strategy builder workspace"
        className="flex flex-shrink-0 items-center gap-1 border-b px-3"
        style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}
      >
        {tabs.map((entry) => {
          const selected = entry.id === tab;
          return (
            <button
              key={entry.id}
              type="button"
              role="tab"
              id={`strategy-builder-tab-${entry.id}`}
              aria-selected={selected}
              aria-controls="strategy-builder-tab-panel"
              onClick={() => setTab(entry.id)}
              className="relative px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-0"
              style={{
                color: selected ? 'var(--text-primary)' : 'var(--text-muted)',
                borderBottom: selected
                  ? '2px solid var(--accent-blue)'
                  : '2px solid transparent',
                marginBottom: '-1px',
                background: 'transparent',
              }}
            >
              {entry.label}
            </button>
          );
        })}
      </div>
      <div
        id="strategy-builder-tab-panel"
        role="tabpanel"
        aria-labelledby={`strategy-builder-tab-${tab}`}
        className="flex-1 min-h-0 overflow-auto"
      >
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
