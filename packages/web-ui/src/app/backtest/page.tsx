'use client';

import { AppLayout } from '@/components/shared/AppLayout';
import { BacktestConfigPanel } from '@/components/strategy-builder/BacktestConfigPanel';

export default function BacktestPage() {
  return (
    <AppLayout>
      <div className="p-8">
        <BacktestConfigPanel open={true} onClose={() => {}} />
      </div>
    </AppLayout>
  );
}
