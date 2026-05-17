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
  commissionPercentage: 0.001,
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
  },
  riskPerTradePct: 1.0,
  minRiskRewardRatio: 1.2,
  maxBarsHeld: 50,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function TabBar({ tabs, active, onChange }: { tabs: string[]; active: number; onChange: (i: number) => void }) {
  return (
    <div className="flex border-b border-zinc-700 overflow-x-auto">
      {tabs.map((t, i) => (
        <button
          key={t}
          onClick={() => onChange(i)}
          className={`px-4 py-2 text-xs font-medium whitespace-nowrap transition-colors ${
            i === active
              ? 'border-b-2 border-purple-500 text-purple-300'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
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
      <label className="text-xs text-zinc-400">{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          min={min}
          max={max}
          step={step ?? 1}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
        />
        {suffix && <span className="text-xs text-zinc-500 shrink-0">{suffix}</span>}
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
      <label className="text-xs text-zinc-400">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
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
    <div className="bg-zinc-800 rounded p-3 space-y-0.5">
      <div className="text-xs text-zinc-400">{label}</div>
      <div className="text-lg font-semibold text-zinc-100">{value}</div>
      {sub && <div className="text-xs text-zinc-500">{sub}</div>}
    </div>
  );
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

  useEffect(() => {
    if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

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

      // Forward full config with all fields to engine
      await runBacktest({
        strategyId: currentStrategy.id,
        startDate: config.startDate,
        endDate: config.endDate,
        initialCapital: config.initialCapital,
        commissionPercentage: config.commissionPercentage,
        mode: config.mode,
        tpslMode: config.tpslMode,
        slAdjustmentMode: config.slAdjustmentMode,
        adaptiveSLPreset: config.adaptiveSLPreset,
        adaptiveSL: config.adaptiveSL,
        riskPerTradePct: config.riskPerTradePct,
        minRiskRewardRatio: config.minRiskRewardRatio,
        maxBarsHeld: config.maxBarsHeld,
      });
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

      <div className="relative w-full max-w-5xl mx-4 rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 shrink-0">
          <h2 id="bcp-title" className="text-sm font-semibold text-zinc-50">
            🧪 Backtest — {currentStrategy?.name ?? 'No strategy selected'}
          </h2>
          <div className="flex items-center gap-2">
            {/* Controls */}
            <button
              onClick={handleRun}
              disabled={!canRun}
              className="px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium disabled:opacity-40 transition-colors"
            >
              {backTestInProgress ? 'Running…' : '▶ Run Test'}
            </button>
            <button
              onClick={handlePause}
              disabled={!backTestInProgress}
              className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-medium disabled:opacity-40 transition-colors"
            >
              {isPaused ? '▶ Resume' : '⏸ Pause'}
            </button>
            <button
              onClick={handleStop}
              disabled={!backTestInProgress}
              className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-medium disabled:opacity-40 transition-colors"
            >
              ⏹ Stop
            </button>
            <button onClick={onClose} className="ml-2 text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close">✕</button>
          </div>
        </div>

        {/* Progress bar */}
        {backTestInProgress && (
          <div className="px-5 py-2 border-b border-zinc-800 shrink-0 space-y-1">
            <div className="flex justify-between text-xs text-zinc-400">
              <span className="flex gap-4">
                <span>Progress: {backTestProgress}%</span>
                <span>TP1: {tpSlAdj.TP1}</span>
                <span>TP2: {tpSlAdj.TP2}</span>
                <span>TP3: {tpSlAdj.TP3}</span>
                <span>SL: {tpSlAdj.SL}</span>
              </span>
              <span>{isPaused ? '⏸ Paused' : '● Running'}</span>
            </div>
            <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-600 rounded-full transition-all duration-300"
                style={{ width: `${backTestProgress}%` }}
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
            <div className="p-5 space-y-5">
              {error && <p className="text-xs text-red-400">{error}</p>}

              {/* Lookback preset buttons */}
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Lookback Preset</p>
                <div className="flex flex-wrap gap-2">
                  {PRESET_DAYS.map((d) => (
                    <button
                      key={d}
                      onClick={() => applyPresetDays(d)}
                      className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium border border-zinc-700 transition-colors"
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-5">
                {/* Column 1: Basic Settings */}
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">Basic Settings</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">Start Date</label>
                      <input
                        type="date"
                        value={config.startDate}
                        onChange={(e) => patch('startDate', e.target.value)}
                        className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">End Date</label>
                      <input
                        type="date"
                        value={config.endDate}
                        onChange={(e) => patch('endDate', e.target.value)}
                        className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                      />
                    </div>
                  </div>
                  <SelectField
                    label="Mode"
                    value={config.mode}
                    onChange={(v) => patch('mode', v)}
                    options={[
                      { label: 'Mode 1 — Historical', value: 'historical' },
                      { label: 'Mode 2 — Live Replay', value: 'live_replay' },
                    ]}
                  />
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
                  <SpinField label="Initial Capital (USD)" value={config.initialCapital} onChange={(v) => patch('initialCapital', v)} min={500} step={1000} />
                  <SpinField label="Commission" value={config.commissionPercentage ?? 0} onChange={(v) => patch('commissionPercentage', v)} min={0} max={0.05} step={0.0001} suffix="fraction" />
                </div>

                {/* Column 2: Adaptive SL v2.0 */}
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">Adaptive SL v2.0</p>

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
                            className="accent-purple-500"
                          />
                          <span className="text-xs text-zinc-300 capitalize">{icons[p]} {p}</span>
                        </label>
                      );
                    })}
                  </div>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.enabled}
                      onChange={(e) => patchAdaptiveSL('enabled', e.target.checked)}
                      className="accent-purple-500"
                    />
                    <span className="text-xs text-zinc-300">Enable Adaptive SL</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.delayEnabled}
                      onChange={(e) => patchAdaptiveSL('delayEnabled', e.target.checked)}
                      className="accent-purple-500"
                    />
                    <span className="text-xs text-zinc-300">Delay SL</span>
                  </label>

                  <SpinField label="Delay Bars" value={config.adaptiveSL.delayBars} onChange={(v) => patchAdaptiveSL('delayBars', v)} min={0} max={20} />
                  <SpinField label="Emergency SL %" value={config.adaptiveSL.emergencySlPct} onChange={(v) => patchAdaptiveSL('emergencySlPct', v)} min={0.5} max={10} step={0.1} suffix="%" />
                  <SpinField label="Vol Lookback" value={config.adaptiveSL.volatilityLookback} onChange={(v) => patchAdaptiveSL('volatilityLookback', v)} min={5} max={100} />
                  <SpinField label="Vol Multiplier" value={config.adaptiveSL.volatilityMultiplier} onChange={(v) => patchAdaptiveSL('volatilityMultiplier', v)} min={0.5} max={10} step={0.1} suffix="×" />
                  <SpinField label="Min SL %" value={config.adaptiveSL.minSlPct} onChange={(v) => patchAdaptiveSL('minSlPct', v)} min={0} max={10} step={0.1} suffix="%" />
                  <SpinField label="Max SL %" value={config.adaptiveSL.maxSlPct} onChange={(v) => patchAdaptiveSL('maxSlPct', v)} min={0} max={20} step={0.1} suffix="%" />

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.adaptiveSL.useStructureSl}
                      onChange={(e) => patchAdaptiveSL('useStructureSl', e.target.checked)}
                      className="accent-purple-500"
                    />
                    <span className="text-xs text-zinc-300">Market Structure SL</span>
                  </label>
                </div>

                {/* Column 3: Risk / Reward */}
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">Risk / Reward</p>
                  <SpinField label="Risk per Trade %" value={config.riskPerTradePct} onChange={(v) => patch('riskPerTradePct', v)} min={0.1} max={10} step={0.1} suffix="%" />
                  <SpinField label="Min R:R Ratio" value={config.minRiskRewardRatio} onChange={(v) => patch('minRiskRewardRatio', v)} min={0.5} max={10} step={0.1} />
                  <SpinField label="Max Bars Held" value={config.maxBarsHeld} onChange={(v) => patch('maxBarsHeld', v)} min={1} max={500} />

                  <div className="border-t border-zinc-700 pt-3">
                    <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide mb-2">Actions</p>
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={saveAsCompare}
                        className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-medium transition-colors"
                      >
                        📋 Save as Compare Baseline
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Tab 1: Live Output ── */}
          {activeTab === 1 && (
            <div className="p-4 h-full">
              <div className="bg-zinc-950 rounded border border-zinc-800 h-96 overflow-y-auto p-3 font-mono text-xs space-y-0.5">
                {logs.length === 0 && (
                  <p className="text-zinc-600 italic">No output yet. Run a backtest to see live logs.</p>
                )}
                {logs.map((l, i) => {
                  const colors: Record<string, string> = {
                    INFO: 'text-zinc-300',
                    WARNING: 'text-yellow-400',
                    ERROR: 'text-red-400',
                    RISK: 'text-orange-400',
                    SIGNAL: 'text-cyan-400',
                    SYSTEM: 'text-purple-400',
                  };
                  return (
                    <div key={i} className={colors[l.level] ?? 'text-zinc-300'}>
                      <span className="text-zinc-600">[{l.timestamp.slice(11, 19)}]</span>{' '}
                      <span className="text-zinc-500">[{l.level}]</span>{' '}
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
                <p className="text-sm text-zinc-500 italic">No trades recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-zinc-300 border-collapse">
                    <thead>
                      <tr className="border-b border-zinc-700 text-zinc-400">
                        {['Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'Qty', 'P&L', 'P&L %', 'Bars', 'Exit Type', 'Status'].map((h) => (
                          <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((t: Trade, i: number) => (
                        <tr key={t.id ?? i} className="border-b border-zinc-800 hover:bg-zinc-800/50">
                          <td className="px-3 py-1.5 whitespace-nowrap">{t.entryTime.slice(0, 16).replace('T', ' ')}</td>
                          <td className="px-3 py-1.5">{fmt(t.entryPrice, 2)}</td>
                          <td className="px-3 py-1.5 whitespace-nowrap">{t.exitTime.slice(0, 16).replace('T', ' ')}</td>
                          <td className="px-3 py-1.5">{fmt(t.exitPrice, 2)}</td>
                          <td className="px-3 py-1.5">{t.quantity}</td>
                          <td className={`px-3 py-1.5 font-medium ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {t.pnl >= 0 ? '+' : ''}{fmt(t.pnl, 2)}
                          </td>
                          <td className={`px-3 py-1.5 ${t.pnlPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {t.pnlPercentage >= 0 ? '+' : ''}{fmt(t.pnlPercentage, 2)}%
                          </td>
                          <td className="px-3 py-1.5">{t.bars}</td>
                          <td className="px-3 py-1.5">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                              t.exitType === 'SL' ? 'bg-red-900/50 text-red-300' :
                              t.exitType?.startsWith('TP') ? 'bg-green-900/50 text-green-300' :
                              'bg-zinc-700 text-zinc-300'
                            }`}>
                              {t.exitType ?? '—'}
                            </span>
                          </td>
                          <td className="px-3 py-1.5">
                            <span className={`text-xs ${t.status === 'open' ? 'text-yellow-400' : 'text-zinc-400'}`}>
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
                <p className="text-sm text-zinc-500 italic">No backtest results yet.</p>
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
                    <div className="bg-zinc-800 rounded p-4">
                      <p className="text-xs text-zinc-400 mb-2 font-medium">Equity Curve</p>
                      <div className="h-32 flex items-end gap-0.5">
                        {result.equityCurve.slice(-60).map((point, i) => {
                          const initial = result.initialCapital;
                          const pct = Math.max(0, Math.min(1, (point.value - initial * 0.8) / (initial * 0.6)));
                          return (
                            <div
                              key={i}
                              className={`flex-1 rounded-t ${point.value >= initial ? 'bg-green-600/70' : 'bg-red-600/70'}`}
                              style={{ height: `${Math.max(4, pct * 100)}%` }}
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
              <p className="text-xs text-zinc-400">
                Preview and send an AI request for strategy recommendations based on the latest backtest results.
              </p>
              {!result ? (
                <p className="text-sm text-zinc-500 italic">Run a backtest first to generate AI recommendations.</p>
              ) : (
                <>
                  <div className="bg-zinc-800 rounded p-3 text-xs text-zinc-300 font-mono space-y-1">
                    <p className="text-zinc-400 font-medium">Auto-generated request preview:</p>
                    <p>Strategy: {currentStrategy?.name}</p>
                    <p>Win Rate: {fmt(result.winRate * 100, 1)}% | Sharpe: {fmt(result.sharpeRatio, 2)} | Drawdown: {fmt(result.maxDrawdown, 2)}%</p>
                    <p>Trades: {result.totalTrades} | Profit Factor: {fmt(result.profitFactor, 2)}</p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-zinc-400">Additional context / questions:</label>
                    <textarea
                      value={aiRequest}
                      onChange={(e) => setAiRequest(e.target.value)}
                      rows={4}
                      placeholder="e.g. How can I improve the win rate while reducing drawdown?"
                      className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500 resize-none"
                    />
                  </div>
                  <button
                    className="px-4 py-2 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors"
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
                <div className="text-sm text-zinc-500 italic space-y-2">
                  <p>No comparison baseline saved.</p>
                  <p className="text-xs">Go to the Config tab and click &ldquo;Save as Compare Baseline&rdquo; to capture the current configuration, then adjust settings and run another backtest to compare.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-5">
                  <div>
                    <p className="text-xs font-semibold text-zinc-300 mb-3 uppercase tracking-wide">Baseline Config</p>
                    <ConfigSummary cfg={compareConfig} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-zinc-300 mb-3 uppercase tracking-wide">Current Config</p>
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
    ['Mode', cfg.mode === 'historical' ? 'Mode 1 — Historical' : 'Mode 2 — Live Replay'],
    ['TP/SL Mode', cfg.tpslMode],
    ['SL Adjustment', cfg.slAdjustmentMode],
    ['SL Preset', cfg.adaptiveSLPreset],
    ['Initial Capital', `$${cfg.initialCapital.toLocaleString()}`],
    ['Commission', `${((cfg.commissionPercentage ?? 0) * 100).toFixed(3)}%`],
    ['Risk per Trade', `${cfg.riskPerTradePct}%`],
    ['Min R:R', String(cfg.minRiskRewardRatio)],
    ['Max Bars Held', String(cfg.maxBarsHeld)],
    ['Emergency SL', `${cfg.adaptiveSL.emergencySlPct}%`],
    ['Vol Multiplier', `${cfg.adaptiveSL.volatilityMultiplier}×`],
    ['Min SL', `${cfg.adaptiveSL.minSlPct}%`],
    ['Max SL', `${cfg.adaptiveSL.maxSlPct}%`],
  ];
  return (
    <div className="bg-zinc-800 rounded p-3 space-y-1">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between text-xs">
          <span className="text-zinc-400">{label}</span>
          <span className="text-zinc-200 font-medium">{value}</span>
        </div>
      ))}
    </div>
  );
}
