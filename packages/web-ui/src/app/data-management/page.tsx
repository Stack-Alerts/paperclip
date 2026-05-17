'use client';

import { useState, useCallback } from 'react';
import { AppLayout } from '@/components/shared/AppLayout';
import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';
import type { DataSource, DataVerificationResult } from '@/types';

const INITIAL_SOURCES: DataSource[] = [
  { id: '1', name: 'Binance 15m', type: 'binance', status: 'active', lastUpdated: new Date() },
  { id: '2', name: 'Binance 1h', type: 'binance', status: 'active', lastUpdated: new Date() },
];

export default function DataManagementPage() {
  const [dataSources] = useState<DataSource[]>(INITIAL_SOURCES);
  const [verificationResults, setVerificationResults] = useState<DataVerificationResult[]>([]);

  const handleVerify = useCallback(async () => {
    await new Promise((r) => setTimeout(r, 800));
    setVerificationResults([
      {
        symbol: 'BTCUSDT',
        timeframe: '15m',
        totalGaps: 3,
        repairableGaps: 2,
        tooOldGaps: 1,
        gaps: [
          { startTime: new Date('2024-05-01'), endTime: new Date('2024-05-02'), missingBars: 96, repairable: true },
          { startTime: new Date('2024-04-15'), endTime: new Date('2024-04-16'), missingBars: 96, repairable: true },
          { startTime: new Date('2023-05-01'), endTime: new Date('2023-05-02'), missingBars: 96, repairable: false, reason: 'Gap predates Binance API 90-day horizon' },
        ],
      },
    ]);
  }, []);

  return (
    <AppLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Data Management</h2>
          <p className="text-gray-600 mt-1">Verify and manage market data sources</p>
        </div>
        <DataManagementPanel dataSources={dataSources} onVerify={handleVerify} verificationResults={verificationResults} />
      </div>
    </AppLayout>
  );
}
