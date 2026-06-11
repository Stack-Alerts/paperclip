'use client';

import React, { useState, useCallback } from 'react';
import { Play, Square, TrendingUp, AlertTriangle, BarChart3 } from 'lucide-react';
import { BacktestConfig, BacktestProgress } from '@/types';
import { BacktestStatusMessage, Trade, BacktestResult } from '@/lib/strategy-builder/types';
import { AppBrand } from '@/components/shared/AppBrand';
import { LiveOutputPanel } from './live-output/LiveOutputPanel';
import { MetricsPanel } from './metrics/MetricsPanel';
import { TradesPanel } from './trades/TradesPanel';
import { BacktestProgressMeter } from './progress-meter';
import { useTooltipSettings } from '@/components/strategy-builder/TooltipSettingsContext';

export interface BacktestWindowProps {
  progress?: BacktestProgress;
  result?: BacktestResult;
  logs?: BacktestStatusMessage[];
  trades?: Trade[];
  isRunning?: boolean;
  onStart?: (config: BacktestConfig) => void;
  onStop?: () => void;
  disabled?: boolean;
}

export function BacktestWindow({
  progress,
  result,
  logs = [],
  trades = [],
  isRunning = false,
  onStart,
  onStop,
  disabled = false,
}: BacktestWindowProps) {
  const [currentTab, setCurrentTab] = useState<'config' | 'progress' | 'results' | 'trades' | 'live-output'>('config');
  const { settings: tooltipSettings, update: updateTooltipSettings } = useTooltipSettings();
  const [config, setConfig] = useState<BacktestConfig>({
    lookbackDays: 180,
    trainingWindow: 30,
    mode: 'historical',
    strategyId: '',
    instrumentId: '',
    startDate: new Date(),
    endDate: new Date(),
  });

  const handleConfigChange = useCallback((field: keyof BacktestConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
  }, []);

  const handleStart = useCallback(() => {
    onStart?.(config);
  }, [config, onStart]);

  const handleStop = useCallback(() => {
    onStop?.();
  }, [onStop]);

  // Render config tab content
  const configContent = (
    <div className="space-y-4">
      <div className="rounded border p-4" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <h3 className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
          Backtest Parameters
        </h3>

        {/* Lookback and Training Window Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="space-y-2">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Lookback Days</label>
            <input
              type="number"
              value={config.lookbackDays}
              onChange={(e) => handleConfigChange('lookbackDays', parseInt(e.target.value) || 0)}
              disabled={disabled || isRunning}
              min="1"
              max="3650"
              className="w-full px-3 py-2 rounded text-sm border"
              style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Training Window (days)</label>
            <input
              type="number"
              value={config.trainingWindow}
              onChange={(e) => handleConfigChange('trainingWindow', parseInt(e.target.value) || 0)}
              disabled={disabled || isRunning}
              min="1"
              max="365"
              className="w-full px-3 py-2 rounded text-sm border"
              style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
            />
          </div>
        </div>

        {/* Mode Selection */}
        <div className="space-y-2 mb-4">
          <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Backtest Mode</label>
          <select
            value={config.mode}
            onChange={(e) => handleConfigChange('mode', e.target.value)}
            disabled={disabled || isRunning}
            className="w-full px-3 py-2 rounded text-sm border"
            style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
          >
            <option value="historical">Mode 1: Historical</option>
            <option value="live">Mode 2: Live Replay</option>
          </select>
        </div>

        {/* Strategy and Instrument Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="space-y-2">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Strategy</label>
            <input
              type="text"
              value={config.strategyId}
              onChange={(e) => handleConfigChange('strategyId', e.target.value)}
              disabled={disabled || isRunning}
              placeholder="Select strategy..."
              className="w-full px-3 py-2 rounded text-sm border"
              style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Instrument</label>
            <input
              type="text"
              value={config.instrumentId}
              onChange={(e) => handleConfigChange('instrumentId', e.target.value)}
              disabled={disabled || isRunning}
              placeholder="Select instrument..."
              className="w-full px-3 py-2 rounded text-sm border"
              style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
            />
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex gap-2 pt-2">
          {!isRunning ? (
            <button
              onClick={handleStart}
              disabled={disabled || !config.strategyId || !config.instrumentId}
              className="flex-1 px-4 py-2 rounded font-medium transition-colors flex items-center justify-center gap-2"
              style={{
                background: disabled || !config.strategyId || !config.instrumentId ? 'var(--bg-hover)' : 'var(--accent-blue)',
                color: disabled || !config.strategyId || !config.instrumentId ? 'var(--text-muted)' : 'var(--btn-primary-text)',
                opacity: disabled || !config.strategyId || !config.instrumentId ? 0.5 : 1,
                cursor: disabled || !config.strategyId || !config.instrumentId ? 'not-allowed' : 'pointer',
              }}
            >
              <Play size={14} strokeWidth={2} />
              <span>Run Test</span>
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="flex-1 px-4 py-2 rounded font-medium transition-colors flex items-center justify-center gap-2"
              style={{
                background: 'var(--accent-red-dark)',
                color: 'var(--btn-primary-text)',
              }}
            >
              <Square size={14} strokeWidth={2} />
              <span>Stop</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );

  // Render progress tab content — thick-client parity (BTCAAAAA-34190).
  // Meter and status panel are always rendered so the idle layout matches
  // the PyQt5 reference (bar at 0%, candle/trade/TP-SL counters at 0, status
  // box showing the "what you will see" checklist).
  const progressPct = progress
    ? progress.totalCandles > 0
      ? Math.round((progress.currentCandle / progress.totalCandles) * 100)
      : 0
    : 0;
  const candles = progress
    ? { current: progress.currentCandle, total: progress.totalCandles }
    : undefined;
  const progressContent = (
    <div className="space-y-3">
      <BacktestProgressMeter
        progress={progressPct}
        isRunning={isRunning}
        result={result ?? null}
        candles={candles}
      />
      <LiveOutputPanel logs={logs} isRunning={isRunning} result={result ?? null} candles={candles} trades={trades} />
    </div>
  );

  // Render results tab content
  const resultsContent = result ? (
    <div className="space-y-3">
      <div className="rounded border p-3" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <h3 className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
          Key Metrics
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Total Trades', value: result.totalTrades, color: undefined },
            { label: 'Win Rate', value: `${(result.winRate * 100).toFixed(1)}%`, color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)' },
            { label: 'Profit Factor', value: result.profitFactor.toFixed(2), color: undefined },
            { label: 'Max Drawdown', value: `${(result.maxDrawdown * 100).toFixed(2)}%`, color: 'var(--accent-orange)' },
            { label: 'Total Return', value: `${result.returnPercentage.toFixed(2)}%`, color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
            { label: 'Sharpe Ratio', value: result.sharpeRatio.toFixed(2), color: undefined },
          ].map(item => (
            <div
              key={item.label}
              className="rounded p-2"
              style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border)',
              }}
            >
              <div style={{ fontSize: '9px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                {item.label}
              </div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: item.color || 'var(--text-secondary)', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* All Metrics via MetricsPanel */}
      <div className="rounded border p-3" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <MetricsPanel result={result} trades={trades} />
      </div>
    </div>
  ) : (
    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
      <p>No results yet. Run a backtest to see performance metrics.</p>
    </div>
  );

  const tabConfig: Array<{ id: 'config' | 'progress' | 'results' | 'trades' | 'live-output'; label: string; icon: typeof BarChart3; badge?: string }> = [
    { id: 'config', label: 'Config', icon: BarChart3 },
    { id: 'progress', label: 'Progress', icon: TrendingUp, badge: isRunning ? '●' : undefined },
    { id: 'results', label: 'Results', icon: TrendingUp, badge: result ? '✓' : undefined },
    { id: 'trades', label: 'Trades', icon: AlertTriangle, badge: trades.length > 0 ? String(trades.length) : undefined },
    { id: 'live-output', label: 'Live Output', icon: BarChart3, badge: logs.length > 0 ? String(logs.length) : undefined },
  ];

  return (
    <div
      className="relative w-full flex flex-col"
      style={{
        maxWidth: '100%',
        width: '100%',
        height: 'auto',
        borderRadius: 0,
        border: '1px solid var(--border)',
        background: 'var(--bg-panel)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h2
          className="text-sm font-semibold flex items-center gap-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          <AppBrand size={24} />
          <span>Backtest Engine</span>
        </h2>
        {/* Tooltip settings — shared singleton with strategy builder */}
        <div className="flex items-center gap-3 flex-shrink-0 text-xs" style={{ color: 'var(--text-faint)' }}>
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={tooltipSettings.enabled}
              onChange={e => updateTooltipSettings({ enabled: e.target.checked })}
              style={{ accentColor: 'var(--toolbar-accent)', width: 11, height: 11 }}
            />
            Tooltips
          </label>
          {tooltipSettings.enabled && (
            <>
              <input
                type="range"
                min={300}
                max={3000}
                step={100}
                value={tooltipSettings.delayMs}
                onChange={e => updateTooltipSettings({ delayMs: Number(e.target.value) })}
                style={{ width: 54, accentColor: 'var(--toolbar-accent)', cursor: 'pointer', opacity: 0.75 }}
              />
              <span style={{ minWidth: 24, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {(tooltipSettings.delayMs / 1000).toFixed(1)}s
              </span>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex-shrink-0 px-6 border-b flex gap-8 overflow-x-auto"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}
      >
        {tabConfig.map(({ id, label, icon: Icon, badge }) => {
          const isActive = currentTab === id;
          return (
            <button
              key={id}
              onClick={() => setCurrentTab(id as any)}
              className="px-4 py-2.5 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap"
              style={
                isActive
                  ? { borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }
                  : { borderColor: 'transparent', color: 'var(--text-secondary)' }
              }
            >
              <Icon size={14} strokeWidth={1.75} />
              <span>{label}</span>
              {badge && (
                <span
                  className="text-xs font-bold ml-1"
                  style={{ color: 'var(--accent-green)' }}
                >
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {currentTab === 'config' && configContent}
        {currentTab === 'progress' && progressContent}
        {currentTab === 'results' && resultsContent}
        {currentTab === 'trades' && <TradesPanel trades={trades} />}
        {currentTab === 'live-output' && <LiveOutputPanel logs={logs} isRunning={isRunning} result={result ?? null} candles={candles} trades={trades} />}
      </div>
    </div>
  );
}

export default BacktestWindow;
