'use client';

import React, { useState, useCallback } from 'react';
import { DataSource, DataVerificationResult } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
      <div className="flex" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <button
          onClick={() => setActiveTab('sources')}
          className="px-4 py-2 border-b-2 font-medium transition-colors"
          style={
            activeTab === 'sources'
              ? {
                  borderBottomColor: 'var(--accent-blue)',
                  color: 'var(--accent-blue)',
                }
              : {
                  borderBottomColor: 'transparent',
                  color: 'var(--text-secondary)',
                }
          }
          onMouseEnter={
            activeTab !== 'sources'
              ? (e) => {
                  (e.currentTarget as HTMLButtonElement).style.color =
                    'var(--text-primary)';
                }
              : undefined
          }
          onMouseLeave={
            activeTab !== 'sources'
              ? (e) => {
                  (e.currentTarget as HTMLButtonElement).style.color =
                    'var(--text-secondary)';
                }
              : undefined
          }
        >
          Data Sources
        </button>
        <button
          onClick={() => setActiveTab('verification')}
          className="px-4 py-2 border-b-2 font-medium transition-colors"
          style={
            activeTab === 'verification'
              ? {
                  borderBottomColor: 'var(--accent-blue)',
                  color: 'var(--accent-blue)',
                }
              : {
                  borderBottomColor: 'transparent',
                  color: 'var(--text-secondary)',
                }
          }
          onMouseEnter={
            activeTab !== 'verification'
              ? (e) => {
                  (e.currentTarget as HTMLButtonElement).style.color =
                    'var(--text-primary)';
                }
              : undefined
          }
          onMouseLeave={
            activeTab !== 'verification'
              ? (e) => {
                  (e.currentTarget as HTMLButtonElement).style.color =
                    'var(--text-secondary)';
                }
              : undefined
          }
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
                      className="flex items-center justify-between p-3 rounded-lg"
                      style={{
                        border: '1px solid var(--border-subtle)',
                        backgroundColor: 'var(--bg-panel)',
                      }}
                    >
                      <div className="flex-1">
                        <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                          {source.name}
                        </p>
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                          {source.type}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                          Last updated: {source.lastUpdated.toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor:
                              source.status === 'active'
                                ? 'var(--bg-panel-raised)'
                                : source.status === 'inactive'
                                  ? 'var(--bg-panel-raised)'
                                  : 'var(--bg-panel-raised)',
                            color:
                              source.status === 'active'
                                ? 'var(--color-bullish)'
                                : source.status === 'inactive'
                                  ? 'var(--text-secondary)'
                                  : 'var(--color-bearish)',
                          }}
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
                <p className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
                  No data sources configured
                </p>
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
                    <div className="max-h-64 overflow-y-auto rounded-lg" style={{ border: '1px solid var(--border-subtle)' }}>
                      <table className="w-full text-sm">
                        <thead style={{ backgroundColor: 'var(--bg-panel-raised)', position: 'sticky', top: 0 }}>
                          <tr>
                            <th className="px-3 py-2 text-left font-medium" style={{ color: 'var(--text-primary)' }}>
                              Start
                            </th>
                            <th className="px-3 py-2 text-left font-medium" style={{ color: 'var(--text-primary)' }}>
                              End
                            </th>
                            <th className="px-3 py-2 text-left font-medium" style={{ color: 'var(--text-primary)' }}>
                              Bars
                            </th>
                            <th className="px-3 py-2 text-left font-medium" style={{ color: 'var(--text-primary)' }}>
                              Status
                            </th>
                          </tr>
                        </thead>
                        <tbody style={{ borderTop: '1px solid var(--border-subtle)' }}>
                          {result.gaps.map((gap, idx) => (
                            <tr
                              key={idx}
                              style={{
                                borderBottom: '1px solid var(--border-subtle)',
                              }}
                              onMouseEnter={(e) => {
                                (e.currentTarget as HTMLTableRowElement).style.backgroundColor = 'var(--bg-panel-raised)';
                              }}
                              onMouseLeave={(e) => {
                                (e.currentTarget as HTMLTableRowElement).style.backgroundColor = 'transparent';
                              }}
                            >
                              <td className="px-3 py-2" style={{ color: 'var(--text-primary)' }}>
                                {gap.startTime.toLocaleDateString()}
                              </td>
                              <td className="px-3 py-2" style={{ color: 'var(--text-primary)' }}>
                                {gap.endTime.toLocaleDateString()}
                              </td>
                              <td className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>
                                {gap.missingBars}
                              </td>
                              <td className="px-3 py-2">
                                <span
                                  className="inline-flex px-2 py-1 rounded text-xs font-medium"
                                  style={{
                                    backgroundColor: 'var(--bg-panel-raised)',
                                    color: gap.repairable ? 'var(--color-bullish)' : 'var(--color-warning)',
                                  }}
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
                <p className="text-center" style={{ color: 'var(--text-secondary)' }}>
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
