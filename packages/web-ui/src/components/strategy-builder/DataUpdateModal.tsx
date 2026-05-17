'use client';

import React, { useState, useCallback } from 'react';

export interface DataUpdateProgress {
  current: number;
  total: number;
  message: string;
}

export interface DataUpdateModalProps {
  open: boolean;
  /** ISO date string for start of gap */
  gapStartDate?: string;
  /** ISO date string for cutoff */
  cutoffDate?: string;
  onUpdate: (startDate: string, endDate: string) => Promise<void>;
  onSkip: () => void;
  progress?: DataUpdateProgress;
  isRunning?: boolean;
  result?: { success: boolean; message: string } | null;
}

export const DataUpdateModal: React.FC<DataUpdateModalProps> = ({
  open,
  gapStartDate,
  cutoffDate,
  onUpdate,
  onSkip,
  progress,
  isRunning = false,
  result,
}) => {
  const [startDate, setStartDate] = useState(
    gapStartDate ?? new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  );
  const [endDate, setEndDate] = useState(
    cutoffDate ?? new Date().toISOString().slice(0, 10)
  );

  const handleUpdate = useCallback(async () => {
    await onUpdate(startDate, endDate);
  }, [startDate, endDate, onUpdate]);

  if (!open) return null;

  const progressPct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-xl mx-4">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-xl">📥</span>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Data Update</h2>
            <p className="text-xs text-zinc-400">Strategy Builder Startup Check</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-4">
          {!isRunning && !result && (
            <>
              <p className="text-sm text-zinc-400">
                Missing market data detected. Download candle data from Binance to ensure accurate
                backtesting.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-zinc-300">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-zinc-300">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            </>
          )}

          {isRunning && (
            <div className="space-y-3">
              <p className="text-sm text-zinc-300">Downloading data from Binance...</p>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-zinc-400">
                <span>{progress?.message ?? 'Initializing...'}</span>
                <span>{progressPct}%</span>
              </div>
            </div>
          )}

          {result && (
            <div
              className={`flex items-start gap-3 p-4 rounded border ${
                result.success
                  ? 'bg-green-900/20 border-green-700 text-green-300'
                  : 'bg-red-900/20 border-red-700 text-red-300'
              }`}
            >
              <span className="text-lg">{result.success ? '✅' : '❌'}</span>
              <p className="text-sm">{result.message}</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-700">
          {!isRunning && !result && (
            <>
              <button
                onClick={onSkip}
                className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
              >
                Skip
              </button>
              <button
                onClick={handleUpdate}
                className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Download Data
              </button>
            </>
          )}
          {result && (
            <button
              onClick={onSkip}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataUpdateModal;
