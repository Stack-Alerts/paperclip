'use client';

import { Suspense, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Strategy } from '@/lib/strategy-builder/types';
import { StrategyBrowserDialog } from '@/components/strategy-builder/StrategyBrowserDialog';
import { Providers } from '@/components/strategy-builder/Providers';
import { TooltipSettingsProvider } from '@/components/strategy-builder/TooltipSettingsContext';
import { TOOLTIP_REGISTRY } from '@/lib/tooltip-registry';

function buildTooltipMap(): Record<string, string> {
  const flat: Record<string, string> = {};
  for (const [mod, fields] of Object.entries(TOOLTIP_REGISTRY)) {
    for (const [field, tip] of Object.entries(fields)) {
      flat[`${mod}.${field}`] = tip.description;
    }
  }
  return flat;
}

type TypeFilter = 'all' | 'bullish' | 'bearish';
type SortKey = 'name' | 'blocks' | 'updated' | 'status' | 'created' | 'version';
type SortDir = 'asc' | 'desc';

const TYPE_FILTERS: ReadonlySet<TypeFilter> = new Set(['all', 'bullish', 'bearish']);
const SORT_KEYS: ReadonlySet<SortKey> = new Set(['name', 'blocks', 'updated', 'status', 'created', 'version']);
const SORT_DIRS: ReadonlySet<SortDir> = new Set(['asc', 'desc']);

function StrategyBrowserPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleSelect = useCallback((strategy: Strategy) => {
    if (typeof window !== 'undefined' && window.opener) {
      window.opener.postMessage(
        { type: 'strategy-browser:selected', strategyId: strategy.id },
        window.location.origin,
      );
      window.close();
    } else {
      router.push(`/strategy-builder?id=${strategy.id}`);
    }
  }, [router]);

  const handleClose = useCallback(() => {
    if (typeof window !== 'undefined' && window.opener) {
      window.close();
    } else {
      router.push('/strategy-builder');
    }
  }, [router]);

  // Inherit selection + search/filter/sort from the inline view at Pop Out
  // time so the standalone window opens on the same view (BTCAAAAA-29371).
  const initialSelectedId = searchParams.get('selectedId');
  const initialSearchText = searchParams.get('q') ?? undefined;
  const typeParam = searchParams.get('type');
  const sortParam = searchParams.get('sort');
  const dirParam = searchParams.get('dir');
  const initialTypeFilter = typeParam && TYPE_FILTERS.has(typeParam as TypeFilter) ? (typeParam as TypeFilter) : undefined;
  const initialSortKey = sortParam && SORT_KEYS.has(sortParam as SortKey) ? (sortParam as SortKey) : undefined;
  const initialSortDir = dirParam && SORT_DIRS.has(dirParam as SortDir) ? (dirParam as SortDir) : undefined;

  return (
    <Providers tooltips={buildTooltipMap()}>
      <TooltipSettingsProvider>
        <div style={{ width: '100vw', height: '100vh', background: 'var(--app-bg)' }}>
          <StrategyBrowserDialog
            open={true}
            onSelect={handleSelect}
            onClose={handleClose}
            mode="open"
            standalone={true}
            initialSelectedId={initialSelectedId}
            initialSearchText={initialSearchText}
            initialTypeFilter={initialTypeFilter}
            initialSortKey={initialSortKey}
            initialSortDir={initialSortDir}
          />
        </div>
      </TooltipSettingsProvider>
    </Providers>
  );
}

export default function StrategyBrowserPage() {
  // useSearchParams() requires a Suspense boundary in the Next.js App Router.
  return (
    <Suspense fallback={null}>
      <StrategyBrowserPageInner />
    </Suspense>
  );
}
