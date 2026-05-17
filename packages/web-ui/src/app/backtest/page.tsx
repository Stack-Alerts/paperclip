'use client';

import { AppLayout } from '@/components/shared/AppLayout';
import { BacktestConfigPanel } from '@/components/strategy-builder/BacktestConfigPanel';
import { Providers } from '@/components/strategy-builder/Providers';

export default function BacktestPage() {
  return (
    <AppLayout>
      <Providers tooltips={{}}>
        <div className="p-8">
          <BacktestConfigPanel open={true} onClose={() => {}} />
        </div>
      </Providers>
    </AppLayout>
  );
}
