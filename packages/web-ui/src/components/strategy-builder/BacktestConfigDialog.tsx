'use client';

import { useState, useCallback, useContext, useEffect, useRef, createContext } from 'react';
import { X, Play, Square, Pause, Settings, Terminal, TrendingUp, BarChart3, BarChart2, Sparkles, GitCompare, ChevronUp, ChevronDown } from 'lucide-react';
import { AppBrand } from '@/components/shared/AppBrand';
import { ThemeSelector } from './ThemeSelector';
import { useTooltipSettings } from './TooltipSettingsContext';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BacktestConfig, BacktestStatusMessage } from '@/lib/strategy-builder/types';
import { getBacktestResults } from '@/lib/strategy-builder/api';
import { RichTooltip, type TooltipContent } from './RichTooltip';
import {
  TT_LOOKBACK, TT_TRAINING, TT_TESTING,
  TT_MODE_HISTORICAL, TT_MODE_WALK, TT_MODE_LIVE_REPLAY,
  TT_TPSL_CONFIG, TT_SL_ADJUSTMENT,
  TT_PRESET_CONSERVATIVE, TT_PRESET_BALANCED, TT_PRESET_AGGRESSIVE, TT_PRESET_CUSTOM,
  TT_DELAY_STOP_LOSS, TT_MARKET_STRUCTURE_STOP,
  TT_STOP_LOSS_DELAY, TT_EMERGENCY, TT_VOL_LOOKBACK, TT_VOL_MULTIPLIER,
  TT_MIN_STOP_LOSS, TT_MAX_STOP_LOSS,
  TT_STARTING_CAPITAL, TT_MIN_RR, TT_RISK_PCT, TT_LEVERAGE,
  TT_CONFLUENCE, TT_HOLD_DURATION, TT_MIN_BARS_HELD, TT_MAX_BARS_HELD,
  TT_PRESETS_LABEL,
  TT_RUN_TEST, TT_PAUSE, TT_STOP, TT_CONFIG_DISCOVERY, TT_VIEW_LIVE_RESULTS, TT_CANCEL,
} from './BacktestConfigTooltips';
import { LiveOutputPanel } from '@/components/backtest/live-output/LiveOutputPanel';
import { BacktestCountersRow } from '@/components/backtest/live-output/BacktestCountersRow';
import { TradesPanel } from '@/components/backtest/trades/TradesPanel';
import { MetricsPanel } from '@/components/backtest/metrics/MetricsPanel';
import { AiRecommendationsPanel } from '@/components/backtest/ai-recommendations/AiRecommendationsPanel';
import { ComparePanel } from '@/components/backtest/compare/ComparePanel';
import { BacktestProgressMeter } from '@/components/backtest/progress-meter';

export interface BacktestConfigDialogProps {
  open: boolean;
  onClose: () => void;
  // When true, the dialog is being rendered in the popped-out window route
  // (/strategy-builder/backtest-config). The standalone surface fills the
  // viewport, shows Pop In instead of Pop Out, and skips the backdrop +
  // sidebar-anchored geometry the inline drawer uses (BTCAAAAA-34600 —
  // mirrors the StrategyBrowserDialog standalone pattern).
  standalone?: boolean;
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


// ─── STATUS section font scaling (BTCAAAAA-34264 → scoped down by BTCAAAAA-34312) ─
//
// The board's original cycle-20 ask was narrow: STATUS-section readability only
// (their screenshot was a closeup of the STATUS checklist). Cycle-19 over-applied
// the bump across the entire dialog (section headers, chip text, spinbox values,
// row labels, sub-section labels). BTCAAAAA-34312 scopes the scale back to
// STATUS only — every other surface returns to its pre-cycle-19 (pre-`a11b1ebdd`)
// hard-coded size, while STATUS retains the three-step Compact / Normal / Large
// scale driven by the dialog-header Aa−/Aa+ control. localStorage key is
// preserved so a user's prior choice still applies (now to STATUS only).
type FontScale = 'Compact' | 'Normal' | 'Large';

type BacktestFontSizes = {
  /** Status section monospace lines (the idle checklist / live event stream). */
  statusText: string;
  /** Status section "Status" header label. */
  statusLabel: string;
};

// BTCAAAAA-34924: cycle-21's per-scale `statusMaxHeight` (115/135/155) clamped
// the Status block and forced an internal scroll bar even when the dialog had
// room left. STATUS now flexes to fill whatever vertical space the dialog body
// leaves over; the font-scale picker only adjusts text sizes here.
const FONT_SCALES: Record<FontScale, BacktestFontSizes> = {
  // Compact ≈ pre-cycle-19 statusText sizing. Kept for power-users who want
  // maximum density across the whole dialog.
  Compact: {
    statusText: '11px',
    statusLabel: '10px',
  },
  // Normal = the bumped STATUS size the board actually asked for in cycle-19.
  // The rest of the dialog stays at the pre-cycle-19 sizes hard-coded inline.
  Normal: {
    statusText: '13px',
    statusLabel: '11px',
  },
  // Large = one step bigger for accessibility / large monitors.
  Large: {
    statusText: '14px',
    statusLabel: '12px',
  },
};

const FONT_SCALE_STORAGE_KEY = 'backtestConfigDialog.fontScale';

function readStoredFontScale(): FontScale {
  if (typeof window === 'undefined') return 'Normal';
  try {
    const raw = window.localStorage.getItem(FONT_SCALE_STORAGE_KEY);
    if (raw === 'Compact' || raw === 'Normal' || raw === 'Large') return raw;
  } catch {
    // localStorage may be unavailable (private mode, SSR hydration); fall back silently.
  }
  return 'Normal';
}

// Threaded via context so StatusColumn can read the active scale without prop
// drilling from the dialog root. Only StatusColumn consumes this — the rest of
// the dialog uses inline hard-coded pre-cycle-19 sizes (BTCAAAAA-34312).
const FontSizesContext = createContext<BacktestFontSizes>(FONT_SCALES.Normal);
const useFontSizes = () => useContext(FontSizesContext);

// ─── Adaptive SL V2.0 — canonical preset values ──────────────────────────────
//
// Each named preset (Conservative / Balanced / Aggressive) is a frozen snapshot
// of the 8 Adaptive SL knobs. Clicking a preset chip applies all 8 at once.
// Whenever the user diverges any single knob from the active preset's snapshot,
// the chip auto-flips to `Custom` so the label never lies about what's loaded.
// (BTCAAAAA-34256 Item A.)
type AdaptivePresetName = 'Conservative' | 'Balanced' | 'Aggressive' | 'Custom';
type AdaptiveValues = {
  delayStopLoss: boolean;
  marketStructureStop: boolean;
  stopLossDelay: number;
  emergency: number;
  volatilityLookback: number;
  volatilityMultiplier: number;
  minStopLoss: number;
  maxStopLoss: number;
};
const ADAPTIVE_PRESETS: Record<Exclude<AdaptivePresetName, 'Custom'>, AdaptiveValues> = {
  Conservative: {
    delayStopLoss: true,
    marketStructureStop: true,
    stopLossDelay: 3,
    emergency: 1.5,
    volatilityLookback: 30,
    volatilityMultiplier: 1.0,
    minStopLoss: 0.5,
    maxStopLoss: 1.5,
  },
  Balanced: {
    delayStopLoss: true,
    marketStructureStop: true,
    stopLossDelay: 2,
    emergency: 2.0,
    volatilityLookback: 20,
    volatilityMultiplier: 1.2,
    minStopLoss: 0.7,
    maxStopLoss: 2.0,
  },
  Aggressive: {
    delayStopLoss: false,
    marketStructureStop: true,
    stopLossDelay: 1,
    emergency: 3.0,
    volatilityLookback: 10,
    volatilityMultiplier: 1.5,
    minStopLoss: 1.0,
    maxStopLoss: 3.0,
  },
};
function adaptiveMatchesPreset(values: AdaptiveValues, preset: Exclude<AdaptivePresetName, 'Custom'>): boolean {
  const canonical = ADAPTIVE_PRESETS[preset];
  return (Object.keys(canonical) as Array<keyof AdaptiveValues>).every(
    (k) => canonical[k] === values[k],
  );
}

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
  tooltip,
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
  // BTCAAAAA-34257: when supplied, the row label, every chip, and the spinbox
  // surface the same field-level institutional definition on hover/focus.
  tooltip?: TooltipContent;
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
  // BTCAAAAA-34541: when the typed/stepped value sits outside the chip preset
  // range (no chip matches), the spinbox carries the same "selected" glow chips
  // use — so every row still has exactly one element flagged as the active
  // selection. Mirrors the chip's strict-equality `isActive` check, plus a
  // null/empty guard so a cleared input never paints as selected.
  const spinboxIsActiveSelection =
    current !== null &&
    current !== undefined &&
    current !== '' &&
    !values.some((v) => v === current);
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
  // BTCAAAAA-34257: helper to wrap an element in RichTooltip when a row-level
  // tooltip is supplied. Keeps the JSX below readable.
  const wrap = (node: React.ReactElement) =>
    tooltip ? <RichTooltip content={tooltip}>{node}</RichTooltip> : node;
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)_76px] items-center gap-x-1.5 gap-y-0">
      {wrap(
        <span
          className="text-[11px] font-medium truncate cursor-help"
          style={{ color: 'var(--text-secondary)' }}
          title={tooltip ? undefined : label}
        >
          {label}
        </span>,
      )}
      <div className="flex gap-1 flex-nowrap items-stretch min-w-0">
        {values.map((v) => {
          const isActive = current === v;
          const btn = (
            <button
              disabled={disabled}
              onClick={() => onSelect(v)}
              className="basis-0 grow shrink min-w-0 py-1.5 rounded-[4px] text-[10px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap text-center"
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
          // BTCAAAAA-34257: every chip on the row shows the same field tooltip.
          return tooltip ? (
            <RichTooltip key={String(v)} content={tooltip}>{btn}</RichTooltip>
          ) : (
            <span key={String(v)} className="contents">{btn}</span>
          );
        })}
      </div>
      {/* Spinbox: one bordered field with inline value + unit + stacked stepper buttons.
          Rest state: neutral border that matches the chip border weight — every spinbox
          looks identical (board post-merge revision 7). Hover reveals a subtle accent
          glow; focus-within keeps the accent for keyboard users. The value-text tint
          when matching a chip preset is preserved as the only at-rest pairing signal.
          BTCAAAAA-34257: spinbox shares the row tooltip with label + chips. */}
      {wrap(
      <div
        className={`flex items-stretch rounded overflow-hidden h-[26px] border border-solid transition-[border-color,box-shadow] hover:border-[rgba(46,140,255,0.55)] hover:shadow-[0_0_0_2px_rgba(46,140,255,0.15)] focus-within:border-[rgba(46,140,255,0.55)] focus-within:shadow-[0_0_0_2px_rgba(46,140,255,0.25)] ${
          spinboxIsActiveSelection
            ? 'border-[rgba(46,140,255,0.55)]'
            : 'border-[var(--border)]'
        }`}
        style={{
          // BTCAAAAA-34541: same subtle-blue background tint chips use when
          // selected, so an out-of-range value reads as the active selection.
          background: spinboxIsActiveSelection
            ? 'rgba(46, 140, 255, 0.18)'
            : 'rgba(255, 255, 255, 0.03)',
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
            // theme (board post-merge revision 9). When the value is outside the chip
            // preset range, it switches to the chip-selected accent so the spinbox
            // doesn't look like a blue frame around grey text (BTCAAAAA-34541).
            color: spinboxIsActiveSelection
              ? 'var(--accent-blue)'
              : 'var(--text-secondary)',
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
      </div>,
      )}
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
// Vertical padding reduced from `py-3 space-y-3` → `py-2 space-y-2` per board
// revision 2026-06-03 so the three columns fit at 1280×720 without scroll.
const SectionCard = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => (
  <section
    className="rounded-[4px] px-3 py-1.5 space-y-1 h-full"
    style={{
      border: '1px solid var(--border)',
      background: 'rgba(255, 255, 255, 0.02)',
    }}
  >
    <h3
      className="text-xs font-semibold uppercase tracking-wider pb-1"
      style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}
    >
      {title}
    </h3>
    {children}
  </section>
);
//
// Cycle-13 (board revision 2026-06-03): the thick-client `📊 Status:`
// checklist lives on the Config tab itself — Live Output's separate function
// (live event stream) should not carry the idle checklist. Rendered as a
// frameless right-rail column with `Status` muted-label + the verbatim
// idle lines (or the streaming feed when a run is active).
// Verbatim thick-client content. Empty spacer lines from the cycle-10
// reference were dropped in cycle-13b to fit at 1280×720 — the section
// headers still scan visually because each is a different color tier.
const STATUS_IDLE_LINES: string[] = [
  'Status updates will appear here when backtest starts.',
  'During backtest you will see:',
  '✅ Data loading progress from Unified Data Manager',
  '✅ NautilusTrader initialization',
  '✅ Bar aggregation status',
  '✅ Hybrid data source routing (LakeAPI + Binance)',
  '✅ Real-time processing updates',
  'All terminal output will be captured and displayed here.',
];

function StatusColumn({
  logs,
  isRunning,
  headerRight,
}: {
  logs: BacktestStatusMessage[];
  isRunning: boolean;
  headerRight?: React.ReactNode;
}) {
  const fontSizes = useFontSizes();
  const showIdle = logs.length === 0 && !isRunning;
  // BTCAAAAA-34924: outer is a flex column that fills the wrapper allocated by
  // ConfigTab. The header row is auto-height; the monospace block grows with
  // `flex-1 min-h-0` so it consumes all remaining vertical room before any
  // internal scroll bar is shown.
  return (
    <div className="flex flex-col h-full min-h-0 space-y-0.5">
      <div className="flex items-center justify-between gap-2 flex-shrink-0">
        <div
          className="font-medium uppercase tracking-wider"
          style={{ color: 'var(--text-muted)', fontSize: fontSizes.statusLabel }}
        >
          Status
        </div>
        {headerRight}
      </div>
      <div
        className="font-mono leading-tight space-y-0 overflow-y-auto flex-1 min-h-0"
        style={{ color: 'var(--text-secondary)', fontSize: fontSizes.statusText }}
      >
        {showIdle
          ? STATUS_IDLE_LINES.map((line, idx) => (
              <div
                key={idx}
                style={{
                  color: line.startsWith('✅')
                    ? 'var(--text-secondary)'
                    : 'var(--text-muted)',
                  minHeight: '1em',
                }}
              >
                {line || ' '}
              </div>
            ))
          : (() => {
              // Status panel shows only SYSTEM-level messages (loading, calibration,
              // completion). Trade event messages (level=INFO) belong in Live Output.
              // Mirrors thick-client Status pane vs Live Output separation.
              const systemLogs = logs.filter(m => m.level === 'SYSTEM');
              return (systemLogs.length > 0 ? systemLogs : logs).slice(-200);
            })().map((msg, idx) => (
              <div
                key={`${msg.timestamp}-${idx}`}
                style={{
                  color:
                    msg.level === 'ERROR'
                      ? 'var(--accent-red)'
                      : msg.level === 'SYSTEM'
                        ? 'var(--accent-blue)'
                        : 'var(--text-secondary)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                <span style={{ color: 'var(--text-faint)' }}>
                  {msg.timestamp
                    ? new Date(msg.timestamp).toISOString().slice(11, 19) + ' '
                    : ''}
                </span>
                {msg.message}
              </div>
            ))}
      </div>
    </div>
  );
}

function ConfigTab({
  config,
  onChange,
  disabled,
  outputLogs,
  isRunning,
  fontScale,
  onFontScaleChange,
  lookbackDays,
  setLookbackDays,
  trainingDays,
  setTrainingDays,
  testingDays,
  setTestingDays,
  mode,
  setMode,
  tpSlConfig,
  setTpSlConfig,
  slAdjustment,
  setSlAdjustment,
  adaptivePreset,
  setAdaptivePreset,
  delayStopLoss,
  setDelayStopLoss,
  marketStructureStop,
  setMarketStructureStop,
  stopLossDelay,
  setStopLossDelay,
  emergency,
  setEmergency,
  volatilityLookback,
  setVolatilityLookback,
  volatilityMultiplier,
  setVolatilityMultiplier,
  minStopLoss,
  setMinStopLoss,
  maxStopLoss,
  setMaxStopLoss,
  minRiskReward,
  setMinRiskReward,
  maxRisk,
  setMaxRisk,
  leverage,
  setLeverage,
  confluence,
  setConfluence,
  minBarsHeld,
  setMinBarsHeld,
  maxBarsHeld,
  setMaxBarsHeld,
}: {
  config: Omit<BacktestConfig, 'strategyId'>;
  onChange: (patch: Partial<Omit<BacktestConfig, 'strategyId'>>) => void;
  disabled: boolean;
  outputLogs: BacktestStatusMessage[];
  isRunning: boolean;
  fontScale: FontScale;
  onFontScaleChange: (next: FontScale) => void;
  lookbackDays: ChipValue;
  setLookbackDays: (v: ChipValue) => void;
  trainingDays: ChipValue;
  setTrainingDays: (v: ChipValue) => void;
  testingDays: ChipValue;
  setTestingDays: (v: ChipValue) => void;
  mode: 'walk-forward' | 'walk' | 'live-replay';
  setMode: (v: 'walk-forward' | 'walk' | 'live-replay') => void;
  tpSlConfig: 'Fibonacci' | 'Hybrid' | 'Fixed';
  setTpSlConfig: (v: 'Fibonacci' | 'Hybrid' | 'Fixed') => void;
  slAdjustment: 'Adaptive v2.0' | 'Static';
  setSlAdjustment: (v: 'Adaptive v2.0' | 'Static') => void;
  adaptivePreset: AdaptivePresetName;
  setAdaptivePreset: (v: AdaptivePresetName) => void;
  delayStopLoss: boolean;
  setDelayStopLoss: (v: boolean) => void;
  marketStructureStop: boolean;
  setMarketStructureStop: (v: boolean) => void;
  stopLossDelay: ChipValue;
  setStopLossDelay: (v: ChipValue) => void;
  emergency: ChipValue;
  setEmergency: (v: ChipValue) => void;
  volatilityLookback: ChipValue;
  setVolatilityLookback: (v: ChipValue) => void;
  volatilityMultiplier: ChipValue;
  setVolatilityMultiplier: (v: ChipValue) => void;
  minStopLoss: ChipValue;
  setMinStopLoss: (v: ChipValue) => void;
  maxStopLoss: ChipValue;
  setMaxStopLoss: (v: ChipValue) => void;
  minRiskReward: ChipValue;
  setMinRiskReward: (v: ChipValue) => void;
  maxRisk: ChipValue;
  setMaxRisk: (v: ChipValue) => void;
  leverage: ChipValue;
  setLeverage: (v: ChipValue) => void;
  confluence: number;
  setConfluence: (v: number) => void;
  minBarsHeld: ChipValue;
  setMinBarsHeld: (v: ChipValue) => void;
  maxBarsHeld: ChipValue;
  setMaxBarsHeld: (v: ChipValue) => void;
}) {

  // Auto-Custom: re-evaluate whether the current 8 Adaptive SL values still
  // match the active preset's canonical snapshot. If they diverge, flip the
  // preset chip to `Custom`. A no-op when already on Custom or when the
  // current values still match (e.g. just clicked the preset chip).
  // BTCAAAAA-34256 Item A.
  const checkAdaptivePresetMatch = useCallback(
    (next: AdaptiveValues) => {
      if (adaptivePreset === 'Custom') return;
      if (!adaptiveMatchesPreset(next, adaptivePreset)) {
        setAdaptivePreset('Custom');
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [adaptivePreset],
  );
  const currentAdaptive: AdaptiveValues = {
    delayStopLoss,
    marketStructureStop,
    stopLossDelay: Number(stopLossDelay),
    emergency: Number(emergency),
    volatilityLookback: Number(volatilityLookback),
    volatilityMultiplier: Number(volatilityMultiplier),
    minStopLoss: Number(minStopLoss),
    maxStopLoss: Number(maxStopLoss),
  };
  const applyAdaptivePreset = useCallback((preset: Exclude<AdaptivePresetName, 'Custom'>) => {
    const v = ADAPTIVE_PRESETS[preset];
    setDelayStopLoss(v.delayStopLoss);
    setMarketStructureStop(v.marketStructureStop);
    setStopLossDelay(v.stopLossDelay);
    setEmergency(v.emergency);
    setVolatilityLookback(v.volatilityLookback);
    setVolatilityMultiplier(v.volatilityMultiplier);
    setMinStopLoss(v.minStopLoss);
    setMaxStopLoss(v.maxStopLoss);
    setAdaptivePreset(preset);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyLookbackToDates = useCallback((days: number) => {
    setLookbackDays(days);
    onChange({ startDate: daysAgo(days), endDate: today() });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onChange]);

  return (
    // BTCAAAAA-34924: root is a flex column so the 3-column form grid keeps
    // its natural height and the below-grid Status wrapper claims every
    // remaining pixel of vertical space inside the dialog body.
    <div className="h-full flex flex-col pb-2">
      {/* 3-Column Grid + below-grid Status section.
          Cycle-13b clarification 2026-06-03: the thick-client `📊 Status:`
          checklist belongs on the Config tab as a full-width text block
          **below** the 3-column grid — not as a 4th right-rail column.
          (Live Output handles a separate streaming role.) */}
      <div className="grid grid-cols-[33fr_33fr_34fr] gap-3 px-2 py-2 items-stretch flex-shrink-0">

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 1: CONFIGURATION (35%)
            ════════════════════════════════════════════════════════════════════ */}
        <SectionCard title="Configuration">
          {/* Basic Settings section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
              Basic Settings
            </div>
            <div className="space-y-1">
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
                tooltip={TT_LOOKBACK}
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
                tooltip={TT_TRAINING}
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
                tooltip={TT_TESTING}
              />
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Mode section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
              Mode
            </div>
            <div className="flex flex-row flex-wrap gap-1">
              {(['walk-forward', 'walk', 'live-replay'] as const).map((m) => {
                const labels = {
                  'walk-forward': 'Mode 1: Historical',
                  'walk': 'Mode 2: Walk',
                  'live-replay': 'Mode 2: Live Replay',
                };
                const tips: Record<typeof m, TooltipContent> = {
                  'walk-forward': TT_MODE_HISTORICAL,
                  'walk': TT_MODE_WALK,
                  'live-replay': TT_MODE_LIVE_REPLAY,
                };
                const isActive = mode === m;
                return (
                  <RichTooltip key={m} content={tips[m]}>
                    <button
                      disabled={disabled}
                      onClick={() => setMode(m)}
                      className="px-1 py-1 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
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
                  </RichTooltip>
                );
              })}
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* TP/SL Config section */}
          <div>
            <RichTooltip content={TT_TPSL_CONFIG}>
              <div className="text-[10px] font-medium uppercase mb-1 cursor-help" style={{ color: 'var(--text-muted)' }}>
                TP/SL Config
              </div>
            </RichTooltip>
            <div className="flex flex-row flex-wrap gap-1">
              {(['Fibonacci', 'Hybrid', 'Fixed'] as const).map((opt) => {
                const isActive = tpSlConfig === opt;
                return (
                  <RichTooltip key={opt} content={TT_TPSL_CONFIG}>
                    <button
                      disabled={disabled}
                      onClick={() => setTpSlConfig(opt)}
                      className="px-1 py-1 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
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
                  </RichTooltip>
                );
              })}
            </div>
          </div>

          {/* Stop Loss Adjustment section */}
          <div>
            <div className="text-[10px] font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
              Stop Loss Adjustment
            </div>
            <div className="flex flex-row flex-wrap gap-1">
              {(['Adaptive v2.0', 'Static'] as const).map((opt) => {
                const isActive = slAdjustment === opt;
                return (
                  <RichTooltip key={opt} content={TT_SL_ADJUSTMENT}>
                    <button
                      disabled={disabled}
                      onClick={() => setSlAdjustment(opt)}
                      className="px-1 py-1 rounded-[3px] text-[11px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap shrink-0"
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
                  </RichTooltip>
                );
              })}
            </div>
          </div>
        </SectionCard>

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 2: ADAPTIVE SL v2.0 (35%)
            ════════════════════════════════════════════════════════════════════ */}
        <div
          style={{
            opacity: slAdjustment === 'Static' ? 0.35 : 1,
            pointerEvents: slAdjustment === 'Static' ? 'none' : 'auto',
            transition: 'opacity 0.15s',
          }}
        >
        <SectionCard title="Adaptive SL v2.0">
          {/* Presets row — inline (cycle-16 board revision 2026-06-03).
              Matches ChipRow's `88px label | 1fr chips | 76px spinbox` template
              so the chip track aligns with Stop Loss Delay / Emergency / Vol
              Lookback below. No spinbox for this row (Presets is a discrete
              choice, not a numeric value), so the spinbox cell stays empty. */}
          <div className="grid grid-cols-[88px_minmax(0,1fr)_76px] items-center gap-x-1.5 gap-y-0">
            <RichTooltip content={TT_PRESETS_LABEL}>
              <span
                className="text-[11px] font-medium truncate cursor-help"
                style={{ color: 'var(--text-secondary)' }}
              >
                Presets
              </span>
            </RichTooltip>
            <div className="flex gap-1 flex-nowrap items-stretch min-w-0">
              {(['Conservative', 'Balanced', 'Aggressive', 'Custom'] as const).map((preset) => {
                const tips: Record<typeof preset, TooltipContent> = {
                  Conservative: TT_PRESET_CONSERVATIVE,
                  Balanced: TT_PRESET_BALANCED,
                  Aggressive: TT_PRESET_AGGRESSIVE,
                  Custom: TT_PRESET_CUSTOM,
                };
                const isActive = adaptivePreset === preset;
                return (
                  <RichTooltip key={preset} content={tips[preset]}>
                    <button
                      disabled={disabled}
                      onClick={() => {
                        if (preset === 'Custom') {
                          setAdaptivePreset('Custom');
                        } else {
                          applyAdaptivePreset(preset);
                        }
                      }}
                      className="basis-0 grow shrink min-w-0 py-1.5 px-0.5 rounded-[4px] text-[10px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-[1.1] text-center overflow-hidden"
                      style={{
                        background: isActive ? 'rgba(46, 140, 255, 0.18)' : 'var(--bg-deep)',
                        border: `1px solid ${isActive ? 'rgba(46, 140, 255, 0.55)' : 'var(--border)'}`,
                        color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
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
                  </RichTooltip>
                );
              })}
            </div>
            <div aria-hidden="true" />
          </div>

          {/* Checkboxes */}
          <div className="flex flex-row flex-wrap gap-3">
            <RichTooltip content={TT_DELAY_STOP_LOSS}>
              <label className="flex items-center gap-2 text-[11px] cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={delayStopLoss}
                  onChange={(e) => {
                    const next = e.target.checked;
                    setDelayStopLoss(next);
                    checkAdaptivePresetMatch({ ...currentAdaptive, delayStopLoss: next });
                  }}
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                Delay Stop-Loss
              </label>
            </RichTooltip>
            <RichTooltip content={TT_MARKET_STRUCTURE_STOP}>
              <label className="flex items-center gap-2 text-[11px] cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={marketStructureStop}
                  onChange={(e) => {
                    const next = e.target.checked;
                    setMarketStructureStop(next);
                    checkAdaptivePresetMatch({ ...currentAdaptive, marketStructureStop: next });
                  }}
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                Market Structure Stop-Loss
              </label>
            </RichTooltip>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Volatility/SL Controls */}
          <div className="space-y-1">
            <ChipRow
              label="Stop Loss Delay"
              values={chipSeries(1, 1, 8)}
              current={stopLossDelay}
              onSelect={(v) => {
                const n = Number(v);
                setStopLossDelay(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, stopLossDelay: n });
              }}
              disabled={disabled}
              format={(v) => `${v}`}
              unit="bars"
              min={0}
              max={50}
              step={1}
              tooltip={TT_STOP_LOSS_DELAY}
            />
            <ChipRow
              label="Emergency"
              values={chipSeries(1.0, 0.25, 7, 2)}
              current={emergency}
              onSelect={(v) => {
                const n = Number(v);
                setEmergency(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, emergency: n });
              }}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(2)}`}
              unit="%"
              min={0.1}
              max={20}
              step={0.25}
              tooltip={TT_EMERGENCY}
            />
            <ChipRow
              label="Vol Lookback"
              values={chipSeries(5, 5, 8)}
              current={volatilityLookback}
              onSelect={(v) => {
                const n = Number(v);
                setVolatilityLookback(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, volatilityLookback: n });
              }}
              disabled={disabled}
              format={(v) => `${v}`}
              unit="bars"
              min={5}
              max={500}
              step={5}
              tooltip={TT_VOL_LOOKBACK}
            />
            <ChipRow
              label="Vol Multiplier"
              values={chipSeries(0.5, 0.5, 8, 1)}
              current={volatilityMultiplier}
              onSelect={(v) => {
                const n = Number(v);
                setVolatilityMultiplier(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, volatilityMultiplier: n });
              }}
              disabled={disabled}
              unit="x"
              min={0.1}
              max={20}
              step={0.5}
              tooltip={TT_VOL_MULTIPLIER}
            />
            <ChipRow
              label="Min Stop-Loss"
              values={chipSeries(0.5, 0.5, 8, 1)}
              current={minStopLoss}
              onSelect={(v) => {
                const n = Number(v);
                setMinStopLoss(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, minStopLoss: n });
              }}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}`}
              unit="%"
              min={0.1}
              max={20}
              step={0.5}
              tooltip={TT_MIN_STOP_LOSS}
            />
            <ChipRow
              label="Max Stop-Loss"
              values={chipSeries(1, 1, 8)}
              current={maxStopLoss}
              onSelect={(v) => {
                const n = Number(v);
                setMaxStopLoss(n);
                checkAdaptivePresetMatch({ ...currentAdaptive, maxStopLoss: n });
              }}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(0)}`}
              unit="%"
              min={0.5}
              max={50}
              step={1}
              tooltip={TT_MAX_STOP_LOSS}
            />
          </div>
        </SectionCard>
        </div>

        {/* ═════════════════════════════════════════════════════════════════════
            COLUMN 3: RISK / REWARD (30%)
            ════════════════════════════════════════════════════════════════════ */}
        <SectionCard title="Risk / Reward">
          {/* Capital & Exposure */}
          <div className="space-y-1">
            <ChipRow
              label="Starting Capital"
              values={[500, 1000, 2000, 5000, 10000, 25000, 50000]}
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
              step={100}
              tooltip={TT_STARTING_CAPITAL}
            />
            <ChipRow
              label="Min Risk:Reward"
              values={[1.2, 1.5, 2.0, 2.2, 2.5, 2.7, 3.0]}
              current={minRiskReward}
              onSelect={setMinRiskReward}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(1)}`}
              unit="x"
              min={1}
              max={100}
              step={0.1}
              tooltip={TT_MIN_RR}
            />
            <ChipRow
              label="Risk %"
              values={[1, 2, 5, 7, 10, 12, 15]}
              current={maxRisk}
              onSelect={setMaxRisk}
              disabled={disabled}
              format={(v) => `${Number(v).toFixed(0)}`}
              unit="%"
              min={1}
              max={100}
              step={1}
              tooltip={TT_RISK_PCT}
            />
            <ChipRow
              label="Leverage"
              values={[3, 5, 10, 15, 20, 25, 30]}
              current={leverage}
              onSelect={setLeverage}
              disabled={disabled}
              unit="x"
              min={1}
              max={125}
              step={1}
              tooltip={TT_LEVERAGE}
            />
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'var(--border)' }} />

          {/* Hold Duration — moved above Confluence per BTCAAAAA-34256 Item B. */}
          <div>
            <RichTooltip content={TT_HOLD_DURATION}>
              <div className="text-[10px] font-medium uppercase mb-1 cursor-help" style={{ color: 'var(--text-muted)' }}>
                Hold Duration
              </div>
            </RichTooltip>
            <div className="space-y-1">
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
                tooltip={TT_MIN_BARS_HELD}
              />
              <ChipRow
                label="Max Bars Held"
                values={[15, 20, 25, 30, 40, 50, 75]}
                current={maxBarsHeld}
                onSelect={setMaxBarsHeld}
                disabled={disabled}
                format={(v) => `${v}`}
                unit="bars"
                min={1}
                max={500}
                step={1}
                tooltip={TT_MAX_BARS_HELD}
              />
            </div>
          </div>

          {/* Confluence — inline ChipRow-identical layout: same grid, same spinbox */}
          <div className="grid grid-cols-[88px_minmax(0,1fr)_76px] items-center gap-x-1.5">
            <RichTooltip content={TT_CONFLUENCE}>
              <span className="text-[11px] font-medium truncate cursor-help" style={{ color: 'var(--text-secondary)' }}>
                Confluence
              </span>
            </RichTooltip>
            {/* Chip track: Reset + increment buttons, flush like ChipRow */}
            <div className="flex gap-1 flex-nowrap items-stretch min-w-0">
              <button
                disabled={disabled}
                onClick={() => setConfluence(40)}
                className="basis-0 grow shrink min-w-0 py-1.5 rounded-[4px] text-[10px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap text-center"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                onMouseEnter={e => { if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)'; }}
              >
                Reset
              </button>
              {([-2, -1, 1, 2] as const).map(delta => (
                <button
                  key={delta}
                  disabled={disabled}
                  onClick={() => setConfluence(Math.max(0, Math.min(100, confluence + delta)))}
                  className="basis-0 grow shrink min-w-0 py-1.5 rounded-[4px] text-[10px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed leading-tight whitespace-nowrap text-center"
                  style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}
                  onMouseEnter={e => { if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-deep)'; }}
                >
                  {delta > 0 ? `+${delta}` : delta}
                </button>
              ))}
            </div>
            {/* Spinbox — identical structure to ChipRow spinbox */}
            <div
              className="flex items-stretch rounded overflow-hidden h-[26px] border border-solid transition-[border-color,box-shadow] hover:border-[rgba(46,140,255,0.55)] hover:shadow-[0_0_0_2px_rgba(46,140,255,0.15)] focus-within:border-[rgba(46,140,255,0.55)] focus-within:shadow-[0_0_0_2px_rgba(46,140,255,0.25)] border-[var(--border)]"
              style={{ background: 'rgba(255,255,255,0.03)' }}
            >
              <input
                type="number"
                value={confluence}
                disabled={disabled}
                min={0}
                max={100}
                step={1}
                aria-label="Confluence value"
                onChange={e => {
                  const n = Number(e.target.value);
                  if (!Number.isNaN(n)) setConfluence(Math.max(0, Math.min(100, n)));
                }}
                className="flex-1 min-w-0 px-0.5 text-[11px] focus:outline-none focus:ring-0 disabled:opacity-50 disabled:cursor-not-allowed text-right bg-transparent appearance-none [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield]"
                style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}
              />
              <span className="flex items-center pl-0.5 pr-1 text-[10px] leading-none whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
                pts
              </span>
            </div>
          </div>
        </SectionCard>

      </div>

      {/* Status section — full-width below the 3-column grid (cycle-13b
          clarification 2026-06-03: "status is supposed to be below the
          Configuration Blocks"). Frameless monospace text block. The
          Candles/Trades/TP-SL counter row was relocated to the dialog
          footer at the very bottom of the dialog (BTCAAAAA-34589).

          BTCAAAAA-34924: wrapper claims the remaining vertical space inside
          the dialog body with `flex-1 min-h-0`. `flex flex-col` is set so the
          inner StatusColumn (also a flex column with `h-full min-h-0`) can
          stretch to fill this wrapper — cycle-21's fixed `statusMaxHeight`
          clamp is gone, so the internal scroll bar now appears only when
          content truly exceeds the available room. */}
      <div className="px-2 pt-1 flex-1 min-h-0 flex flex-col">
        <StatusColumn
          logs={outputLogs}
          isRunning={isRunning}
          headerRight={
            <FontScalePicker scale={fontScale} onChange={onFontScaleChange} />
          }
        />
      </div>
    </div>
  );
}

// ─── Font scale picker — Aa−/Aa+ control (BTCAAAAA-34264) ─────────────────────
//
// Three discrete steps: Compact / Normal / Large. The Aa−/Aa+ buttons step
// through them; the active step is rendered between the buttons so the user
// always knows the current value. Sits in the dialog header next to the close
// button. The choice is persisted to localStorage by the parent.
const FONT_SCALE_ORDER: FontScale[] = ['Compact', 'Normal', 'Large'];
const FontScalePicker = ({
  scale,
  onChange,
}: {
  scale: FontScale;
  onChange: (next: FontScale) => void;
}) => {
  const idx = FONT_SCALE_ORDER.indexOf(scale);
  const canShrink = idx > 0;
  const canGrow = idx < FONT_SCALE_ORDER.length - 1;
  const step = (delta: number) => {
    const next = FONT_SCALE_ORDER[idx + delta];
    if (next) onChange(next);
  };
  return (
    <div
      role="group"
      aria-label="Dialog font size"
      className="flex items-center rounded-[4px] overflow-hidden"
      style={{ border: '1px solid var(--border)', background: 'var(--bg-deep)' }}
    >
      <button
        type="button"
        onClick={() => step(-1)}
        disabled={!canShrink}
        aria-label="Decrease font size"
        title="Decrease font size"
        className="px-2 py-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}
        onMouseEnter={(e) => {
          if (canShrink) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
      >
        <span style={{ fontSize: '11px' }}>A</span>
        <span style={{ fontSize: '13px' }}>a</span>
        <span style={{ marginLeft: 2 }}>−</span>
      </button>
      <span
        aria-live="polite"
        className="px-2 text-[10px] font-medium uppercase tracking-wider whitespace-nowrap select-none"
        style={{
          color: 'var(--text-muted)',
          borderLeft: '1px solid var(--border)',
          borderRight: '1px solid var(--border)',
        }}
      >
        {scale}
      </span>
      <button
        type="button"
        onClick={() => step(1)}
        disabled={!canGrow}
        aria-label="Increase font size"
        title="Increase font size"
        className="px-2 py-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}
        onMouseEnter={(e) => {
          if (canGrow) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
      >
        <span style={{ fontSize: '11px' }}>A</span>
        <span style={{ fontSize: '15px' }}>a</span>
        <span style={{ marginLeft: 2 }}>+</span>
      </button>
    </div>
  );
};

// ─── Main dialog ───────────────────────────────────────────────────────────────
export function BacktestConfigDialog({ open, onClose, standalone = false }: BacktestConfigDialogProps) {
  const {
    currentStrategy,
    backTestInProgress,
    backTestProgress,
    backTestResult,
    backTestLogs,
    runBacktest,
  } = useStrategyStore();

  const { settings: tooltipSettings, update: updateTooltipSettings } = useTooltipSettings();

  const [activeTab, setActiveTab] = useState<TabKey>('config');
  // Font scale picked from header Aa−/Aa+ control. Defaults to `Normal` per
  // BTCAAAAA-34264 acceptance #1; reads the persisted choice on mount so each
  // dialog open respects the user's last selection.
  const [fontScale, setFontScale] = useState<FontScale>('Normal');
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (open) setFontScale(readStoredFontScale());
  }, [open]);
  const updateFontScale = useCallback((next: FontScale) => {
    setFontScale(next);
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(FONT_SCALE_STORAGE_KEY, next);
      } catch {
        // localStorage may be disabled; choice still applies for this session.
      }
    }
  }, []);
  const fontSizes = FONT_SCALES[fontScale];
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

  // BTCAAAAA-34942: tail in-flight logs from the store so the Live Output /
  // STATUS panels update during the run instead of waiting for the 30 min
  // poll loop to resolve. handleStart seeds a "Starting backtest…" line
  // first; once the backend starts emitting via the store's poll loop, every
  // new entry that didn't exist on the prior tick is appended. Length is the
  // dedup key — backend `_backtest_runs[run_id]['logs']` is append-only.
  const lastSeenLogCountRef = useRef(0);
  useEffect(() => {
    if (!backTestInProgress && backTestLogs.length === 0) {
      lastSeenLogCountRef.current = 0;
      return;
    }
    if (backTestLogs.length > lastSeenLogCountRef.current) {
      const fresh = backTestLogs.slice(lastSeenLogCountRef.current);
      lastSeenLogCountRef.current = backTestLogs.length;
      setOutputLogs((prev) => [...prev, ...fresh]);
    }
  }, [backTestLogs, backTestInProgress]);

  // Backtest configuration state — lifted to parent so handleStart can access
  const [lookbackDays, setLookbackDays] = useState<ChipValue>(90);
  const [trainingDays, setTrainingDays] = useState<ChipValue>(60);
  const [testingDays, setTestingDays] = useState<ChipValue>(30);
  const [mode, setMode] = useState<'walk-forward' | 'walk' | 'live-replay'>('walk-forward');
  const [tpSlConfig, setTpSlConfig] = useState<'Fibonacci' | 'Hybrid' | 'Fixed'>('Fibonacci');
  const [slAdjustment, setSlAdjustment] = useState<'Adaptive v2.0' | 'Static'>('Adaptive v2.0');
  const [adaptivePreset, setAdaptivePreset] = useState<AdaptivePresetName>('Balanced');
  const [delayStopLoss, setDelayStopLoss] = useState<boolean>(ADAPTIVE_PRESETS.Balanced.delayStopLoss);
  const [marketStructureStop, setMarketStructureStop] = useState<boolean>(ADAPTIVE_PRESETS.Balanced.marketStructureStop);
  const [stopLossDelay, setStopLossDelay] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.stopLossDelay);
  const [emergency, setEmergency] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.emergency);
  const [volatilityLookback, setVolatilityLookback] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.volatilityLookback);
  const [volatilityMultiplier, setVolatilityMultiplier] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.volatilityMultiplier);
  const [minStopLoss, setMinStopLoss] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.minStopLoss);
  const [maxStopLoss, setMaxStopLoss] = useState<ChipValue>(ADAPTIVE_PRESETS.Balanced.maxStopLoss);
  const [minRiskReward, setMinRiskReward] = useState<ChipValue>(1.2);
  const [maxRisk, setMaxRisk] = useState<ChipValue>(10);
  const [leverage, setLeverage] = useState<ChipValue>(10);
  const [confluence, setConfluence] = useState<number>(40);
  const [minBarsHeld, setMinBarsHeld] = useState<ChipValue>(5);
  const [maxBarsHeld, setMaxBarsHeld] = useState<ChipValue>(200);

  const dialogRef = useRef<HTMLDivElement>(null);

  // Seed timeframe from current strategy when dialog opens
  useEffect(() => {
    if (open && currentStrategy?.settings?.timeframe) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
      const fullConfig = {
        // camelCase fields consumed by the store/API layer
        strategyId: currentStrategy.id,
        startDate: config.startDate,
        endDate: config.endDate,
        initialCapital: config.initialCapital,
        commissionPercentage: config.commissionPercentage,
        slippagePercentage: config.slippagePercentage,
        maxConcurrentPositions: config.maxConcurrentPositions,
        timeframe: config.timeframe,
        // snake_case fields consumed by MulticoreBacktestEngine
        starting_capital: config.initialCapital,
        commission_pct: config.commissionPercentage,
        slippage_pct: config.slippagePercentage,
        lookback_days: Number(lookbackDays),
        training_days: Number(trainingDays),
        testing_days: Number(testingDays),
        mode: mode === 'walk-forward' ? 1 : mode === 'walk' ? 2 : 3,
        tpsl_mode: tpSlConfig,
        sl_adjustment_mode: slAdjustment,
        adaptive_sl_preset: adaptivePreset,
        adaptive_sl: {
          enabled: slAdjustment === 'Adaptive v2.0',
          delay_enabled: delayStopLoss,
          delay_bars: Number(stopLossDelay),
          emergency_sl_pct: Number(emergency),
          volatility_lookback: Number(volatilityLookback),
          volatility_multiplier: Number(volatilityMultiplier),
          min_sl_pct: Number(minStopLoss),
          max_sl_pct: Number(maxStopLoss),
          use_structure_sl: marketStructureStop,
        },
        risk_per_trade_pct: Number(maxRisk),
        min_risk_reward: Number(minRiskReward),
        max_bars_held: Number(maxBarsHeld),
        min_bars_held: Number(minBarsHeld),
        max_leverage: Number(leverage),
        confluence_threshold: Number(confluence),
      };

      // Start the backtest and get runId
      const startResp = await runBacktest(fullConfig) as { runId: string };
      const runId = startResp?.runId;
      if (!runId) throw new Error('No runId returned from backtest start');

      // Poll for results and logs until backtest is done
      let attempts = 0;
      const maxAttempts = 600; // 10 min at 1s intervals
      const pollInterval = 1000;
      const seenLogIds = new Set<string>();

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;

        try {
          const result = await getBacktestResults(currentStrategy.id, runId) as {
            status: string;
            logs?: Array<{ message: string; level: string; timestamp: string }>;
          };

          if (result?.logs) {
            result.logs.forEach((log, idx) => {
              const logId = `${runId}-${idx}`;
              if (!seenLogIds.has(logId)) {
                seenLogIds.add(logId);
                setOutputLogs(prev => [
                  ...prev,
                  {
                    message: log.message,
                    level: log.level as BacktestStatusMessage['level'],
                    timestamp: log.timestamp,
                  },
                ]);
              }
            });
          }

          if (result?.status === 'done' || result?.status === 'error') {
            break;
          }
        } catch (pollErr) {
          console.warn('Poll error:', pollErr);
        }
      }

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
  }, [config, currentStrategy, runBacktest, lookbackDays, trainingDays, testingDays, mode, tpSlConfig, slAdjustment, adaptivePreset, delayStopLoss, stopLossDelay, emergency, volatilityLookback, volatilityMultiplier, minStopLoss, maxStopLoss, marketStructureStop, maxRisk, minRiskReward, maxBarsHeld, minBarsHeld, leverage, confluence]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !backTestInProgress) onClose();
  }, [onClose, backTestInProgress]);

  // Pop Out → standalone window route. Mirrors StrategyBrowserDialog's
  // window.open(URL, '_blank', size) pattern verbatim (BTCAAAAA-34600 Step 2):
  // a new browser window navigates to /strategy-builder/backtest-config which
  // re-mounts this same component with standalone={true}. Inline dialog
  // closes itself so only one config surface is visible at a time.
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const handlePopOut = useCallback(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams({ popout: '1' });
    if (currentStrategy?.id) params.set('strategyId', currentStrategy.id);
    const win = window.open(
      `/strategy-builder/backtest-config?${params.toString()}`,
      '_blank',
      'width=1440,height=900,menubar=no,toolbar=no,location=no,status=no',
    );
    if (win && !backTestInProgress) onClose();
  }, [onClose, backTestInProgress, currentStrategy?.id]);

  // Pop In: standalone window only. Closes itself; the opener window keeps
  // showing the strategy-builder page where the user can re-open the dialog.
  const handlePopIn = useCallback(() => {
    if (typeof window === 'undefined') return;
    window.close();
  }, []);

  // Only show Pop In when this standalone window was opened via Pop Out
  // (i.e., has an opener). Direct URL visits get no Pop In target — matches
  // the Strategy Browser pattern.
  const [canPopIn, setCanPopIn] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined' && standalone && window.opener) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCanPopIn(true);
    }
  }, [standalone]);

  if (!open) return null;

  // Drafts auto-persist on Run Test via saveStrategy (BTCAAAAA-34626), so
  // the isPersistedStrategy check is no longer needed. Run Test requires
  // valid dates and an active strategy, but drafts are now runnable.
  const canRun =
    !!currentStrategy &&
    !!config.startDate &&
    !!config.endDate &&
    !backTestInProgress;

  return (
    <FontSizesContext.Provider value={fontSizes}>
    <div
      role="dialog"
      aria-modal={!standalone}
      aria-labelledby="backtest-dialog-title"
      className={standalone ? 'flex items-stretch w-full h-full' : 'fixed inset-y-0 right-0 z-50 flex items-stretch'}
      style={standalone ? undefined : { left: 'var(--sidebar-width, 0px)' }}
      onKeyDown={handleKeyDown}
    >
      {/* Backdrop — drawer-pattern parity with ValidationReportWindow / StrategyBrowserDialog.
          In standalone (popped-out window) mode the dialog already fills the
          viewport, so the backdrop is omitted and the wrapper is a plain block. */}
      {!standalone && (
        <div
          className="absolute inset-0 bg-black/70 cursor-pointer"
          onClick={() => { if (!backTestInProgress) onClose(); }}
        />
      )}

      {/* Drawer box — full-height right-anchored window (inline) or
          viewport-filling window (standalone popout). */}
      <div
        ref={dialogRef}
        className={standalone ? 'relative flex flex-col flex-1' : 'relative flex flex-col flex-1 shadow-2xl'}
        style={{
          border: '1px solid var(--border)',
          background: 'var(--bg-panel)',
        }}
      >
        {/* ── Header ── */}
        {/* Header padding tightened `py-4` → `py-3` (board revision
            2026-06-03) to claw back vertical room for the no-scroll
            Config target. Chrome (AppBrand + sidebar icon + ThemeSelector +
            Pop Out / Pop In) added per BTCAAAAA-34600 to match Strategy
            Browser. */}
        <div
          className="flex items-center justify-between px-6 py-3 flex-shrink-0 gap-3"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          {/* Left cluster — AppBrand prefix + Backtesting sidebar icon + titles */}
          <div className="flex items-center gap-3 min-w-0">
            <AppBrand size={24} />
            <div className="min-w-0">
              <h2
                id="backtest-dialog-title"
                className="text-sm font-semibold uppercase tracking-wide flex items-center gap-2"
                style={{ color: 'var(--text-secondary)' }}
              >
                <BarChart2 size={16} style={{ flexShrink: 0 }} aria-hidden="true" />
                <span className="truncate">Backtest Configuration</span>
              </h2>
              <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                {currentStrategy?.name ? `${currentStrategy.name} Strategy` : 'No strategy loaded'}
              </p>
            </div>
          </div>
          {/* Right cluster — ThemeSelector + Pop Out / Pop In + close.
              ThemeSelector mirrors the toolbar instance from
              StrategyBuilderMainWindow so the popped-out window has the
              same Dark/Ocean control without depending on the parent
              toolbar. Pop Out uses the StrategyBrowserDialog pattern
              (window.open → /strategy-builder/backtest-config). */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <ThemeSelector />
            {/* Tooltip delay — shared singleton with BacktestWindow / strategy builder */}
            <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-faint)' }}>
              <label className="flex items-center gap-1 cursor-pointer select-none" title="Toggle institutional-grade tooltips on all configuration fields">
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
                    title="Tooltip hover delay — lower = tooltips appear faster"
                    style={{ width: 54, accentColor: 'var(--toolbar-accent)', cursor: 'pointer', opacity: 0.75 }}
                  />
                  <span style={{ minWidth: 28, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {(tooltipSettings.delayMs / 1000).toFixed(1)}s
                  </span>
                </>
              )}
            </div>
            <div className="w-px h-4" style={{ background: 'var(--border)' }} />
            {!standalone && (
              <button
                onClick={handlePopOut}
                disabled={backTestInProgress}
                title="Open this dialog in a separate window that can be moved to another monitor"
                className="px-2.5 py-1 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { if (!backTestInProgress) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              >
                ↗ Pop Out
              </button>
            )}
            {canPopIn && (
              <button
                onClick={handlePopIn}
                title="Return this dialog to the main app window"
                className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              >
                ↙ Pop In
              </button>
            )}
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
        </div>

        {/* ── Tab navigation ── */}
        {/* overflow-y-hidden suppresses the hairline vertical scrollbar that
            `overflow-x-auto` was triggering on the tab strip (BTCAAAAA-34540).
            Horizontal auto-scroll is preserved for narrow viewports. */}
        <div
          className="flex flex-shrink-0 overflow-x-auto overflow-y-hidden"
          style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-deep)' }}
        >
          {TABS.map(({ key, label, icon }) => {
            const isActive = activeTab === key;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium whitespace-nowrap transition-colors"
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
        {/* Vertical padding tightened from `py-4` → `py-2` (board revision
            2026-06-03) so the Config tab's 3-column grid fits without
            internal scroll at 1280×720. */}
        <div className="flex-1 overflow-auto px-4 py-1" style={{ background: 'var(--bg-deep)' }}>
          {activeTab === 'config' && (
            <ConfigTab
              config={config}
              onChange={patchConfig}
              disabled={backTestInProgress}
              outputLogs={outputLogs}
              isRunning={backTestInProgress}
              fontScale={fontScale}
              onFontScaleChange={updateFontScale}
              lookbackDays={lookbackDays}
              setLookbackDays={setLookbackDays}
              trainingDays={trainingDays}
              setTrainingDays={setTrainingDays}
              testingDays={testingDays}
              setTestingDays={setTestingDays}
              mode={mode}
              setMode={setMode}
              tpSlConfig={tpSlConfig}
              setTpSlConfig={setTpSlConfig}
              slAdjustment={slAdjustment}
              setSlAdjustment={setSlAdjustment}
              adaptivePreset={adaptivePreset}
              setAdaptivePreset={setAdaptivePreset}
              delayStopLoss={delayStopLoss}
              setDelayStopLoss={setDelayStopLoss}
              marketStructureStop={marketStructureStop}
              setMarketStructureStop={setMarketStructureStop}
              stopLossDelay={stopLossDelay}
              setStopLossDelay={setStopLossDelay}
              emergency={emergency}
              setEmergency={setEmergency}
              volatilityLookback={volatilityLookback}
              setVolatilityLookback={setVolatilityLookback}
              volatilityMultiplier={volatilityMultiplier}
              setVolatilityMultiplier={setVolatilityMultiplier}
              minStopLoss={minStopLoss}
              setMinStopLoss={setMinStopLoss}
              maxStopLoss={maxStopLoss}
              setMaxStopLoss={setMaxStopLoss}
              minRiskReward={minRiskReward}
              setMinRiskReward={setMinRiskReward}
              maxRisk={maxRisk}
              setMaxRisk={setMaxRisk}
              leverage={leverage}
              setLeverage={setLeverage}
              confluence={confluence}
              setConfluence={setConfluence}
              minBarsHeld={minBarsHeld}
              setMinBarsHeld={setMinBarsHeld}
              maxBarsHeld={maxBarsHeld}
              setMaxBarsHeld={setMaxBarsHeld}
            />
          )}
          {activeTab === 'output' && (
            <LiveOutputPanel logs={outputLogs} isRunning={backTestInProgress} result={backTestResult} />
          )}
          {activeTab === 'trades' && (
            <TradesPanel trades={backTestResult?.trades ?? []} />
          )}
          {activeTab === 'metrics' && (
            <MetricsPanel result={backTestResult} />
          )}
          {activeTab === 'ai' && (
            <AiRecommendationsPanel
              result={backTestResult}
              strategy={currentStrategy}
              backtestConfig={{
                startDate: config.startDate,
                endDate: config.endDate,
                initialCapital: config.initialCapital,
                commissionPercentage: config.commissionPercentage,
                slippagePercentage: config.slippagePercentage,
                maxConcurrentPositions: config.maxConcurrentPositions,
                timeframe: config.timeframe,
                mode,
                tpSlConfig,
                slAdjustment,
                adaptivePreset,
                lookbackDays,
                trainingDays,
                testingDays,
              }}
            />
          )}
          {activeTab === 'compare' && (
            <ComparePanel />
          )}
        </div>

        {/* ── Footer: status, progress + run controls ── */}
        {/* Footer padding trimmed `py-4` → `py-2` (cycle-13b 2026-06-03)
            to fit the below-grid Status block at 1280×720. */}
        <div
          className="flex-shrink-0 px-6 py-2"
          style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-panel)' }}
        >
          {/* Candles / Trades / TP-SL counter row — sits at the very bottom
              of the dialog, just above the slim Progress strip and the
              Run Test / Cancel action bar (BTCAAAAA-34589 board revision
              2026-06-04: "right at the bottom"). Scoped to the Config tab
              so the Live Output tab header counter (cycle 11 + 26) isn't
              duplicated. */}
          {activeTab === 'config' && (
            <div className="mb-1">
              <BacktestCountersRow result={backTestResult} align="start" />
            </div>
          )}

          {/* Slim, frameless Progress bar (BTCAAAAA-34190 board revision
              2026-06-03 — replaced the framed meter + Status card so the
              Config form fits without scrolling). The Status checklist and
              TP/SL counters now live in the Live Output tab. */}
          <div className="mb-1">
            <BacktestProgressMeter
              progress={backTestProgress}
              isRunning={backTestInProgress}
              result={backTestResult}
            />
          </div>

          {error && (
            <p className="text-xs mb-3" style={{ color: 'var(--accent-red)' }}>{error}</p>
          )}

          {/* Action bar — thickclient layout: Run Test / Pause / Stop on left, Config Discovery / saved-at / View Live Results on right */}
          <div className="flex items-center justify-between gap-2">
            {/* Left cluster — primary run controls (thickclient leading edge) */}
            <div className="flex items-center gap-2">
              <RichTooltip content={TT_RUN_TEST}>
                {!backTestInProgress ? (
                  <button
                    onClick={handleStart}
                    disabled={!canRun}
                    data-testid="strategy-builder-run-test"
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
                  >
                    <Square size={14} />
                    Running…
                  </button>
                )}
              </RichTooltip>
              <RichTooltip content={TT_PAUSE}>
                <button
                  disabled
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                >
                  <Pause size={14} />
                  Pause
                </button>
              </RichTooltip>
              <RichTooltip content={TT_STOP}>
                <button
                  disabled
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                >
                  <Square size={14} />
                  Stop
                </button>
              </RichTooltip>
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
              <RichTooltip content={TT_CONFIG_DISCOVERY}>
                <button
                  disabled
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
              </RichTooltip>
              <RichTooltip content={TT_VIEW_LIVE_RESULTS}>
                <button
                  disabled={!backTestResult}
                  onClick={() => setActiveTab('trades')}
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: backTestResult ? 'var(--text-secondary)' : 'var(--text-muted)' }}
                >
                  <TrendingUp size={14} />
                  View Live Results
                </button>
              </RichTooltip>
              <RichTooltip content={TT_CANCEL}>
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
              </RichTooltip>
            </div>
          </div>
        </div>
      </div>
    </div>
    </FontSizesContext.Provider>
  );
}
