'use client';

import { Suspense, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { BacktestConfigDialog } from '@/components/strategy-builder/BacktestConfigDialog';
import { Providers } from '@/components/strategy-builder/Providers';
import { TooltipSettingsProvider } from '@/components/strategy-builder/TooltipSettingsContext';
import { TOOLTIP_REGISTRY } from '@/lib/tooltip-registry';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

function buildTooltipMap(): Record<string, string> {
  const flat: Record<string, string> = {};
  for (const [mod, fields] of Object.entries(TOOLTIP_REGISTRY)) {
    for (const [field, tip] of Object.entries(fields)) {
      flat[`${mod}.${field}`] = tip.description;
    }
  }
  return flat;
}

function BacktestConfigPopoutInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loadStrategy, currentStrategy } = useStrategyStore();

  // If the opener passed a strategy id on the query string (BTCAAAAA-34600
  // popout flow), hydrate the standalone window's store so the dialog shows
  // the same strategy the inline view had loaded. Matches the
  // /strategy-builder?id=... seeding pattern.
  const strategyId = searchParams.get('strategyId');
  useEffect(() => {
    if (strategyId && currentStrategy?.id !== strategyId) {
      loadStrategy(strategyId).catch(() => {
        /* surface the empty state in the dialog header */
      });
    }
  }, [strategyId, currentStrategy?.id, loadStrategy]);

  const handleClose = useCallback(() => {
    if (typeof window !== 'undefined' && window.opener) {
      window.close();
    } else {
      router.push('/strategy-builder');
    }
  }, [router]);

  return (
    <Providers tooltips={buildTooltipMap()}>
      <TooltipSettingsProvider>
        {/* height:100% (not 100vh) so the dialog fills only the space above the
            global Status bar; 100vh overflowed the layout's flex area and the
            Status bar clipped the footer Run Test / Cancel buttons
            (BTCAAAAA-36504). */}
        <div style={{ width: '100%', height: '100%', background: 'var(--app-bg)' }}>
          <BacktestConfigDialog
            open={true}
            onClose={handleClose}
            standalone={true}
          />
        </div>
      </TooltipSettingsProvider>
    </Providers>
  );
}

export default function BacktestConfigPopoutPage() {
  // useSearchParams() requires a Suspense boundary in the Next.js App Router.
  return (
    <Suspense fallback={null}>
      <BacktestConfigPopoutInner />
    </Suspense>
  );
}
