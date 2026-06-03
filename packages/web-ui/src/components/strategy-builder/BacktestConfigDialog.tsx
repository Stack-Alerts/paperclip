'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { X, Play, Square, Pause, RotateCcw, Settings, Terminal, TrendingUp, BarChart3, Sparkles, GitCompare, ChevronUp, ChevronDown } from 'lucide-react';
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

// Generate a uniform-step chip series. Per-row counts hand-picked to fill the
// chip track at the standard 1440 dialog width without overflow into the
// spinbox cell (board pre-merge revision 4: "by the same incrementation",
// no irregular jumps, no leftover slack).
function chipSeries(start: number, step: number, count: number, decimals = 0): number[] {
  return Array.from({ length: count }, (_, i) => {
    const v = start + i * step;
    return decimals > 0 ? Number(v.toFixed(decimals)) : v;
  });
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

// ─── Chip row helper (used for parity with thickclient duration / percentage rows) ─────
//
// Each row pairs (a) preset chip buttons with (b) a numeric spinbox + unit suffix on the
// right. Both controls write to the same `onSelect` setter, so typing in the spinbox or
// using the up/down spinners updates the active chip, and clicking a chip updates the
// spinbox value. This mirrors the thick-client which exposes both controls on every row.
type ChipValue = string | number;
function ChipRow({
  label,
  values,
  current,
  onSelect,
  disabled,
  format,
  unit,
  unitPosition = 'suffix',
  min,
  max,
  step,
}: {
  label: string;
  values: ChipValue[];
  current: ChipValue | null | undefined;
  onSelect: (v: ChipValue) => void;
  disabled: boolean;
  format?: (v: ChipValue) => string;
  unit?: string;
  unitPosition?: 'prefix' | 'suffix';
  min?: number;
  max?: number;
  step?: number;
}) {
  const fmt = format ?? ((v: ChipValue) => String(v));
  // Chip sizing is now driven by `flex-1 basis-0` on each chip (board post-merge
  // revision 6: "too cramped, there is more space available" + thick-client reference).
  // Each row grows its chips uniformly to consume the full chip-track width, so chips
  // self-balance across viewport sizes and there is no leftover slack between the
  // last chip and the spinbox. Cycle 5's per-chip `min-w/w` constants would fight
  // `flex-1`, so they're intentionally not applied here.
  const numericCurrent =
    current === null || current === undefined
      ? ''
      : typeof current === 'number'
        ? current
        : Number(current);
  const numericValue = typeof numericCurrent === 'number' ? numericCurrent : 0;
  const handleSpinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    if (raw === '') return;
    const n = Number(raw);
    if (Number.isNaN(n)) return;
    onSelect(n);
  };
  const bumpBy = (delta: number) => {
    const next = numericValue + delta;
    const clamped =
      typeof max === 'number' && next > max
        ? max
        : typeof min === 'number' && next < min
          ? min
          : next;
    // Avoid floating-point noise when step is a clean decimal.
    const stepStr = step !== undefined ? String(step) : '1';
    const decimals = stepStr.includes('.') ? stepStr.split('.')[1].length : 0;
    const rounded = decimals > 0 ? Number(clamped.toFixed(decimals)) : clamped;
    onSelect(rounded);
  };
  const stepDelta = step ?? 1;
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)_76px] items-center gap-x-1.5 gap-y-0">
      <span
        className="text-[11px] font-medium truncate"
        style={{ color: 'var(--text-secondary)' }}
        title={label}
      >
        {label}
      </span>
      <div className="flex gap-1 flex-nowrap items-stretch min-w-0">
        {values.map((v) => {
          const isActive = current === v;
          return (
            <button
              key={String(v)}
              disabled={disabled}
              onClick={() => onSelect(v)}
              className="basis-0 grow shrink min-w-0 py-2 rounded-[4px] text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap text-center"
              style={{
                background: isActive ? 'rgba(46, 140, 255, 0.18)' : 'var(--bg-deep)',
                border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.55)' : 'var(--border)'}`,
                color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontVariantNumeric: 'tabular-nums',
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
      {/* Spinbox: one bordered field with inline value + unit + stacked stepper buttons.
          Rest state: neutral border that matches the chip border weight — every spinbox
          looks identical (board post-merge revision 7). Hover reveals a subtle accent
          glow; focus-within keeps the accent for keyboard users. The value-text tint
          when matching a chip preset is preserved as the only at-rest pairing signal. */}
      <div
        className="flex items-stretch rounded overflow-hidden h-[26px] border border-solid border-[var(--border)] transition-[border-color,box-shadow] hover:border-[rgba(46,140,255,0.55)] hover:shadow-[0_0_0_2px_rgba(46,140,255,0.15)] focus-within:border-[rgba(46,140,255,0.55)] focus-within:shadow-[0_0_0_2px_rgba(46,140,255,0.25)]"
        style={{
          background: 'rgba(255, 255, 255, 0.03)',
        }}
      >
        {unit && unitPosition === 'prefix' && (
          <span
            className="flex items-center pl-1 pr-0.5 text-[11px] leading-none whitespace-nowrap"
            style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
          >
            {unit}
          </span>
        )}
        <input
          type="number"
          value={numericCurrent}
          onChange={handleSpinChange}
          disabled={disabled}
          min={min}
          max={max}
          step={step}
          aria-label={`${label} value`}
          className="flex-1 min-w-0 px-0.5 text-[11px] focus:outline-none focus:ring-0 disabled:opacity-50 disabled:cursor-not-allowed text-right bg-transparent appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield]"
          style={{
            // Muted-blue value text — same `--text-secondary` (#8AAEC8) the chip-row
            // labels ("Lookback", "Training", "Starting Capital", "Min Risk:Reward",
            // "Risk %", "Leverage") already use, so the spinbox value sits in the same
            // visual tier as its immediately-adjacent row label and complements the
            // theme (board post-merge revision 9).
            color: 'var(--text-secondary)',
            fontVariantNumeric: 'tabular-nums',
          }}
        />
        {unit && unitPosition === 'suffix' && (
          <span
            className="flex items-center pl-0.5 pr-1 text-[10px] leading-none whitespace-nowrap"
            style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
          >
            {unit}
          </span>
        )}
        {/* Stacked stepper — always visible, not hidden behind browser spin-button defaults */}
        <div
          className="flex flex-col shrink-0 border-l"
          style={{ borderColor: 'var(--border)' }}
        >
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled || (typeof max === 'number' && numericValue >= max)}
            onClick={() => bumpBy(stepDelta)}
            aria-label={`Increment ${label}`}
            className="flex-1 px-1 flex items-center justify-center transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => {
              if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }}
          >
            <ChevronUp size={10} />
          </button>
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled || (typeof min === 'number' && numericValue <= min)}
            onClick={() => bumpBy(-stepDelta)}
            aria-label={`Decrement ${label}`}
            className="flex-1 px-1 flex items-center justify-center transition-colors disabled:opacity-30 disabled:cursor-not-allowed border-t"
            style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
            onMouseEnter={(e) => {
              if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }}
          >
            <ChevronDown size={10} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Config Tab — 3-column grid layout matching thick-client exactly ─────────────────
//
// Layout: three bordered section cards [Configuration | Adaptive SL v2.0 | Risk/Reward].
// Each card holds vertically-stacked ChipRow groups that share a single locked
// `100px label + 1fr chips + 120px spinbox` template — chips never wrap into the
// spinbox slot, spinboxes line up section-wide.
//
// Section card wrapper for visual separation (board polish-pass spec).
const SectionCard = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section
    className="rounded-[4px] px-3 py-3 space-y-3"
    style={{
      border: '1px solid var(--border)',
      background: 'rgba(255, 255, 255, 0.02)',
    }}
  >
    <h3
      className="text-xs font-semibold uppercase tracking-wider pb-2"
      style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}
    >
      {title}
    </h3>
    {children}
  </section>
);
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
  const [lookbackDays, setLookbackDays] = useState<ChipValue>(90);
  const [trainingDays, setTrainingDays] = useState<ChipValue>(60);
  const [testingDays, setTestingDays] = useState<ChipValue>(30);
  const [mode, setMode] = useState<'walk-forward' | 'walk' | 'live-replay'>('walk-forward');
  const [tpSlConfig, setTpSlConfig] = useState<string>('Default');
  const [slAdjustment, setSlAdjustment] = useState<'Adaptive v2.0' | 'Static'>('Adaptive v2.0');
  const [adaptivePreset, setAdaptivePreset] = useState<'Conservative' | 'Balanced' | 'Aggressive' | 'Custom'>('Balanced');
  const [delayStopLoss, setDelayStopLoss] = useState(true);
  const [marketStructureStop, setMarketStructureStop] = useState(true);
  const [stopLossDelay, setStopLossDelay] = useState<ChipValue>(2);
  const [emergency, setEmergency] = useState<ChipValue>(2.0);
  const [volatilityLookback, setVolatilityLookback] = useState<ChipValue>(20);
  const [volatilityMultiplier, setVolatilityMultiplier] = useState<ChipValue>(1.2);
  const [minStopLoss, setMinStopLoss] = useState<ChipValue>(0.7);
  const [maxStopLoss, setMaxStopLoss] = useState<ChipValue>(2.0);
  const [minRiskReward, setMinRiskReward] = useState<ChipValue>(1.2);
  const [maxRisk, setMaxRisk] = useState<ChipValue>(10);
  const [leverage, setLeverage] = useState<ChipValue>(10);
  const [confluence, setConfluence] = useState<string>('Boost from Strategy');
  const [minBarsHeld, setMinBarsHeld] = useState<ChipValue>(5);
  const [maxBarsHeld, setMaxBarsHeld] = useState<ChipValue>(200);

  const applyLookbackToDates = useCallback((days: number) => {
    setLookbackDays(days);
    onChange({ startDate: daysAgo(days), endDate: today() });
  }, [onChange]);

  return (
    <div className="h-full overflow-auto pb-6">
      {/* 3-Column Grid: Configuration | Adaptive SL v2.0 | Risk/Reward */}
      <div className="grid grid-cols-[33fr_33fr_34fr] gap-5 px-2 py-3 items-start">

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 1: CONFIGURATION (35%)
            ════════════════════════════════════════════════════════════════════ */}
        <SectionCard title="Configuration">
          {/* Basic Settings section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Basic Settings
            </div>
            <div className="space-y-3">
              <ChipRow
                label="Lookback"
                values={chipSeries(30, 30, 8)}
                current={lookbackDays}
                onSelect={(v) => applyLookbackToDates(Number(v))}
                disabled={disabled}
                unit="d"
                min={1}
                max={3650}
                step={30}
              />
              <ChipRow
                label="Training"
                values={chipSeries(30, 30, 8)}
                current={trainingDays}
                onSelect={setTrainingDays}
                disabled={disabled}
                unit="d"
                min={1}
                max={3650}
                step={30}
              />
              <ChipRow
                label="Testing"
                values={chipSeries(30, 30, 8)}
                current={testingDays}
                onSelect={setTestingDays}
                disabled={disabled}
                unit="d"
                min={1}
                max={3650}
                step={30}
              />
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Mode section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Mode
            </div>
            <div className="flex flex-row flex-wrap gap-1">
              {(['walk-forward', 'walk', 'live-replay'] as const).map((m) => {
                const labels = {
                  'walk-forward': 'Mode 1: Historical',
                  'walk': 'Mode 2: Walk',
                  'live-replay': 'Mode 2: Live Replay',
                };
                const isActive = mode === m;
                return (
                  <button
                    key={m}
                    disabled={disabled}
                    onClick={() => setMode(m)}
                    className="px-1 py-0.5 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
                    style={{
                      background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-deep)',
                      border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                      color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    }}
                    onMouseEnter={(e) => {
                      if (!disabled && !isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)';
                    }}
                  >
                    {labels[m]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* TP/SL Config section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              TP/SL Config
            </div>
            <select
              disabled={disabled}
              value={tpSlConfig}
              onChange={(e) => setTpSlConfig(e.target.value)}
              className="w-full px-2 py-1 rounded text-[11px] focus:outline-none disabled:opacity-50"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              <option>Fibonacci</option>
              <option>Hybrid</option>
              <option>Fixed</option>
            </select>
          </div>

          {/* Stop Loss Adjustment section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Stop Loss Adjustment
            </div>
            <div className="flex flex-row flex-wrap gap-1">
              {(['Adaptive v2.0', 'Static'] as const).map((opt) => {
                const isActive = slAdjustment === opt;
                return (
                  <button
                    key={opt}
                    disabled={disabled}
                    onClick={() => setSlAdjustment(opt)}
                    className="px-1 py-0.5 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
                    style={{
                      background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-deep)',
                      border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                      color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    }}
                    onMouseEnter={(e) => {
                      if (!disabled && !isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)';
                    }}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          </div>
        </SectionCard>

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 2: ADAPTIVE SL v2.0 (35%)
            ════════════════════════════════════════════════════════════════════ */}
        <SectionCard title="Adaptive SL v2.0">
          {/* Presets section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Presets
            </div>
            <div className="flex flex-row flex-wrap gap-1">
              {(['Conservative', 'Balanced', 'Aggressive', 'Custom'] as const).map((preset) => {
                const isActive = adaptivePreset === preset;
                return (
                  <button
                    key={preset}
                    disabled={disabled}
                    onClick={() => setAdaptivePreset(preset)}
                    className="px-1 py-0.5 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
                    style={{
                      background: isActive ? 'rgba(46, 140, 255, 0.15)' : 'var(--bg-deep)',
                      border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.5)' : 'var(--border)'}`,
                      color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                      minWidth: 0,
                    }}
                    onMouseEnter={(e) => {
                      if (!disabled && !isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)';
                    }}
                  >
                    {preset}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Checkboxes */}
          <div className="flex flex-row flex-wrap gap-3">
            <label className="flex items-center gap-2 text-[11px] cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                disabled={disabled}
                checked={delayStopLoss}
                onChange={(e) => setDelayStopLoss(e.target.checked)}
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              Delay Stop-Loss
            </label>
            <label className="flex items-center gap-2 text-[11px] cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
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

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Volatility/SL Controls */}
          <div className="space-y-3">
            <ChipRow
              label="Stop Loss Delay"
              values={chipSeries(1, 1, 8)}
              current={stopLossDelay}
              onSelect={setStopLossDelay}
              disabled={disabled}
              format={(v) => `${v}`}
              unit="bars"
              min={0}
              max={50}
              step={1}
            />
            <ChipRow
              label="Emergency"
              values={chipSeries(1.0, 0.25, 7, 2)}
              current={emergency}
              onSelect={setEmergency}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(2)}`}
              unit="%"
              min={0.1}
              max={20}
              step={0.25}
            />
            <ChipRow
              label="Vol Lookback"
              values={chipSeries(5, 5, 8)}
              current={volatilityLookback}
              onSelect={setVolatilityLookback}
              disabled={disabled}
              format={(v) => `${v}`}
              unit="bars"
              min={5}
              max={500}
              step={5}
            />
            <ChipRow
              label="Vol Multiplier"
              values={chipSeries(0.5, 0.5, 8, 1)}
              current={volatilityMultiplier}
              onSelect={setVolatilityMultiplier}
              disabled={disabled}
              unit="x"
              min={0.1}
              max={20}
              step={0.5}
            />
            <ChipRow
              label="Min Stop-Loss"
              values={chipSeries(0.5, 0.5, 8, 1)}
              current={minStopLoss}
              onSelect={setMinStopLoss}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}`}
              unit="%"
              min={0.1}
              max={20}
              step={0.5}
            />
            <ChipRow
              label="Max Stop-Loss"
              values={chipSeries(1, 1, 8)}
              current={maxStopLoss}
              onSelect={setMaxStopLoss}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(0)}`}
              unit="%"
              min={0.5}
              max={50}
              step={1}
            />
          </div>
        </SectionCard>

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 3: RISK / REWARD (30%)
            ════════════════════════════════════════════════════════════════════ */}
        <SectionCard title="Risk / Reward">
          {/* Capital & Exposure */}
          <div className="space-y-3">
            <ChipRow
              label="Starting Capital"
              values={chipSeries(5000, 5000, 8)}
              current={config.initialCapital ?? 10000}
              onSelect={(v) => onChange({ initialCapital: Number(v) })}
              disabled={disabled}
              format={(v) => {
                const n = Number(v);
                if (n >= 1000) return `${(n / 1000).toFixed(0)}k`;
                return `${n}`;
              }}
              unit="$"
              unitPosition="prefix"
              min={100}
              max={10_000_000}
              step={1000}
            />
            <ChipRow
              label="Min Risk:Reward"
              values={chipSeries(1, 0.5, 8, 1)}
              current={minRiskReward}
              onSelect={setMinRiskReward}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}`}
              unit="x"
              min={1}
              max={100}
              step={0.5}
            />
            <ChipRow
              label="Risk %"
              values={chipSeries(0.5, 0.5, 8, 1)}
              current={maxRisk}
              onSelect={setMaxRisk}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}`}
              unit="%"
              min={0.5}
              max={100}
              step={0.5}
            />
            <ChipRow
              label="Leverage"
              values={chipSeries(5, 5, 8)}
              current={leverage}
              onSelect={setLeverage}
              disabled={disabled}
              unit="x"
              min={1}
              max={125}
              step={5}
            />
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Confluence */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Confluence
            </div>
            <select
              disabled={disabled}
              value={confluence}
              onChange={(e) => setConfluence(e.target.value)}
              className="w-full px-2 py-1 rounded text-[11px] focus:outline-none disabled:opacity-50"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              <option>Boost from Strategy</option>
              <option>Independent Score</option>
              <option>Disabled</option>
            </select>
          </div>

          {/* Hold Duration */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
              Hold Duration
            </div>
            <div className="space-y-3">
              <ChipRow
                label="Min Bars Held"
                values={chipSeries(5, 5, 8)}
                current={minBarsHeld}
                onSelect={setMinBarsHeld}
                disabled={disabled}
                format={(v) => `${v}`}
                unit="bars"
                min={0}
                max={1000}
                step={5}
              />
              <ChipRow
                label="Max Bars Held"
                values={chipSeries(25, 25, 8)}
                current={maxBarsHeld}
                onSelect={setMaxBarsHeld}
                disabled={disabled}
                format={(v) => `${v}`}
                unit="bars"
                min={1}
                max={10000}
                step={25}
              />
            </div>
          </div>
        </SectionCard>
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
      className="rounded-[4px] mb-4"
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
        <div className="flex-1 overflow-auto px-4 py-4" style={{ background: 'var(--bg-deep)' }}>
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
