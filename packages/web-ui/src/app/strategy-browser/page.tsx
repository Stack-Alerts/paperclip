'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
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

export default function StrategyBrowserPage() {
  const router = useRouter();

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
          />
        </div>
      </TooltipSettingsProvider>
    </Providers>
  );
}
