'use client';

import { useState, useCallback } from 'react';
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

  const [config, setConfig] = useState<Omit<BacktestConfig, 'strategyId'>>(() => ({
    ...defaultConfig,
    startDate: daysAgo(90),
    endDate: today(),
  }));
  const [error, setError] = useState<string | null>(null);

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

      <div className="relative w-full max-w-xl rounded-lg shadow-2xl mx-4" style={{ border: '1px solid var(--border)', background: 'var(--bg-panel)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--bg-card)' }}>
          <h2 id="backtest-dialog-title" className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>
            🧪 Backtest Configuration
          </h2>
          <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-muted)' }} aria-label="Close dialog">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Date range presets */}
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Lookback Preset</p>
            <div className="flex gap-2">
              {PRESET_DAYS.map((d) => (
                <InfoTooltip key={d} id={`backtest-preset-${d}`}>
                  <button
                    onClick={() => applyPreset(d)}
                    className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
                    style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
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
              <label htmlFor="bt-start" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Start Date</label>
              <InfoTooltip id="backtest-start-date">
                <input
                  id="bt-start"
                  type="date"
                  value={config.startDate}
                  onChange={(e) => patch('startDate', e.target.value)}
                  className="w-full px-3 py-2 rounded text-sm focus:outline-none"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                />
              </InfoTooltip>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="bt-end" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>End Date</label>
              <InfoTooltip id="backtest-end-date">
                <input
                  id="bt-end"
                  type="date"
                  value={config.endDate}
                  onChange={(e) => patch('endDate', e.target.value)}
                  className="w-full px-3 py-2 rounded text-sm focus:outline-none"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                />
              </InfoTooltip>
            </div>
          </div>

          {/* Capital & commission */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="bt-capital" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Initial Capital (USD)</label>
              <InfoTooltip id="backtest-initial-capital">
                <input
                  id="bt-capital"
                  type="number"
                  min={100}
                  step={1000}
                  value={config.initialCapital}
                  onChange={(e) => patch('initialCapital', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 rounded text-sm focus:outline-none"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                />
              </InfoTooltip>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="bt-commission" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Commission (fraction)</label>
              <InfoTooltip id="backtest-commission">
                <input
                  id="bt-commission"
                  type="number"
                  min={0}
                  max={0.05}
                  step={0.0001}
                  value={config.commissionPercentage}
                  onChange={(e) => patch('commissionPercentage', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 rounded text-sm focus:outline-none"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                />
              </InfoTooltip>
              <p className="text-xs" style={{ color: 'var(--text-faintest)' }}>e.g. 0.001 = 0.1%</p>
            </div>
          </div>

          {/* Progress bar */}
          {backTestInProgress && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
                <span>Running…</span>
                <span>{backTestProgress}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-card)' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${backTestProgress}%`, background: 'var(--accent-blue)' }}
                />
              </div>
            </div>
          )}

          {error && <p className="text-xs" style={{ color: 'var(--accent-red)' }}>{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4" style={{ borderTop: '1px solid var(--bg-card)' }}>
          <InfoTooltip id="backtest-cancel-btn">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              Cancel
            </button>
          </InfoTooltip>
          <InfoTooltip id="backtest-run-btn">
            <button
              onClick={handleRun}
              disabled={!canRun}
              className="px-4 py-2 rounded text-sm font-medium disabled:opacity-50 transition-colors"
              style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            >
              {backTestInProgress ? 'Running…' : '▶ Run Backtest'}
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}
