'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { X, Play, Square, Pause, RotateCcw, Settings, Terminal, TrendingUp, BarChart3, Sparkles, GitCompare } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BacktestConfig, BacktestStatusMessage } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';
import { LiveOutputPanel } from '@/components/backtest/live-output/LiveOutputPanel';
import { TradesPanel } from '@/components/backtest/trades/TradesPanel';
import { MetricsPanel } from '@/components/backtest/metrics/MetricsPanel';
import { AiRecommendationsPanel } from '@/components/backtest/ai-recommendations/AiRecommendationsPanel';
import { ComparePanel } from '@/components/backtest/compare/ComparePanel';

export interface BacktestConfigDialogProps {
  open: boolean;
  onClose: () => void;
}

type TabKey = 'config' | 'output' | 'trades' | 'metrics' | 'ai' | 'compare';

const TABS: Array<{ key: TabKey; label: string; icon: React.ReactNode }> = [
  { key: 'config', label: 'Config', icon: <Settings size={14} /> },
  { key: 'output', label: 'Live Output', icon: <Terminal size={14} /> },
  { key: 'trades', label: 'Trades', icon: <TrendingUp size={14} /> },
  { key: 'metrics', label: 'Metrics', icon: <BarChart3 size={14} /> },
  { key: 'ai', label: 'AI Recommendations', icon: <Sparkles size={14} /> },
  { key: 'compare', label: 'Compare', icon: <GitCompare size={14} /> },
];

const PRESET_DAYS = [30, 90, 180, 365];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

// ─── Config Tab ────────────────────────────────────────────────────────────────
function ConfigTab({
  config,
  onChange,
  disabled,
}: {
  config: Omit<BacktestConfig, 'strategyId'>;
  onChange: (patch: Partial<Omit<BacktestConfig, 'strategyId'>>) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* Lookback presets */}
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          LOOKBACK PRESET
        </p>
        <div className="flex gap-2 flex-wrap">
          {PRESET_DAYS.map((d) => (
            <button
              key={d}
              disabled={disabled}
              onClick={() => onChange({ startDate: daysAgo(d), endDate: today() })}
              className="px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => { if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Date range */}
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          DATE RANGE
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="bt-start" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Start Date</label>
            <InfoTooltip id="bt-start">
              <input
                id="bt-start"
                type="date"
                disabled={disabled}
                value={config.startDate}
                onChange={e => onChange({ startDate: e.target.value })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="bt-end" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>End Date</label>
            <InfoTooltip id="bt-end">
              <input
                id="bt-end"
                type="date"
                disabled={disabled}
                value={config.endDate}
                onChange={e => onChange({ endDate: e.target.value })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
          </div>
        </div>
      </div>

      {/* Capital & commission */}
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          CAPITAL & FEES
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="bt-capital" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Initial Capital (USD)</label>
            <InfoTooltip id="bt-capital">
              <input
                id="bt-capital"
                type="number"
                disabled={disabled}
                min={100}
                step={1000}
                value={config.initialCapital}
                onChange={e => onChange({ initialCapital: parseFloat(e.target.value) || 10000 })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="bt-commission" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Commission (fraction)</label>
            <InfoTooltip id="bt-commission">
              <input
                id="bt-commission"
                type="number"
                disabled={disabled}
                min={0}
                max={0.05}
                step={0.0001}
                value={config.commissionPercentage ?? 0.001}
                onChange={e => onChange({ commissionPercentage: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
            <p className="text-xs" style={{ color: 'var(--text-faint)' }}>e.g. 0.001 = 0.1%</p>
          </div>
        </div>
      </div>

      {/* Risk parameters */}
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          RISK PARAMETERS
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="bt-max-pos" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Max Concurrent Positions</label>
            <InfoTooltip id="bt-max-pos">
              <input
                id="bt-max-pos"
                type="number"
                disabled={disabled}
                min={1}
                max={20}
                step={1}
                value={config.maxConcurrentPositions ?? 1}
                onChange={e => onChange({ maxConcurrentPositions: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="bt-slippage" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Slippage (fraction)</label>
            <InfoTooltip id="bt-slippage">
              <input
                id="bt-slippage"
                type="number"
                disabled={disabled}
                min={0}
                max={0.02}
                step={0.0001}
                value={config.slippagePercentage ?? 0}
                onChange={e => onChange({ slippagePercentage: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              />
            </InfoTooltip>
          </div>
        </div>
      </div>

      {/* Timeframe */}
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          TIMEFRAME
        </p>
        <div style={{ maxWidth: 200 }}>
          <label htmlFor="bt-timeframe" className="text-xs font-medium sr-only" style={{ color: 'var(--text-secondary)' }}>Timeframe</label>
          <InfoTooltip id="bt-timeframe">
            <select
              id="bt-timeframe"
              disabled={disabled}
              value={config.timeframe ?? '1h'}
              onChange={e => onChange({ timeframe: e.target.value })}
              className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              {['1m', '5m', '15m', '30m', '1h', '4h', '1d'].map(tf => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </InfoTooltip>
        </div>
      </div>

      {/* Optimize hook (out of scope placeholder) */}
      <div className="pt-2">
        <button
          disabled
          title="Coming in BTCAAAAA-31182"
          className="px-4 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
        >
          Optimize…
        </button>
        <p className="text-xs mt-1" style={{ color: 'var(--text-faint)' }}>Parameter sweep optimizer — coming in BTCAAAAA-31182</p>
      </div>
    </div>
  );
}

// ─── Main dialog ───────────────────────────────────────────────────────────────
export function BacktestConfigDialog({ open, onClose }: BacktestConfigDialogProps) {
  const {
    currentStrategy,
    backTestInProgress,
    backTestProgress,
    backTestResult,
    runBacktest,
  } = useStrategyStore();

  const [activeTab, setActiveTab] = useState<TabKey>('config');
  const [config, setConfig] = useState<Omit<BacktestConfig, 'strategyId'>>({
    startDate: daysAgo(90),
    endDate: today(),
    initialCapital: 10000,
    commissionPercentage: 0.001,
    slippagePercentage: 0,
    maxConcurrentPositions: 1,
    timeframe: '1h',
  });
  const [outputLogs, setOutputLogs] = useState<BacktestStatusMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);

  // Seed timeframe from current strategy when dialog opens
  useEffect(() => {
    if (open && currentStrategy?.settings?.timeframe) {
      setConfig(prev => ({ ...prev, timeframe: currentStrategy.settings?.timeframe ?? '1h' }));
    }
  }, [open, currentStrategy]);

  const patchConfig = useCallback((patch: Partial<Omit<BacktestConfig, 'strategyId'>>) => {
    setConfig(prev => ({ ...prev, ...patch }));
  }, []);

  const handleStart = useCallback(async () => {
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
    setOutputLogs([{
      message: `Starting backtest for "${currentStrategy.name}" (${config.startDate} → ${config.endDate})…`,
      level: 'SYSTEM',
      timestamp: new Date().toISOString(),
    }]);
    setActiveTab('output');

    try {
      await runBacktest({ ...config, strategyId: currentStrategy.id });
      setOutputLogs(prev => [
        ...prev,
        { message: 'Backtest completed.', level: 'SYSTEM', timestamp: new Date().toISOString() },
      ]);
      setActiveTab('trades');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Backtest failed.';
      setError(msg);
      setOutputLogs(prev => [
        ...prev,
        { message: `ERROR: ${msg}`, level: 'ERROR', timestamp: new Date().toISOString() },
      ]);
    }
  }, [config, currentStrategy, runBacktest]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !backTestInProgress) onClose();
  }, [onClose, backTestInProgress]);

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
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.6)' }}
        onClick={() => { if (!backTestInProgress) onClose(); }}
      />

      {/* Dialog box */}
      <div
        ref={dialogRef}
        className="relative flex flex-col rounded-lg shadow-2xl mx-4"
        style={{
          width: '90vw',
          maxWidth: 1100,
          height: '82vh',
          border: '1px solid var(--border)',
          background: 'var(--bg-panel)',
        }}
      >
        {/* ── Header ── */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div>
            <h2
              id="backtest-dialog-title"
              className="text-sm font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-secondary)' }}
            >
              BACKTEST
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {currentStrategy?.name ?? 'No strategy loaded'}
            </p>
          </div>
          <button
            onClick={() => { if (!backTestInProgress) onClose(); }}
            className="p-1 rounded transition-opacity hover:opacity-70"
            style={{ color: 'var(--text-muted)' }}
            aria-label="Close dialog"
            disabled={backTestInProgress}
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Tab navigation ── */}
        <div
          className="flex flex-shrink-0 overflow-x-auto"
          style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-deep)' }}
        >
          {TABS.map(({ key, label, icon }) => {
            const isActive = activeTab === key;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className="flex items-center gap-1.5 px-4 py-3 text-xs font-medium whitespace-nowrap transition-colors"
                style={{
                  borderBottom: isActive ? '2px solid var(--accent-blue)' : '2px solid transparent',
                  color: isActive ? 'var(--text-secondary)' : 'var(--text-muted)',
                  background: 'transparent',
                  marginBottom: -1,
                }}
                onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
                onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'; }}
              >
                {icon}
                {label}
              </button>
            );
          })}
        </div>

        {/* ── Tab content ── */}
        <div className="flex-1 overflow-auto p-6" style={{ background: 'var(--bg-deep)' }}>
          {activeTab === 'config' && (
            <ConfigTab config={config} onChange={patchConfig} disabled={backTestInProgress} />
          )}
          {activeTab === 'output' && (
            <LiveOutputPanel logs={outputLogs} isRunning={backTestInProgress} />
          )}
          {activeTab === 'trades' && (
            <TradesPanel trades={backTestResult?.trades ?? []} />
          )}
          {activeTab === 'metrics' && (
            <MetricsPanel result={backTestResult} />
          )}
          {activeTab === 'ai' && (
            <AiRecommendationsPanel />
          )}
          {activeTab === 'compare' && (
            <ComparePanel />
          )}
        </div>

        {/* ── Footer: progress + run controls ── */}
        <div
          className="flex-shrink-0 px-6 py-4"
          style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-panel)' }}
        >
          {/* Progress bar */}
          {backTestInProgress && (
            <div className="mb-4 space-y-1">
              <div
                className="flex justify-between text-xs"
                style={{ color: 'var(--text-secondary)' }}
              >
                <span>Running…</span>
                <span style={{ fontVariantNumeric: 'tabular-nums' }}>{backTestProgress}%</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-card)' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${backTestProgress}%`, background: 'var(--accent-blue)' }}
                />
              </div>
            </div>
          )}

          {error && (
            <p className="text-xs mb-3" style={{ color: 'var(--accent-red)' }}>{error}</p>
          )}

          {/* Buttons */}
          <div className="flex items-center justify-end gap-2">
            {/* Pause/Resume (disabled until backend contract ships) */}
            {backTestInProgress && (
              <InfoTooltip id="bt-pause-btn">
                <button
                  disabled
                  title="Pause/Resume coming in BTCAAAAA-31183"
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                >
                  <Pause size={14} />
                  Pause
                </button>
              </InfoTooltip>
            )}

            {/* Cancel / Reset */}
            <InfoTooltip id="bt-cancel-btn">
              <button
                onClick={onClose}
                disabled={backTestInProgress}
                className="px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: '#314255', color: 'var(--btn-primary-text, white)' }}
                onMouseEnter={e => { if (!backTestInProgress) (e.currentTarget as HTMLButtonElement).style.opacity = '0.85'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
              >
                {backTestResult ? 'Close' : 'Cancel'}
              </button>
            </InfoTooltip>

            {/* Start / Stop */}
            <InfoTooltip id="bt-run-btn">
              {!backTestInProgress ? (
                <button
                  onClick={handleStart}
                  disabled={!canRun}
                  className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: '#32557c', color: 'var(--btn-primary-text, white)' }}
                  onMouseEnter={e => { if (canRun) (e.currentTarget as HTMLButtonElement).style.opacity = '0.85'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
                >
                  <Play size={14} />
                  {backTestResult ? 'Re-run' : 'Start Backtest'}
                </button>
              ) : (
                <button
                  className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium"
                  style={{ background: '#32557c', color: 'var(--btn-primary-text, white)', opacity: 0.6, cursor: 'not-allowed' }}
                  disabled
                  title="Stop not yet available — awaiting backend contract"
                >
                  <Square size={14} />
                  Running…
                </button>
              )}
            </InfoTooltip>
          </div>
        </div>
      </div>
    </div>
  );
}
