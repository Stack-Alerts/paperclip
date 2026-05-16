'use client';

import { useState, useCallback, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BacktestConfig } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

export interface BacktestConfigDialogProps {
  open: boolean;
  onClose: () => void;
}

const PRESET_DAYS = [30, 90, 180, 365];

const defaultConfig: Omit<BacktestConfig, 'strategyId'> = {
  startDate: '',
  endDate: '',
  initialCapital: 10000,
  commissionPercentage: 0.001,
};

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export function BacktestConfigDialog({ open, onClose }: BacktestConfigDialogProps) {
  const { currentStrategy, runBacktest, backTestInProgress, backTestProgress } = useStrategyStore();

  const [config, setConfig] = useState<Omit<BacktestConfig, 'strategyId'>>(defaultConfig);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setConfig({ ...defaultConfig, startDate: daysAgo(90), endDate: today() });
      setError(null);
    }
  }, [open]);

  const patch = useCallback(<K extends keyof typeof config>(key: K, value: (typeof config)[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }, []);

  const applyPreset = useCallback((days: number) => {
    setConfig((prev) => ({ ...prev, startDate: daysAgo(days), endDate: today() }));
  }, []);

  const handleRun = useCallback(async () => {
    if (!currentStrategy) return;
    if (!config.startDate || !config.endDate) {
      setError('Start date and end date are required.');
      return;
    }
    if (config.startDate >= config.endDate) {
      setError('Start date must be before end date.');
      return;
    }
    setError(null);
    try {
      await runBacktest({ ...config, strategyId: currentStrategy.id });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backtest failed.');
    }
  }, [config, currentStrategy, runBacktest, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => { if (e.key === 'Escape') onClose(); },
    [onClose],
  );

  if (!open) return null;

  const canRun = !!currentStrategy && !!config.startDate && !!config.endDate && !backTestInProgress;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="backtest-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-xl rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h2 id="backtest-dialog-title" className="text-base font-semibold text-zinc-50">
            🧪 Backtest Configuration
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close dialog">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Date range presets */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Lookback Preset</p>
            <div className="flex gap-2">
              {PRESET_DAYS.map((d) => (
                <InfoTooltip key={d} id={`backtest-preset-${d}`}>
                  <button
                    onClick={() => applyPreset(d)}
                    className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium border border-zinc-700 transition-colors"
                  >
                    {d}d
                  </button>
                </InfoTooltip>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="bt-start" className="text-xs text-zinc-400 font-medium">Start Date</label>
              <InfoTooltip id="backtest-start-date">
                <input
                  id="bt-start"
                  type="date"
                  value={config.startDate}
                  onChange={(e) => patch('startDate', e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                />
              </InfoTooltip>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="bt-end" className="text-xs text-zinc-400 font-medium">End Date</label>
              <InfoTooltip id="backtest-end-date">
                <input
                  id="bt-end"
                  type="date"
                  value={config.endDate}
                  onChange={(e) => patch('endDate', e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                />
              </InfoTooltip>
            </div>
          </div>

          {/* Capital & commission */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="bt-capital" className="text-xs text-zinc-400 font-medium">Initial Capital (USD)</label>
              <InfoTooltip id="backtest-initial-capital">
                <input
                  id="bt-capital"
                  type="number"
                  min={100}
                  step={1000}
                  value={config.initialCapital}
                  onChange={(e) => patch('initialCapital', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                />
              </InfoTooltip>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="bt-commission" className="text-xs text-zinc-400 font-medium">Commission (fraction)</label>
              <InfoTooltip id="backtest-commission">
                <input
                  id="bt-commission"
                  type="number"
                  min={0}
                  max={0.05}
                  step={0.0001}
                  value={config.commissionPercentage}
                  onChange={(e) => patch('commissionPercentage', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                />
              </InfoTooltip>
              <p className="text-xs text-zinc-600">e.g. 0.001 = 0.1%</p>
            </div>
          </div>

          {/* Progress bar */}
          {backTestInProgress && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-zinc-400">
                <span>Running…</span>
                <span>{backTestProgress}%</span>
              </div>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-600 rounded-full transition-all duration-300"
                  style={{ width: `${backTestProgress}%` }}
                />
              </div>
            </div>
          )}

          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-800">
          <InfoTooltip id="backtest-cancel-btn">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </InfoTooltip>
          <InfoTooltip id="backtest-run-btn">
            <button
              onClick={handleRun}
              disabled={!canRun}
              className="px-4 py-2 rounded bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {backTestInProgress ? 'Running…' : '▶ Run Backtest'}
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}
