'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { DataSource, DataVerificationResult, DataGap } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export interface DataManagementPanelProps {
  dataSources?: DataSource[];
  onVerify?: () => void;
  onUpdate?: (dataSourceId: string) => void;
  onRepair?: (gapIds: string[]) => void;
  verificationResults?: DataVerificationResult[];
  disabled?: boolean;
}

/**
 * DataManagementPanel - React port of PyQt5 Data Management modules
 *
 * Provides data source management and verification with:
 * - Data source listing and management
 * - Gap detection and classification
 * - Repair capability for gaps within Binance API horizon
 * - Status indicators for data integrity
 */
export const DataManagementPanel: React.FC<DataManagementPanelProps> = ({
  dataSources = [],
  onVerify,
  onUpdate,
  onRepair,
  verificationResults = [],
  disabled = false,
}) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [activeTab, setActiveTab] = useState<'sources' | 'verification'>('sources');

  const handleVerify = useCallback(async () => {
    setIsVerifying(true);
    try {
      await onVerify?.();
    } finally {
      setIsVerifying(false);
    }
  }, [onVerify]);

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('sources')}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'sources'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Data Sources
        </button>
        <button
          onClick={() => setActiveTab('verification')}
          className={`px-4 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'verification'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Verification
        </button>
      </div>

      {/* Data Sources Tab */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Data Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {dataSources.length > 0 ? (
                <div className="space-y-3">
                  {dataSources.map((source) => (
                    <div
                      key={source.id}
                      className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{source.name}</p>
                        <p className="text-sm text-gray-600">{source.type}</p>
                        <p className="text-xs text-gray-500">
                          Last updated: {source.lastUpdated.toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            source.status === 'active'
                              ? 'bg-green-100 text-green-800'
                              : source.status === 'inactive'
                              ? 'bg-gray-100 text-gray-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {source.status}
                        </span>
                        <Button
                          size="sm"
                          onClick={() => onUpdate?.(source.id)}
                          disabled={disabled}
                        >
                          Update
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No data sources configured</p>
              )}
            </CardContent>
          </Card>

          <Button
            onClick={handleVerify}
            disabled={disabled || isVerifying || dataSources.length === 0}
            className="w-full"
          >
            {isVerifying ? 'Verifying...' : 'Verify Data Integrity'}
          </Button>
        </div>
      )}

      {/* Verification Tab */}
      {activeTab === 'verification' && (
        <div className="space-y-4">
          {verificationResults.length > 0 ? (
            verificationResults.map((result) => (
              <Card key={`${result.symbol}-${result.timeframe}`}>
                <CardHeader>
                  <CardTitle>
                    {result.symbol} - {result.timeframe}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <Label className="text-xs">Total Gaps</Label>
                      <p className="text-lg font-semibold">{result.totalGaps}</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Repairable</Label>
                      <p className="text-lg font-semibold text-green-600">{result.repairableGaps}</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Too Old</Label>
                      <p className="text-lg font-semibold text-orange-600">{result.tooOldGaps}</p>
                    </div>
                  </div>

                  {result.repairableGaps > 0 && (
                    <Button
                      onClick={() =>
                        onRepair?.(result.gaps.filter((g) => g.repairable).map((g) => g.startTime.toISOString()))
                      }
                      disabled={disabled}
                      className="w-full"
                    >
                      Repair Gaps
                    </Button>
                  )}

                  {result.gaps.length > 0 && (
                    <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium text-gray-700">Start</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-700">End</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-700">Bars</th>
                            <th className="px-3 py-2 text-left font-medium text-gray-700">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {result.gaps.map((gap, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-3 py-2 text-gray-900">
                                {gap.startTime.toLocaleDateString()}
                              </td>
                              <td className="px-3 py-2 text-gray-900">
                                {gap.endTime.toLocaleDateString()}
                              </td>
                              <td className="px-3 py-2 text-gray-700">{gap.missingBars}</td>
                              <td className="px-3 py-2">
                                <span
                                  className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                                    gap.repairable
                                      ? 'bg-green-100 text-green-800'
                                      : 'bg-orange-100 text-orange-800'
                                  }`}
                                >
                                  {gap.repairable ? 'Repairable' : 'Too Old'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="py-8">
                <p className="text-gray-500 text-center">
                  Run verification to check data integrity
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

export default DataManagementPanel;
