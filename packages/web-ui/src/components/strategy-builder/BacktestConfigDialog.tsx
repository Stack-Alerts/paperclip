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

// Tab order mirrors thickclient: Config / Live Output / Trades / AI Recommendations / Metrics / Compare
const TABS: Array<{ key: TabKey; label: string; icon: React.ReactNode }> = [
  { key: 'config', label: 'Config', icon: <Settings size={14} /> },
  { key: 'output', label: 'Live Output', icon: <Terminal size={14} /> },
  { key: 'trades', label: 'Trades', icon: <TrendingUp size={14} /> },
  { key: 'ai', label: 'AI Recommendations', icon: <Sparkles size={14} /> },
  { key: 'metrics', label: 'Metrics', icon: <BarChart3 size={14} /> },
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

// ─── Chip row helper (used for parity with thickclient duration / percentage rows) ─────
type ChipValue = string | number;
function ChipRow({
  label,
  values,
  current,
  onSelect,
  disabled,
  format,
}: {
  label: string;
  values: ChipValue[];
  current: ChipValue | null | undefined;
  onSelect: (v: ChipValue) => void;
  disabled: boolean;
  format?: (v: ChipValue) => string;
}) {
  const fmt = format ?? ((v: ChipValue) => String(v));
  return (
    <div className="grid grid-cols-[110px_1fr_56px] items-center gap-x-3 gap-y-0">
      <span
        className="text-[10px] font-medium uppercase tracking-wider truncate"
        style={{ color: 'var(--text-muted)' }}
      >
        {label}
      </span>
      <div className="flex gap-1 flex-wrap items-center">
        {values.map((v) => {
          const isActive = current === v;
          return (
            <button
              key={String(v)}
              disabled={disabled}
              onClick={() => onSelect(v)}
              className="px-2 py-0.5 rounded text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight"
              style={{
                background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-deep)',
                border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontVariantNumeric: 'tabular-nums',
                minWidth: 38,
              }}
              onMouseEnter={(e) => {
                if (!disabled && !isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)';
              }}
            >
              {fmt(v)}
            </button>
          );
        })}
      </div>
      {/* Selected-value readout — mirrors thickclient row-end suffix ("90 days", "1.5x", "20 bars") */}
      <span
        className="text-[10px] text-right truncate"
        style={{
          color: current !== null && current !== undefined ? 'var(--accent-blue)' : 'var(--text-faint)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {current !== null && current !== undefined ? fmt(current) : '—'}
      </span>
    </div>
  );
}

// ─── Section header for two-column ConfigTab body ──────────────────────────────────────
function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="space-y-0.5 mb-3">
      <h3
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: 'var(--text-secondary)' }}
      >
        {title}
      </h3>
      {subtitle && (
        <p className="text-xs" style={{ color: 'var(--text-faint)' }}>{subtitle}</p>
      )}
    </div>
  );
}

// ─── Card wrapper for each ConfigTab section ───────────────────────────────────────────
function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-md p-3 space-y-2"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
      }}
    >
      {children}
    </div>
  );
}

// ─── Config Tab — Two-column drawer body matching thickclient backtest_config_panel ────
//
// LEFT COLUMN: Configuration
//   - Basic Settings (Lookback / Training / Testing duration chip rows)
//   - Mode toggles (Walk-Forward / Live Replay)
//   - TP/SL Config (TP/SL Picker, Stop-Loss Adjustment, Adaptive v2.0)
//   - Execution & Fees (Date range, capital, commission, slippage, timeframe, max positions)
//
// RIGHT COLUMN: Risk/Reward
//   - Starting Capital chip row
//   - Min Risk/Reward chip row
//   - Max Risk chip row
//   - Leverage chip row
//   - Confluence (Boost from Strategy)
//   - Min/Max Bars Held chip rows
//
// All chips and inputs degrade gracefully when backend metadata is unavailable. Sections
// mirror the PyQt5 src/strategy_builder/ui/backtest_config_panel.py layout.
//
function ConfigTab({
  config,
  onChange,
  disabled,
}: {
  config: Omit<BacktestConfig, 'strategyId'>;
  onChange: (patch: Partial<Omit<BacktestConfig, 'strategyId'>>) => void;
  disabled: boolean;
}) {
  // Local UI-only state for thickclient parameters that don't (yet) reach the backend.
  // These mirror the thickclient panel surface so the visual port is complete; they will
  // be wired to BTCAAAAA-31183 backend config payload once that contract lands.
  const [lookbackDays, setLookbackDays] = useState<ChipValue>(90);
  const [trainingDays, setTrainingDays] = useState<ChipValue>(60);
  const [testingDays, setTestingDays] = useState<ChipValue>(30);
  const [mode, setMode] = useState<'walk-forward' | 'walk' | 'live-replay'>('walk-forward');
  const [tpSlConfig, setTpSlConfig] = useState<string>('Default');
  const [adaptivePreset, setAdaptivePreset] = useState<'Conservative' | 'Balanced' | 'Aggressive' | 'Custom'>('Balanced');
  const [delayStopLoss, setDelayStopLoss] = useState(true);
  const [marketStructureStop, setMarketStructureStop] = useState(false);
  const [stopLossDelay, setStopLossDelay] = useState<ChipValue>(1.0);
  const [emergency, setEmergency] = useState<ChipValue>(1.5);
  const [volatilityLookback, setVolatilityLookback] = useState<ChipValue>(20);
  const [volatilityMultiplier, setVolatilityMultiplier] = useState<ChipValue>(1.5);
  const [minStopLoss, setMinStopLoss] = useState<ChipValue>(1.0);
  const [maxStopLoss, setMaxStopLoss] = useState<ChipValue>(3.0);
  const [minRiskReward, setMinRiskReward] = useState<ChipValue>(2.0);
  const [maxRisk, setMaxRisk] = useState<ChipValue>(10);
  const [leverage, setLeverage] = useState<ChipValue>(5);
  const [confluence, setConfluence] = useState<string>('Boost from Strategy');
  const [minBarsHeld, setMinBarsHeld] = useState<ChipValue>(5);
  const [maxBarsHeld, setMaxBarsHeld] = useState<ChipValue>(60);

  const applyLookbackToDates = useCallback((days: number) => {
    setLookbackDays(days);
    onChange({ startDate: daysAgo(days), endDate: today() });
  }, [onChange]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3 max-w-[1700px] mx-auto pb-4">
      {/* ============================= LEFT COLUMN — CONFIGURATION ============================= */}
      <div className="space-y-3">
        <SectionHeader title="Configuration" subtitle="Basic settings, mode, TP/SL config" />

        {/* ── Basic Settings ── */}
        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            BASIC SETTINGS
          </h4>
          <ChipRow
            label="Lookback"
            values={[30, 60, 90, 120, 180, 365]}
            current={lookbackDays}
            onSelect={(v) => applyLookbackToDates(Number(v))}
            disabled={disabled}
            format={(v) => `${v}d`}
          />
          <ChipRow
            label="Training"
            values={[30, 60, 90, 120, 180]}
            current={trainingDays}
            onSelect={setTrainingDays}
            disabled={disabled}
            format={(v) => `${v}d`}
          />
          <ChipRow
            label="Testing"
            values={[15, 30, 45, 60, 90]}
            current={testingDays}
            onSelect={setTestingDays}
            disabled={disabled}
            format={(v) => `${v}d`}
          />
        </SectionCard>

        {/* ── Mode toggles ── */}
        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            MODE
          </h4>
          <div className="flex gap-2 flex-wrap">
            {([
              { id: 'walk-forward' as const, label: 'Walk-Forward' },
              { id: 'walk' as const, label: 'Walk' },
              { id: 'live-replay' as const, label: 'Live Replay' },
            ]).map((m) => {
              const isActive = mode === m.id;
              return (
                <button
                  key={m.id}
                  disabled={disabled}
                  onClick={() => setMode(m.id)}
                  className="px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
                  style={{
                    background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-card)',
                    border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                    color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  }}
                >
                  {m.label}
                </button>
              );
            })}
          </div>
        </SectionCard>

        {/* ── TP/SL Config ── */}
        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            TP/SL CONFIG
          </h4>
          <div className="grid grid-cols-1 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="bt-tpsl-config" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                TP/SL Config
              </label>
              <select
                id="bt-tpsl-config"
                disabled={disabled}
                value={tpSlConfig}
                onChange={(e) => setTpSlConfig(e.target.value)}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              >
                <option>Default</option>
                <option>TBoosct</option>
                <option>Conservative</option>
                <option>Aggressive</option>
                <option>Manual</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Stop-Loss Adjustment
              </label>
              <div className="flex gap-2 flex-wrap">
                {['Adaptive v2.0', 'Static', 'Trailing', 'None'].map((opt) => {
                  const isActive = opt === 'Adaptive v2.0';
                  return (
                    <button
                      key={opt}
                      disabled={disabled}
                      className="px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50"
                      style={{
                        background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-deep)',
                        border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                        color: isActive ? 'var(--accent-blue)' : 'var(--text-muted)',
                      }}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* ============================= MIDDLE COLUMN — ADAPTIVE v2.0 ============================= */}
      <div className="space-y-3">
        <SectionHeader title="Adaptive v2.0" subtitle="Volatility-aware stop-loss and take-profit tuning" />

        {/* ── Adaptive v2.0 panel ── */}
        <SectionCard>
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
              ADAPTIVE v2.0
            </h4>
            <span className="text-xs" style={{ color: 'var(--text-faint)' }}>Volatility-aware SL/TP</span>
          </div>
          <div className="space-y-3">
            {/* Presets */}
            <ChipRow
              label="Presets"
              values={['Conservative', 'Balanced', 'Aggressive', 'Custom']}
              current={adaptivePreset}
              onSelect={(v) => setAdaptivePreset(v as typeof adaptivePreset)}
              disabled={disabled}
            />

            {/* Toggles */}
            <div className="flex gap-4 pt-1">
              <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={delayStopLoss}
                  onChange={(e) => setDelayStopLoss(e.target.checked)}
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                Delay Stop-Loss
              </label>
              <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={marketStructureStop}
                  onChange={(e) => setMarketStructureStop(e.target.checked)}
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                Market Structure Stop-Loss
              </label>
            </div>

            <ChipRow
              label="Stop-Loss Delay"
              values={[0, 1, 2, 3, 4, 5, 6, 7]}
              current={stopLossDelay}
              onSelect={setStopLossDelay}
              disabled={disabled}
              format={(v) => `${v} bars`}
            />
            <ChipRow
              label="Emergency"
              values={[1.0, 1.5, 2.0, 2.5, 3.0]}
              current={emergency}
              onSelect={setEmergency}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(2)}%`}
            />
            <ChipRow
              label="Volatility Lookback"
              values={[10, 15, 20, 25, 30, 50]}
              current={volatilityLookback}
              onSelect={setVolatilityLookback}
              disabled={disabled}
              format={(v) => `${v} bars`}
            />
            <ChipRow
              label="Volatility Multiplier"
              values={[1, 2, 3, 4, 5]}
              current={volatilityMultiplier}
              onSelect={setVolatilityMultiplier}
              disabled={disabled}
              format={(v) => `${v}x`}
            />
            <ChipRow
              label="Min Stop-Loss"
              values={[0.5, 1.0, 1.5, 2.0, 2.5]}
              current={minStopLoss}
              onSelect={setMinStopLoss}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}%`}
            />
            <ChipRow
              label="Max Stop-Loss"
              values={[2.0, 3.0, 5.0, 7.0, 10.0]}
              current={maxStopLoss}
              onSelect={setMaxStopLoss}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}%`}
            />
          </div>
        </SectionCard>
      </div>

      {/* ============================= RIGHT COLUMN — RISK/REWARD ============================= */}
      <div className="space-y-3">
        <SectionHeader title="Risk / Reward" subtitle="Sizing, exposure, and trade-duration bounds" />

        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            CAPITAL & EXPOSURE
          </h4>
          <ChipRow
            label="Starting Capital"
            values={[100, 1000, 10000, 100000, 1000000]}
            current={config.initialCapital ?? 10000}
            onSelect={(v) => onChange({ initialCapital: Number(v) })}
            disabled={disabled}
            format={(v) => `$${Number(v).toLocaleString()}`}
          />
          <ChipRow
            label="Min Risk/Reward"
            values={[1.0, 1.5, 2.0, 3.0, 5.0]}
            current={minRiskReward}
            onSelect={setMinRiskReward}
            disabled={disabled}
            format={(v) => `${v}x`}
          />
          <ChipRow
            label="Max Risk"
            values={[1, 5, 10, 20, 40]}
            current={maxRisk}
            onSelect={setMaxRisk}
            disabled={disabled}
            format={(v) => `${v}%`}
          />
          <ChipRow
            label="Leverage"
            values={[1, 2, 3, 5, 10, 25, 50, 100]}
            current={leverage}
            onSelect={setLeverage}
            disabled={disabled}
            format={(v) => `${v}x`}
          />
        </SectionCard>

        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            CONFLUENCE
          </h4>
          <div className="space-y-1.5">
            <label htmlFor="bt-confluence" className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
              Confluence Mode
            </label>
            <select
              id="bt-confluence"
              disabled={disabled}
              value={confluence}
              onChange={(e) => setConfluence(e.target.value)}
              className="w-full px-3 py-2 rounded text-sm focus:outline-none disabled:opacity-50"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              <option>Boost from Strategy</option>
              <option>Independent Score</option>
              <option>Disabled</option>
            </select>
            <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
              Use strategy-side confluence boost vs an independent score band.
            </p>
          </div>
        </SectionCard>

        <SectionCard>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            HOLD DURATION
          </h4>
          <ChipRow
            label="Min Bars Held"
            values={[1, 5, 10, 20, 40]}
            current={minBarsHeld}
            onSelect={setMinBarsHeld}
            disabled={disabled}
            format={(v) => `${v}`}
          />
          <ChipRow
            label="Max Bars Held"
            values={[5, 10, 30, 60, 120, 200]}
            current={maxBarsHeld}
            onSelect={setMaxBarsHeld}
            disabled={disabled}
            format={(v) => `${v}`}
          />
        </SectionCard>

        {/* Optimize hook — deferred to BTCAAAAA-31247 */}
        <div className="pt-2">
          <button
            disabled
            title="Parameter sweep optimizer — deferred to BTCAAAAA-31247"
            className="px-4 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
          >
            Optimize…
          </button>
          <p className="text-xs mt-1" style={{ color: 'var(--text-faint)' }}>Parameter sweep optimizer — deferred to BTCAAAAA-31247</p>
        </div>
      </div>
    </div>
  );
}

// ─── Status log panel — mirrors thickclient bottom status box ──────────────────────────
function StatusLogPanel({
  logs,
  isRunning,
}: {
  logs: BacktestStatusMessage[];
  isRunning: boolean;
}) {
  if (logs.length === 0 && !isRunning) return null;
  const recent = logs.slice(-5);
  return (
    <div
      className="rounded-md mb-4"
      style={{
        background: 'var(--bg-deep)',
        border: '1px solid var(--border)',
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-1.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <span
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          Status
        </span>
        <span
          className="text-xs"
          style={{ color: isRunning ? 'var(--accent-blue)' : 'var(--text-faint)' }}
        >
          {isRunning ? 'Running…' : 'Idle'}
        </span>
      </div>
      <ul className="px-3 py-2 space-y-0.5 max-h-28 overflow-auto">
        {recent.map((log, idx) => (
          <li
            key={`${log.timestamp}-${idx}`}
            className="text-xs font-mono leading-snug"
            style={{
              color:
                log.level === 'ERROR'
                  ? 'var(--accent-red)'
                  : log.level === 'SYSTEM'
                    ? 'var(--accent-blue)'
                    : 'var(--text-secondary)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            <span style={{ color: 'var(--text-faint)' }}>
              {new Date(log.timestamp).toISOString().slice(11, 19)}{' '}
            </span>
            {log.message}
          </li>
        ))}
      </ul>
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
      className="fixed inset-y-0 right-0 z-50 flex items-stretch"
      style={{ left: 'var(--sidebar-width, 0px)' }}
      onKeyDown={handleKeyDown}
    >
      {/* Backdrop — drawer-pattern parity with ValidationReportWindow / StrategyBrowserDialog */}
      <div
        className="absolute inset-0 bg-black/70 cursor-pointer"
        onClick={() => { if (!backTestInProgress) onClose(); }}
      />

      {/* Drawer box — full-height right-anchored window */}
      <div
        ref={dialogRef}
        className="relative flex flex-col flex-1 shadow-2xl"
        style={{
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
              Backtest Configuration
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {currentStrategy?.name ? `${currentStrategy.name} Strategy` : 'No strategy loaded'}
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

        {/* ── Footer: status, progress + run controls ── */}
        <div
          className="flex-shrink-0 px-6 py-4"
          style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-panel)' }}
        >
          {/* Status log panel — drawer footer mirrors thickclient bottom status box */}
          <StatusLogPanel logs={outputLogs} isRunning={backTestInProgress} />

          {/* Progress bar — thickclient parity: Candles N/M, Trades K, TPSL Adjustments K */}
          {(backTestInProgress || backTestProgress > 0) && (
            <div className="mb-4 space-y-1">
              <div
                className="text-[11px]"
                style={{ color: 'var(--text-secondary)' }}
              >
                <span className="font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Progress</span>
                <span className="ml-3" style={{ color: 'var(--text-muted)' }}>
                  Candles:{' '}
                  <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
                    {(backTestResult?.trades && (backTestResult as unknown as { totalBars?: number }).totalBars) ?? '—'}
                  </span>
                </span>
                <span className="ml-3" style={{ color: 'var(--text-muted)' }}>
                  Trades:{' '}
                  <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }}>
                    {backTestResult?.trades?.length ?? '—'}
                  </span>
                </span>
                <span className="ml-3" style={{ color: 'var(--text-muted)' }}>
                  TPSL Adjustments:{' '}
                  <span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-faint)' }}>—</span>
                </span>
                <span className="ml-3 float-right" style={{ fontVariantNumeric: 'tabular-nums' }}>{backTestProgress}%</span>
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

          {/* Action bar — thickclient layout: Run Test / Pause / Stop on left, Config Discovery / saved-at / View Live Results on right */}
          <div className="flex items-center justify-between gap-2">
            {/* Left cluster — primary run controls (thickclient leading edge) */}
            <div className="flex items-center gap-2">
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
                    {backTestResult ? 'Re-run' : 'Run Test'}
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
              <InfoTooltip id="bt-pause-btn">
                <button
                  disabled
                  title="Pause/Resume — deferred (control endpoint coming in follow-up)"
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                >
                  <Pause size={14} />
                  Pause
                </button>
              </InfoTooltip>
              <InfoTooltip id="bt-stop-btn">
                <button
                  disabled
                  title="Stop — deferred (control endpoint coming in follow-up)"
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                >
                  <Square size={14} />
                  Stop
                </button>
              </InfoTooltip>
              {/* "Config saved at HH:MM:SS (after test run)" — italic, only after a run completes */}
              {backTestResult?.completedAt && (
                <span
                  className="ml-2 italic text-xs"
                  style={{ color: 'var(--text-faint)' }}
                >
                  Config saved at {new Date(backTestResult.completedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (after test run)
                </span>
              )}
            </div>

            {/* Right cluster — ancillary actions + close */}
            <div className="flex items-center gap-2">
              <InfoTooltip id="bt-config-discovery-btn">
                <button
                  disabled
                  title="Config Discovery — auto-tune TP/SL across recent windows (deferred to BTCAAAAA-31247)"
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:cursor-not-allowed"
                  style={{
                    background: 'rgba(46, 140, 255, 0.10)',
                    border: '1px solid rgba(46, 140, 255, 0.30)',
                    color: 'var(--text-muted)',
                  }}
                >
                  <Settings size={14} />
                  Config Discovery
                </button>
              </InfoTooltip>
              <InfoTooltip id="bt-view-live-btn">
                <button
                  disabled={!backTestResult}
                  onClick={() => setActiveTab('trades')}
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: backTestResult ? 'var(--text-secondary)' : 'var(--text-muted)' }}
                >
                  <TrendingUp size={14} />
                  View Live Results
                </button>
              </InfoTooltip>
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
