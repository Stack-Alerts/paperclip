'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import {
  BacktestConfigFull,
  BacktestStatusMessage,
  TpSlAdjustments,
  Trade,
} from '@/lib/strategy-builder/types';

// ── Helpers ──────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}
function fmt(n: number, decimals = 2) {
  return n.toFixed(decimals);
}

const PRESET_DAYS = [30, 60, 90, 120, 180, 240, 360];

const PRESET_INITIAL_CAPITAL = [500, 1000, 2000, 5000, 10000, 25000, 50000];
const PRESET_RISK_PCT = [1, 2, 5, 7, 10, 12, 15];
const PRESET_RR_RATIO = [1.2, 1.5, 2.0, 2.2, 2.5, 2.7, 3.0];
const PRESET_MAX_BARS = [15, 20, 25, 30, 40, 50, 75];
const PRESET_DELAY_BARS = [1, 3, 5, 7, 10, 15, 20];
const PRESET_EMERGENCY_SL = [1, 2, 3, 4, 5, 7, 10];
const PRESET_VOL_LOOKBACK = [10, 14, 20, 30, 50, 75, 100];
const PRESET_VOL_MULTIPLIER = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0];
const PRESET_MIN_SL = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0];
const PRESET_MAX_SL = [2, 3, 5, 7, 10, 12, 15];
const PRESET_MAX_LEVERAGE = [3, 5, 10, 15, 20, 25, 30];
const PRESET_CONFLUENCE = [20, 30, 40, 50, 60];

const ADAPTIVE_SL_PRESETS: Record<string, Partial<BacktestConfigFull['adaptiveSL']> & { emergencySlPct: number; volatilityMultiplier: number; delayBars: number; minSlPct: number; maxSlPct: number }> = {
  conservative: { delayEnabled: true, delayBars: 3, emergencySlPct: 3, volatilityLookback: 20, volatilityMultiplier: 1.5, minSlPct: 1.0, maxSlPct: 2.5 },
  balanced:     { delayEnabled: true, delayBars: 2, emergencySlPct: 2, volatilityLookback: 14, volatilityMultiplier: 1.2, minSlPct: 0.7, maxSlPct: 2.0 },
  aggressive:   { delayEnabled: true, delayBars: 1, emergencySlPct: 2, volatilityLookback: 10, volatilityMultiplier: 1.0, minSlPct: 0.6, maxSlPct: 1.5 },
};

const defaultConfig: BacktestConfigFull = {
  strategyId: '',
  startDate: daysAgo(90),
  endDate: today(),
  initialCapital: 10000,
  commissionPercentage: 0.0004,
  mode: 'historical',
  tpslMode: 'fibonacci',
  slAdjustmentMode: 'adaptiveV2',
  adaptiveSLPreset: 'balanced',
  adaptiveSL: {
    enabled: true,
    delayEnabled: true,
    delayBars: 2,
    emergencySlPct: 2,
    volatilityLookback: 14,
    volatilityMultiplier: 1.2,
    minSlPct: 0.7,
    maxSlPct: 2.0,
    useStructureSl: false,
    structureSources: ['swing_points', 'supply_demand', 'fibonacci'],
  },
  riskPerTradePct: 10,
  minRiskRewardRatio: 1.2,
  maxBarsHeld: 50,
  lookbackDays: 180,
  trainingDays: 90,
  testingDays: 30,
  maxLeverage: 10,
  confluenceThreshold: 40,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function TabBar({ tabs, active, onChange }: { tabs: string[]; active: number; onChange: (i: number) => void }) {
  return (
    <div className="flex border-b overflow-x-auto" style={{ borderColor: 'var(--border)' }}>
      {tabs.map((t, i) => (
        <button
          key={t}
          onClick={() => onChange(i)}
          className="px-4 py-2 text-xs font-medium whitespace-nowrap transition-colors"
          style={
            i === active
              ? { borderBottom: '2px solid var(--accent-blue)', color: 'var(--accent-blue)' }
              : { color: 'var(--text-secondary)' }
          }
        >
          {t}
        </button>
      ))}
    </div>
  );
}

function SpinField({
  label, value, onChange, min, max, step, suffix,
}: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; suffix?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          min={min}
          max={max}
          step={step ?? 1}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-full px-2 py-1.5 rounded text-sm focus:outline-none"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
        />
        {suffix && <span className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>{suffix}</span>}
      </div>
    </div>
  );
}

function SelectField<T extends string>({
  label, value, onChange, options,
}: {
  label: string; value: T; onChange: (v: T) => void;
  options: Array<{ label: string; value: T }>;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="w-full px-2 py-1.5 rounded text-sm focus:outline-none"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded p-3 space-y-0.5" style={{ background: 'var(--bg-card)' }}>
      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</div>
      <div className="text-lg font-semibold" style={{ color: 'var(--text-secondary)' }}>{value}</div>
      {sub && <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

function PresetButtonRow({
  label,
  values,
  onSelect,
  format,
}: {
  label: string;
  values: number[];
  onSelect: (v: number) => void;
  format?: (v: number) => string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <button
            key={v}
            onClick={() => onSelect(v)}
            className="px-2 py-1 rounded text-xs font-medium transition-colors"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
          >
            {format ? format(v) : v}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── API payload translation (React camelCase → Python snake_case) ─────────────

function buildPythonPayload(config: BacktestConfigFull, strategyId: string): Record<string, unknown> {
  // Python engine expects mode as int enum: 1 = historical, 2 = live_replay
  const modeInt = config.mode === 'historical' ? 1 : 2;

  const payload: Record<string, unknown> = {
    strategyId, // retained so the store can build the API URL path
    lookback_days: config.lookbackDays ?? 180,
    mode: modeInt,
    tpsl_mode: config.tpslMode,
    sl_mode: config.slAdjustmentMode,
    start_date: config.startDate,
    end_date: config.endDate,
    timeframe: '15m',
    starting_capital: config.initialCapital,
    commission_percentage: config.commissionPercentage ?? 0.0004,
    risk_per_trade_pct: config.riskPerTradePct,
    min_risk_reward: config.minRiskRewardRatio,
    max_leverage: config.maxLeverage ?? 10,
    confluence_threshold: config.confluenceThreshold ?? 40,
    max_bars_held: config.maxBarsHeld,
    adaptive_sl: {
      enabled: config.adaptiveSL.enabled,
      delay_enabled: config.adaptiveSL.delayEnabled,
      delay_bars: config.adaptiveSL.delayBars,
      emergency_sl_pct: config.adaptiveSL.emergencySlPct,
      volatility_lookback: config.adaptiveSL.volatilityLookback,
      volatility_multiplier: config.adaptiveSL.volatilityMultiplier,
      min_sl_pct: config.adaptiveSL.minSlPct,
      max_sl_pct: config.adaptiveSL.maxSlPct,
      use_structure_sl: config.adaptiveSL.useStructureSl,
      structure_sources: config.adaptiveSL.structureSources ?? ['swing_points', 'supply_demand', 'fibonacci'],
    },
  };

  // Mode 1 (historical): include training/testing split windows
  if (modeInt === 1) {
    payload.training_window = config.trainingDays ?? 90;
    payload.testing_window = config.testingDays ?? 30;
  }

  return payload;
}

// ── Main panel ────────────────────────────────────────────────────────────────

export interface BacktestConfigPanelProps {
  open: boolean;
  onClose: () => void;
}

const TABS = ['💠 Config', '● Live Output', '💰 Trades', '💹 Metrics', '🤖 AI Recs', '🔁 Compare'];

export function BacktestConfigPanel({ open, onClose }: BacktestConfigPanelProps) {
  const { currentStrategy, runBacktest, backTestInProgress, backTestProgress, backTestResult } = useStrategyStore();

  const [activeTab, setActiveTab] = useState(0);
  const [config, setConfig] = useState<BacktestConfigFull>(() => ({
    ...defaultConfig,
    strategyId: currentStrategy?.id ?? '',
  }));
  const [error, setError] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [logs, setLogs] = useState<BacktestStatusMessage[]>([]);
  const [tpSlAdj, setTpSlAdj] = useState<TpSlAdjustments>({ TP1: 0, TP2: 0, TP3: 0, SL: 0 });
  const [compareConfig, setCompareConfig] = useState<BacktestConfigFull | null>(null);
  const [aiRequest, setAiRequest] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      localStorage.setItem('backtest-config', JSON.stringify(config));
    }, 500);
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [config]);

  // Update strategyId when strategy changes
  useEffect(() => {
    if (currentStrategy?.id) {
      setConfig((prev) => ({ ...prev, strategyId: currentStrategy.id }));
    }
  }, [currentStrategy?.id]);

  const patch = useCallback(<K extends keyof BacktestConfigFull>(k: K, v: BacktestConfigFull[K]) => {
    setConfig((prev) => ({ ...prev, [k]: v }));
  }, []);

  const patchAdaptiveSL = useCallback(<K extends keyof BacktestConfigFull['adaptiveSL']>(
    k: K, v: BacktestConfigFull['adaptiveSL'][K],
  ) => {
    setConfig((prev) => ({ ...prev, adaptiveSL: { ...prev.adaptiveSL, [k]: v }, adaptiveSLPreset: 'custom' }));
  }, []);

  const applyPresetDays = useCallback((days: number) => {
    setConfig((prev) => ({ ...prev, startDate: daysAgo(days), endDate: today() }));
  }, []);

  const applyAdaptiveSLPreset = useCallback((preset: 'conservative' | 'balanced' | 'aggressive') => {
    const vals = ADAPTIVE_SL_PRESETS[preset];
    setConfig((prev) => ({
      ...prev,
      adaptiveSLPreset: preset,
      adaptiveSL: { ...prev.adaptiveSL, ...vals },
    }));
  }, []);

  const addLog = useCallback((msg: string, level: BacktestStatusMessage['level'] = 'INFO') => {
    setLogs((prev) => [
      ...prev,
      { message: msg, level, timestamp: new Date().toISOString() },
    ]);
  }, []);

  const handleRun = useCallback(async () => {
    if (!currentStrategy) return;
    if (!config.startDate || !config.endDate) { setError('Start and end dates required.'); return; }
    if (config.startDate >= config.endDate) { setError('Start date must be before end date.'); return; }
    setError(null);
    setLogs([]);
    setTpSlAdj({ TP1: 0, TP2: 0, TP3: 0, SL: 0 });
    setIsPaused(false);
    setActiveTab(1); // switch to Live Output
    addLog('🚀 Starting backtest...', 'SYSTEM');
    addLog(`Mode: ${config.mode === 'historical' ? 'Mode 1 — Historical' : 'Mode 2 — Live Replay'}`, 'INFO');
    addLog(`TP/SL: ${config.tpslMode} | SL Adj: ${config.slAdjustmentMode}`, 'INFO');
    try {
      // Run calibration before backtest (desktop equivalent: _run_auto_calibration)
      addLog('⚙️ Running auto-calibration...', 'SYSTEM');
      // TODO(P2): Wire calibration endpoint when available

      // Translate React camelCase config → Python snake_case payload before sending
      await runBacktest(buildPythonPayload(config, currentStrategy.id) as unknown as BacktestConfigFull);
      addLog('✅ Backtest complete.', 'SYSTEM');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Backtest failed.';
      setError(msg);
      addLog(`❌ ${msg}`, 'ERROR');
    }
  }, [config, currentStrategy, runBacktest, addLog]);

  const handlePause = useCallback(() => setIsPaused((p) => !p), []);
  const handleStop = useCallback(() => {
    addLog('⏹️ Backtest stopped by user.', 'SYSTEM');
    setIsPaused(false);
  }, [addLog]);

  const saveAsCompare = useCallback(() => {
    setCompareConfig({ ...config });
    addLog('Saved current config as Compare baseline.', 'INFO');
  }, [config, addLog]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => { if (e.key === 'Escape') onClose(); },
    [onClose],
  );

  if (!open) return null;

  const canRun = !!currentStrategy && !!config.startDate && !!config.endDate && !backTestInProgress;
  const trades = backTestResult?.trades ?? [];
  const result = backTestResult;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="bcp-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />

      <div className="relative w-full max-w-5xl mx-4 rounded-lg shadow-2xl flex flex-col max-h-[90vh]" style={{ border: '1px solid var(--border)', background: 'var(--bg-panel)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 shrink-0" style={{ borderBottom: '1px solid var(--bg-card)' }}>
          <h2 id="bcp-title" className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
            🧪 Backtest — {currentStrategy?.name ?? 'No strategy selected'}
          </h2>
          <div className="flex items-center gap-2">
            {/* Controls */}
            <button
              onClick={() => addLog('🔍 Config Discovery started...', 'SYSTEM')}
              disabled={backTestInProgress}
              title="Run N config permutations and rank results"
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              🔍 Config Discovery
            </button>
            <button
              onClick={() => setActiveTab(1)}
              disabled={!backTestResult}
              title="View most recent backtest results"
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              💠 View Live Results
            </button>
            <button
              onClick={handleRun}
              disabled={!canRun}
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            >
              {backTestInProgress ? 'Running…' : '▶ Run Test'}
            </button>
            <button
              onClick={handlePause}
              disabled={!backTestInProgress}
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              {isPaused ? '▶ Resume' : '⏸ Pause'}
            </button>
            <button
              onClick={handleStop}
              disabled={!backTestInProgress}
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              ⏹ Stop
            </button>
            <button onClick={onClose} className="ml-2 text-lg" style={{ color: 'var(--text-muted)' }} aria-label="Close">✕</button>
          </div>
        </div>

        {/* Progress bar */}
        {backTestInProgress && (
          <div className="px-5 py-2 shrink-0 space-y-1" style={{ borderBottom: '1px solid var(--bg-card)' }}>
            <div className="flex justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
              <span className="flex gap-4">
                <span>Progress: {backTestProgress}%</span>
                <span>TP1: {tpSlAdj.TP1}</span>
                <span>TP2: {tpSlAdj.TP2}</span>
                <span>TP3: {tpSlAdj.TP3}</span>
                <span>SL: {tpSlAdj.SL}</span>
              </span>
              <span>{isPaused ? '⏸ Paused' : '● Running'}</span>
            </div>
            <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-card)' }}>
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{ width: `${backTestProgress}%`, background: 'var(--accent-blue)' }}
              />
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="shrink-0">
          <TabBar tabs={TABS} active={activeTab} onChange={setActiveTab} />
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">

          {/* ── Tab 0: Config ── */}
          {activeTab === 0 && (
            <div className="p-5 space-y-5 overflow-y-auto max-h-full">
              {error && <p className="text-xs" style={{ color: 'var(--accent-red)' }}>{error}</p>}

              <div className="grid grid-cols-4 gap-5">
                {/* Column 1: Lookback / Training / Testing Windows */}
                <div className="space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Time Windows</p>

                  <SpinField
                    label="Historical Data Lookback"
                    value={config.lookbackDays ?? 180}
                    onChange={(v) => patch('lookbackDays', v)}
                    min={1}
                    max={365}
                    suffix="days"
                  />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_DAYS}
                    onSelect={(v) => patch('lookbackDays', v)}
                    format={(v) => `${v}d`}
                  />

                  <SpinField
                    label="Strategy Training Window"
                    value={config.trainingDays ?? 90}
                    onChange={(v) => patch('trainingDays', v)}
                    min={1}
                    max={365}
                    suffix="days"
                  />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_DAYS}
                    onSelect={(v) => patch('trainingDays', v)}
                    format={(v) => `${v}d`}
                  />

                  <SpinField
                    label="Out-of-Sample Testing"
                    value={config.testingDays ?? 30}
                    onChange={(v) => patch('testingDays', v)}
                    min={1}
                    max={365}
                    suffix="days"
                  />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_DAYS}
                    onSelect={(v) => patch('testingDays', v)}
                    format={(v) => `${v}d`}
                  />

                  <div className="border-t pt-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
                    <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Mode</p>
                    <div className="flex flex-col gap-2">
                      {[
                        { label: 'Mode 1 — Historical', value: 'historical' },
                        { label: 'Mode 2 — Live Replay', value: 'live_replay' },
                      ].map((option) => (
                        <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name="mode"
                            checked={config.mode === option.value}
                            onChange={() => patch('mode', option.value as 'historical' | 'live_replay')}
                            className="accent-blue-500"
                          />
                          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{option.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Column 2: Basic Settings & Capital */}
                <div className="space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Basic Settings</p>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Start Date</label>
                      <input
                        type="date"
                        value={config.startDate}
                        onChange={(e) => patch('startDate', e.target.value)}
                        className="w-full px-2 py-1.5 rounded text-xs focus:outline-none"
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>End Date</label>
                      <input
                        type="date"
                        value={config.endDate}
                        onChange={(e) => patch('endDate', e.target.value)}
                        className="w-full px-2 py-1.5 rounded text-xs focus:outline-none"
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                      />
                    </div>
                  </div>

                  <SelectField
                    label="TP/SL Mode"
                    value={config.tpslMode}
                    onChange={(v) => patch('tpslMode', v)}
                    options={[
                      { label: 'Fibonacci', value: 'fibonacci' },
                      { label: 'Hybrid', value: 'hybrid' },
                      { label: 'Fixed', value: 'fixed' },
                    ]}
                  />

                  <SelectField
                    label="SL Adjustment"
                    value={config.slAdjustmentMode}
                    onChange={(v) => patch('slAdjustmentMode', v)}
                    options={[
                      { label: 'Adaptive v2.0', value: 'adaptiveV2' },
                      { label: 'Static', value: 'static' },
                    ]}
                  />

                  <div className="space-y-1">
                    <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Initial Capital (USD)</label>
                    <div className="space-y-1.5">
                      <input
                        type="number"
                        value={config.initialCapital}
                        onChange={(e) => patch('initialCapital', parseFloat(e.target.value))}
                        min={500}
                        step={1000}
                        className="w-full px-2 py-1.5 rounded text-sm focus:outline-none"
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                      />
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Current: ${config.initialCapital.toLocaleString('en-US')}</div>
                    </div>
                  </div>
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_INITIAL_CAPITAL}
                    onSelect={(v) => patch('initialCapital', v)}
                    format={(v) => v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`}
                  />

                  <SpinField
                    label="Commission (fraction)"
                    value={config.commissionPercentage ?? 0.0004}
                    onChange={(v) => patch('commissionPercentage', v)}
                    min={0}
                    max={0.05}
                    step={0.0001}
                  />
                </div>

                {/* Column 3: Adaptive SL v2.0 */}
                <div className="space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Adaptive SL v2.0</p>

                  {/* Preset radio buttons */}
                  <div className="flex flex-col gap-1.5">
                    {(['conservative', 'balanced', 'aggressive', 'custom'] as const).map((p) => {
                      const icons = { conservative: '🐢', balanced: '⚖️', aggressive: '🚀', custom: '💠' };
                      return (
                        <label key={p} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name="sl-preset"
                            checked={config.adaptiveSLPreset === p}
                            onChange={() => {
                              if (p !== 'custom') applyAdaptiveSLPreset(p as 'conservative' | 'balanced' | 'aggressive');
                              else patch('adaptiveSLPreset', 'custom');
                            }}
                            className="accent-blue-500"
                          />
                          <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{icons[p]} {p}</span>
                        </label>
                      );
                    })}
                  </div>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.enabled}
                      onChange={(e) => patchAdaptiveSL('enabled', e.target.checked)}
                      className="accent-blue-500"
                    />
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Enable Adaptive SL</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.delayEnabled}
                      onChange={(e) => patchAdaptiveSL('delayEnabled', e.target.checked)}
                      className="accent-blue-500"
                    />
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Delay SL</span>
                  </label>

                  <SpinField label="Delay Bars" value={config.adaptiveSL.delayBars} onChange={(v) => patchAdaptiveSL('delayBars', v)} min={0} max={20} />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_DELAY_BARS}
                    onSelect={(v) => patchAdaptiveSL('delayBars', v)}
                  />

                  <SpinField label="Emergency SL %" value={config.adaptiveSL.emergencySlPct} onChange={(v) => patchAdaptiveSL('emergencySlPct', v)} min={0.5} max={10} step={0.1} suffix="%" />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_EMERGENCY_SL}
                    onSelect={(v) => patchAdaptiveSL('emergencySlPct', v)}
                    format={(v) => `${v}%`}
                  />

                  <SpinField label="Vol Lookback" value={config.adaptiveSL.volatilityLookback} onChange={(v) => patchAdaptiveSL('volatilityLookback', v)} min={5} max={100} />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_VOL_LOOKBACK}
                    onSelect={(v) => patchAdaptiveSL('volatilityLookback', v)}
                  />

                  <SpinField label="Vol Multiplier" value={config.adaptiveSL.volatilityMultiplier} onChange={(v) => patchAdaptiveSL('volatilityMultiplier', v)} min={0.5} max={10} step={0.1} suffix="×" />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_VOL_MULTIPLIER}
                    onSelect={(v) => patchAdaptiveSL('volatilityMultiplier', v)}
                    format={(v) => `${v}×`}
                  />

                  <SpinField label="Min SL %" value={config.adaptiveSL.minSlPct} onChange={(v) => patchAdaptiveSL('minSlPct', v)} min={0} max={10} step={0.1} suffix="%" />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_MIN_SL}
                    onSelect={(v) => patchAdaptiveSL('minSlPct', v)}
                    format={(v) => `${v}%`}
                  />

                  <SpinField label="Max SL %" value={config.adaptiveSL.maxSlPct} onChange={(v) => patchAdaptiveSL('maxSlPct', v)} min={0} max={20} step={0.1} suffix="%" />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_MAX_SL}
                    onSelect={(v) => patchAdaptiveSL('maxSlPct', v)}
                    format={(v) => `${v}%`}
                  />

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.useStructureSl}
                      onChange={(e) => patchAdaptiveSL('useStructureSl', e.target.checked)}
                      className="accent-blue-500"
                    />
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Market Structure SL</span>
                  </label>
                </div>

                {/* Column 4: Risk / Reward + Advanced */}
                <div className="space-y-4">
                  <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Risk / Reward</p>

                  <SpinField label="Risk per Trade %" value={config.riskPerTradePct} onChange={(v) => patch('riskPerTradePct', v)} min={1} max={100} step={1} suffix="%" />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_RISK_PCT}
                    onSelect={(v) => patch('riskPerTradePct', v)}
                    format={(v) => `${v}%`}
                  />

                  <SpinField label="Min R:R Ratio" value={config.minRiskRewardRatio} onChange={(v) => patch('minRiskRewardRatio', v)} min={0.5} max={10} step={0.1} />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_RR_RATIO}
                    onSelect={(v) => patch('minRiskRewardRatio', v)}
                    format={(v) => `1:${(v).toFixed(1)}`}
                  />

                  <SpinField label="Max Bars Held" value={config.maxBarsHeld} onChange={(v) => patch('maxBarsHeld', v)} min={1} max={500} />
                  <PresetButtonRow
                    label="Quick-set"
                    values={PRESET_MAX_BARS}
                    onSelect={(v) => patch('maxBarsHeld', v)}
                  />

                  <div className="border-t pt-3 space-y-3" style={{ borderColor: 'var(--border)' }}>
                    <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Advanced</p>

                    <SpinField label="Max Leverage" value={config.maxLeverage ?? 10} onChange={(v) => patch('maxLeverage', v)} min={1} max={100} suffix="x" />
                    <PresetButtonRow
                      label="Quick-set"
                      values={PRESET_MAX_LEVERAGE}
                      onSelect={(v) => patch('maxLeverage', v)}
                      format={(v) => `${v}x`}
                    />

                    <SpinField label="Confluence Threshold" value={config.confluenceThreshold ?? 40} onChange={(v) => patch('confluenceThreshold', v)} min={0} max={100} suffix="pts" />
                    <div className="space-y-1">
                      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Adjust</p>
                      <div className="flex gap-1">
                        <button
                          onClick={() => patch('confluenceThreshold', Math.max(0, (config.confluenceThreshold ?? 40) - 2))}
                          className="flex-1 px-2 py-1 rounded text-xs font-medium transition-colors"
                          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                        >
                          [-2]
                        </button>
                        <button
                          onClick={() => patch('confluenceThreshold', Math.max(0, (config.confluenceThreshold ?? 40) - 1))}
                          className="flex-1 px-2 py-1 rounded text-xs font-medium transition-colors"
                          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                        >
                          [-1]
                        </button>
                        <button
                          onClick={() => patch('confluenceThreshold', Math.min(100, (config.confluenceThreshold ?? 40) + 1))}
                          className="flex-1 px-2 py-1 rounded text-xs font-medium transition-colors"
                          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                        >
                          [+1]
                        </button>
                        <button
                          onClick={() => patch('confluenceThreshold', Math.min(100, (config.confluenceThreshold ?? 40) + 2))}
                          className="flex-1 px-2 py-1 rounded text-xs font-medium transition-colors"
                          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                        >
                          [+2]
                        </button>
                      </div>
                    </div>
                    <PresetButtonRow
                      label="Quick-set"
                      values={PRESET_CONFLUENCE}
                      onSelect={(v) => patch('confluenceThreshold', v)}
                    />
                    <button
                      onClick={() => addLog('🔄 Reset From Strategy — calculating recommended confluence threshold...', 'SYSTEM')}
                      className="w-full px-3 py-1.5 rounded text-xs font-medium transition-colors"
                      style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                    >
                      🔄 Reset From Strategy
                    </button>
                  </div>

                  <div className="border-t pt-3" style={{ borderColor: 'var(--border)' }}>
                    <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-secondary)' }}>Actions</p>
                    <button
                      onClick={saveAsCompare}
                      className="w-full px-3 py-1.5 rounded text-xs font-medium transition-colors"
                      style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                    >
                      📋 Save as Compare Baseline
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Tab 1: Live Output ── */}
          {activeTab === 1 && (
            <div className="p-4 h-full">
              <div className="rounded h-96 overflow-y-auto p-3 font-mono text-xs space-y-0.5" style={{ background: 'var(--bg-deep)', border: '1px solid var(--bg-card)' }}>
                {logs.length === 0 && (
                  <p className="italic" style={{ color: 'var(--text-faintest)' }}>No output yet. Run a backtest to see live logs.</p>
                )}
                {logs.map((l, i) => {
                  const colorMap: Record<string, string> = {
                    INFO: 'var(--text-secondary)',
                    WARNING: 'var(--accent-orange)',
                    ERROR: 'var(--accent-red)',
                    RISK: 'var(--accent-orange)',
                    SIGNAL: 'var(--accent-teal)',
                    SYSTEM: 'var(--accent-blue)',
                  };
                  const color = colorMap[l.level] ?? 'var(--text-secondary)';
                  return (
                    <div key={i} style={{ color }}>
                      <span style={{ color: 'var(--text-faintest)' }}>[{l.timestamp.slice(11, 19)}]</span>{' '}
                      <span style={{ color: 'var(--text-muted)' }}>[{l.level}]</span>{' '}
                      {l.message}
                    </div>
                  );
                })}
                <div ref={logsEndRef} />
              </div>
            </div>
          )}

          {/* ── Tab 2: Trades ── */}
          {activeTab === 2 && (
            <div className="p-4">
              {trades.length === 0 ? (
                <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>No trades recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse" style={{ color: 'var(--text-secondary)' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                        {['Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'Qty', 'P&L', 'P&L %', 'Bars', 'Exit Type', 'Status'].map((h) => (
                          <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((t: Trade, i: number) => (
                        <tr key={t.id ?? i} style={{ borderBottom: '1px solid var(--bg-card)' }}>
                          <td className="px-3 py-1.5 whitespace-nowrap">{t.entryTime.slice(0, 16).replace('T', ' ')}</td>
                          <td className="px-3 py-1.5">{fmt(t.entryPrice, 2)}</td>
                          <td className="px-3 py-1.5 whitespace-nowrap">{t.exitTime.slice(0, 16).replace('T', ' ')}</td>
                          <td className="px-3 py-1.5">{fmt(t.exitPrice, 2)}</td>
                          <td className="px-3 py-1.5">{t.quantity}</td>
                          <td className="px-3 py-1.5 font-medium" style={{ color: t.pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {t.pnl >= 0 ? '+' : ''}{fmt(t.pnl, 2)}
                          </td>
                          <td className="px-3 py-1.5" style={{ color: t.pnlPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {t.pnlPercentage >= 0 ? '+' : ''}{fmt(t.pnlPercentage, 2)}%
                          </td>
                          <td className="px-3 py-1.5">{t.bars}</td>
                          <td className="px-3 py-1.5">
                            <span
                              className="px-1.5 py-0.5 rounded text-xs font-medium"
                              style={
                                t.exitType === 'SL'
                                  ? { background: 'var(--accent-red-deeper)', color: 'var(--accent-red)' }
                                  : t.exitType?.startsWith('TP')
                                  ? { background: 'var(--accent-green-dark)', color: 'var(--accent-green)' }
                                  : { background: 'var(--bg-hover)', color: 'var(--text-secondary)' }
                              }
                            >
                              {t.exitType ?? '—'}
                            </span>
                          </td>
                          <td className="px-3 py-1.5">
                            <span className="text-xs" style={{ color: t.status === 'open' ? 'var(--accent-orange)' : 'var(--text-secondary)' }}>
                              {t.status ?? 'closed'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Tab 3: Metrics ── */}
          {activeTab === 3 && (
            <div className="p-5">
              {!result ? (
                <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>No backtest results yet.</p>
              ) : (
                <div className="space-y-5">
                  <div className="grid grid-cols-4 gap-3">
                    <MetricCard
                      label="Total Return"
                      value={`${result.returnPercentage >= 0 ? '+' : ''}${fmt(result.returnPercentage, 2)}%`}
                      sub={`$${fmt(result.totalReturn, 2)}`}
                    />
                    <MetricCard
                      label="Win Rate"
                      value={`${fmt(result.winRate * 100, 1)}%`}
                      sub={`${result.winningTrades}W / ${result.losingTrades}L`}
                    />
                    <MetricCard
                      label="Sharpe Ratio"
                      value={fmt(result.sharpeRatio, 2)}
                    />
                    <MetricCard
                      label="Max Drawdown"
                      value={`${fmt(result.maxDrawdown, 2)}%`}
                    />
                    <MetricCard
                      label="Profit Factor"
                      value={fmt(result.profitFactor, 2)}
                    />
                    <MetricCard
                      label="Avg Win"
                      value={`$${fmt(result.averageWin, 2)}`}
                    />
                    <MetricCard
                      label="Avg Loss"
                      value={`$${fmt(result.averageLoss, 2)}`}
                    />
                    <MetricCard
                      label="Total Trades"
                      value={String(result.totalTrades)}
                      sub={`Final: $${fmt(result.finalCapital, 2)}`}
                    />
                  </div>

                  {/* Equity curve placeholder */}
                  {result.equityCurve && result.equityCurve.length > 0 && (
                    <div className="rounded p-4" style={{ background: 'var(--bg-card)' }}>
                      <p className="text-xs mb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Equity Curve</p>
                      <div className="h-32 flex items-end gap-0.5">
                        {result.equityCurve.slice(-60).map((point, i) => {
                          const initial = result.initialCapital;
                          const pct = Math.max(0, Math.min(1, (point.value - initial * 0.8) / (initial * 0.6)));
                          return (
                            <div
                              key={i}
                              className="flex-1 rounded-t"
                              style={{
                                height: `${Math.max(4, pct * 100)}%`,
                                background: point.value >= initial ? 'var(--accent-green-mid)' : 'var(--accent-red-dark)',
                              }}
                            />
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Tab 4: AI Recommendations ── */}
          {activeTab === 4 && (
            <div className="p-5 space-y-4">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Preview and send an AI request for strategy recommendations based on the latest backtest results.
              </p>
              {!result ? (
                <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>Run a backtest first to generate AI recommendations.</p>
              ) : (
                <>
                  <div className="rounded p-3 text-xs font-mono space-y-1" style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)' }}>
                    <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>Auto-generated request preview:</p>
                    <p>Strategy: {currentStrategy?.name}</p>
                    <p>Win Rate: {fmt(result.winRate * 100, 1)}% | Sharpe: {fmt(result.sharpeRatio, 2)} | Drawdown: {fmt(result.maxDrawdown, 2)}%</p>
                    <p>Trades: {result.totalTrades} | Profit Factor: {fmt(result.profitFactor, 2)}</p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Additional context / questions:</label>
                    <textarea
                      value={aiRequest}
                      onChange={(e) => setAiRequest(e.target.value)}
                      rows={4}
                      placeholder="e.g. How can I improve the win rate while reducing drawdown?"
                      className="w-full px-3 py-2 rounded text-sm focus:outline-none resize-none"
                      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                    />
                  </div>
                  <button
                    className="px-4 py-2 rounded text-xs font-medium transition-colors"
                    style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
                    onClick={() => addLog('🤖 AI request sent (stub — integrate with AI endpoint).', 'SYSTEM')}
                  >
                    🤖 Send AI Request
                  </button>
                </>
              )}
            </div>
          )}

          {/* ── Tab 5: Compare ── */}
          {activeTab === 5 && (
            <div className="p-5">
              {!compareConfig ? (
                <div className="text-sm italic space-y-2" style={{ color: 'var(--text-muted)' }}>
                  <p>No comparison baseline saved.</p>
                  <p className="text-xs">Go to the Config tab and click &ldquo;Save as Compare Baseline&rdquo; to capture the current configuration, then adjust settings and run another backtest to compare.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-5">
                  <div>
                    <p className="text-xs font-semibold mb-3 uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Baseline Config</p>
                    <ConfigSummary cfg={compareConfig} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold mb-3 uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Current Config</p>
                    <ConfigSummary cfg={config} />
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ── Compare summary helper ────────────────────────────────────────────────────

function ConfigSummary({ cfg }: { cfg: BacktestConfigFull }) {
  const rows: Array<[string, string]> = [
    ['Start Date', cfg.startDate],
    ['End Date', cfg.endDate],
    ['Lookback Days', String(cfg.lookbackDays ?? 180)],
    ['Training Days', String(cfg.trainingDays ?? 90)],
    ['Testing Days', String(cfg.testingDays ?? 30)],
    ['Mode', cfg.mode === 'historical' ? 'Mode 1 — Historical' : 'Mode 2 — Live Replay'],
    ['TP/SL Mode', cfg.tpslMode],
    ['SL Adjustment', cfg.slAdjustmentMode],
    ['SL Preset', cfg.adaptiveSLPreset],
    ['Initial Capital', `$${cfg.initialCapital.toLocaleString()}`],
    ['Commission', `${((cfg.commissionPercentage ?? 0) * 100).toFixed(4)}%`],
    ['Risk per Trade', `${cfg.riskPerTradePct}%`],
    ['Min R:R', String(cfg.minRiskRewardRatio)],
    ['Max Bars Held', String(cfg.maxBarsHeld)],
    ['Max Leverage', `${cfg.maxLeverage ?? 10}x`],
    ['Confluence Threshold', `${cfg.confluenceThreshold ?? 40} pts`],
    ['Delay Bars', String(cfg.adaptiveSL.delayBars)],
    ['Emergency SL', `${cfg.adaptiveSL.emergencySlPct}%`],
    ['Vol Lookback', String(cfg.adaptiveSL.volatilityLookback)],
    ['Vol Multiplier', `${cfg.adaptiveSL.volatilityMultiplier}×`],
    ['Min SL', `${cfg.adaptiveSL.minSlPct}%`],
    ['Max SL', `${cfg.adaptiveSL.maxSlPct}%`],
  ];
  return (
    <div className="rounded p-3 space-y-1 max-h-96 overflow-y-auto" style={{ background: 'var(--bg-card)' }}>
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between text-xs">
          <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
          <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>{value}</span>
        </div>
      ))}
    </div>
  );
}
