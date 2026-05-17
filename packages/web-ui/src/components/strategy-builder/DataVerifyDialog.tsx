'use client';

import React, { useState, useCallback } from 'react';

export interface DataGapEntry {
  gapStart: string;
  gapEnd: string;
  missingBars: number;
  repairable: boolean;
  reason?: string;
}

export interface TimeframeVerifyResult {
  timeframe: string;
  totalGaps: number;
  repairableCount: number;
  tooOldCount: number;
  totalMissingBars: number;
  gaps: DataGapEntry[];
}

export interface DataVerifyDialogProps {
  open: boolean;
  onVerify: () => Promise<Record<string, TimeframeVerifyResult>>;
  onRepair: (timeframe: string) => Promise<void>;
  onClose: () => void;
}

export const DataVerifyDialog: React.FC<DataVerifyDialogProps> = ({
  open,
  onVerify,
  onRepair,
  onClose,
}) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [isRepairing, setIsRepairing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, TimeframeVerifyResult> | null>(null);
  const [error, setError] = useState('');

  const handleVerify = useCallback(async () => {
    setIsVerifying(true);
    setError('');
    try {
      const res = await onVerify();
      setResults(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsVerifying(false);
    }
  }, [onVerify]);

  const handleRepair = useCallback(
    async (tf: string) => {
      setIsRepairing(tf);
      try {
        await onRepair(tf);
        // Re-verify after repair
        const res = await onVerify();
        setResults(res);
      } catch (e) {
        setError(String(e));
      } finally {
        setIsRepairing(null);
      }
    },
    [onRepair, onVerify]
  );

  if (!open) return null;

  const tfResults = results ? Object.values(results) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-zinc-700 px-6 py-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">🔍</span>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">Data Verification</h2>
              <p className="text-xs text-zinc-400">Gap detection and repair for OHLCV data</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {!results && !isVerifying && (
            <div className="text-center py-12">
              <p className="text-zinc-400 text-sm mb-4">
                Run verification to detect gaps in your stored OHLCV data.
              </p>
              <button
                onClick={handleVerify}
                className="px-5 py-2.5 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Run Verification
              </button>
            </div>
          )}

          {isVerifying && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-zinc-400 text-sm">Scanning data files...</p>
            </div>
          )}

          {tfResults.map((tfResult) => (
            <div key={tfResult.timeframe} className="bg-zinc-800/50 rounded-lg border border-zinc-700">
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-zinc-100">{tfResult.timeframe}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      tfResult.totalGaps === 0
                        ? 'bg-green-900/40 text-green-400'
                        : 'bg-red-900/40 text-red-400'
                    }`}
                  >
                    {tfResult.totalGaps === 0 ? '✓ Clean' : `${tfResult.totalGaps} gaps`}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-zinc-400">
                  <span>
                    Repairable:{' '}
                    <span className="text-green-400 font-medium">{tfResult.repairableCount}</span>
                  </span>
                  <span>
                    Too Old:{' '}
                    <span className="text-orange-400 font-medium">{tfResult.tooOldCount}</span>
                  </span>
                  <span>
                    Missing Bars:{' '}
                    <span className="text-zinc-300 font-medium">{tfResult.totalMissingBars}</span>
                  </span>
                  {tfResult.repairableCount > 0 && (
                    <button
                      onClick={() => handleRepair(tfResult.timeframe)}
                      disabled={isRepairing === tfResult.timeframe}
                      className="px-3 py-1 rounded bg-green-700 text-white text-xs font-medium hover:bg-green-600 disabled:opacity-50 transition-colors"
                    >
                      {isRepairing === tfResult.timeframe ? 'Repairing...' : 'Repair Gaps'}
                    </button>
                  )}
                </div>
              </div>

              {tfResult.gaps.length > 0 && (
                <div className="overflow-x-auto max-h-48">
                  <table className="w-full text-xs border-collapse">
                    <thead className="bg-zinc-800 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Start</th>
                        <th className="px-3 py-2 text-left text-zinc-400 font-semibold">End</th>
                        <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Missing</th>
                        <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Status</th>
                        <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Reason</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-700/50">
                      {tfResult.gaps.map((gap, i) => (
                        <tr key={i} className="hover:bg-zinc-700/20">
                          <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapStart}</td>
                          <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapEnd}</td>
                          <td className="px-3 py-1.5 text-zinc-300">{gap.missingBars}</td>
                          <td className="px-3 py-1.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-xs ${
                                gap.repairable
                                  ? 'bg-green-900/40 text-green-400'
                                  : 'bg-orange-900/40 text-orange-400'
                              }`}
                            >
                              {gap.repairable ? 'Repairable' : 'Too Old'}
                            </span>
                          </td>
                          <td className="px-3 py-1.5 text-zinc-500">{gap.reason ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-between px-6 py-4 border-t border-zinc-700 flex-shrink-0">
          {results && (
            <button
              onClick={handleVerify}
              disabled={isVerifying}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 disabled:opacity-50 transition-colors"
            >
              Re-verify
            </button>
          )}
          <div className="ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataVerifyDialog;
