// Config Discovery engine (thick-client port of src/strategy_builder/ui/config_permutation_engine.py).
//
// Pure, framework-free functions: permutation generation, delta application over
// BacktestConfigFull, per-scenario metric aggregation from raw trades, and
// ranking/badging into the DiscoveryScenario shape consumed by
// ConfigDiscoveryResultsDialog. The async runner that loops the backtest API
// lives in components/backtest/config-discovery/runDiscovery.ts.

import type { BacktestConfigFull, BacktestResult, Trade } from './types';
import type { DiscoveryScenario } from '@/components/strategy-builder/ConfigDiscoveryResultsDialog';

export interface ParameterRange {
  // Dot-notation path into BacktestConfigFull, e.g. 'adaptiveSL.volatilityLookback'.
  key: string;
  label: string;
  // Explicit value list; when omitted, linspace(minVal, maxVal, steps) is used.
  values?: Array<number | string>;
  minVal?: number;
  maxVal?: number;
  steps?: number;
  fmt: (v: number | string) => string;
}

export interface DiscoveryScenarioSpec {
  scenarioId: string;
  description: string;
  // Dot-notation overrides applied on top of the base config.
  configDelta: Record<string, number | string>;
  paramLabels: Array<[string, string]>;
}

export interface ScenarioMetrics {
  trades: number;
  winRate: number; // 0-100
  totalPnl: number;
  avgPnl: number;
  sharpe: number;
  tp1: number;
  tp2: number;
  tp3: number;
  sl: number;
  time: number;
  avgBars: number;
  maxDd: number;
}

export const DEFAULT_PARAMETER_RANGES: ParameterRange[] = [
  {
    key: 'adaptiveSL.volatilityLookback',
    label: 'Vol Lookback',
    minVal: 10,
    maxVal: 30,
    steps: 3,
    fmt: v => `${Number(v).toFixed(0)} bars`,
  },
  {
    key: 'adaptiveSL.volatilityMultiplier',
    label: 'Vol Multiplier',
    minVal: 0.8,
    maxVal: 1.8,
    steps: 3,
    fmt: v => `${Number(v).toFixed(1)}x`,
  },
  {
    key: 'adaptiveSL.minSlPct',
    label: 'Min SL %',
    minVal: 0.5,
    maxVal: 1.2,
    steps: 3,
    fmt: v => `${Number(v).toFixed(1)}%`,
  },
  {
    key: 'adaptiveSL.maxSlPct',
    label: 'Max SL %',
    minVal: 1.5,
    maxVal: 3.0,
    steps: 3,
    fmt: v => `${Number(v).toFixed(1)}%`,
  },
  {
    key: 'tpslMode',
    label: 'TP/SL Mode',
    values: ['Fibonacci', 'Hybrid', 'Fixed'],
    fmt: v => String(v),
  },
  {
    key: 'maxBarsHeld',
    label: 'Max Bars',
    values: [50, 100, 200],
    fmt: v => `${Number(v).toFixed(0)}`,
  },
];

export function rangeValues(range: ParameterRange): Array<number | string> {
  if (range.values !== undefined) return [...range.values];
  if (range.minVal === undefined || range.maxVal === undefined) {
    throw new Error(`ParameterRange '${range.key}': must supply either values or minVal+maxVal`);
  }
  const steps = range.steps ?? 5;
  if (steps < 2) return [range.minVal];
  const step = (range.maxVal - range.minVal) / (steps - 1);
  return Array.from({ length: steps }, (_, i) =>
    Number((range.minVal! + step * i).toFixed(6)),
  );
}

// Deep-clone obj and set a dot-notation key. Intermediate non-objects are replaced.
export function setNested<T>(obj: T, key: string, value: number | string): T {
  // BacktestConfigFull is plain JSON (no Dates/functions), so a JSON clone is
  // safe and avoids relying on structuredClone (absent in the jsdom test env).
  const result = JSON.parse(JSON.stringify(obj)) as Record<string, unknown>;
  const parts = key.split('.');
  let target = result;
  for (const part of parts.slice(0, -1)) {
    if (typeof target[part] !== 'object' || target[part] === null) {
      target[part] = {};
    }
    target = target[part] as Record<string, unknown>;
  }
  target[parts[parts.length - 1]] = value;
  return result as T;
}

export function applyDelta(
  base: BacktestConfigFull,
  delta: Record<string, number | string>,
): BacktestConfigFull {
  let merged = base;
  for (const [key, value] of Object.entries(delta)) {
    merged = setNested(merged, key, value);
  }
  return merged;
}

// One-at-a-time sweep: each axis varied independently, all others held at base.
export function generateSingleAxisScenarios(ranges: ParameterRange[]): DiscoveryScenarioSpec[] {
  const scenarios: DiscoveryScenarioSpec[] = [];
  let idx = 1;
  for (const range of ranges) {
    for (const val of rangeValues(range)) {
      const formatted = range.fmt(val);
      scenarios.push({
        scenarioId: `DISC_${String(idx).padStart(4, '0')}`,
        description: `${range.label}=${formatted}`,
        configDelta: { [range.key]: val },
        paramLabels: [[range.label, formatted]],
      });
      idx += 1;
    }
  }
  return scenarios;
}

function classifyExit(t: Trade): keyof Pick<ScenarioMetrics, 'tp1' | 'tp2' | 'tp3' | 'sl' | 'time'> | null {
  const ec = (t.exitType ?? '').toUpperCase();
  const notes = (t.notes ?? '').toUpperCase();
  const hay = `${ec} ${notes}`;
  if (hay.includes('TP1')) return 'tp1';
  if (hay.includes('TP2')) return 'tp2';
  if (hay.includes('TP3')) return 'tp3';
  if (ec === 'SL' || hay.includes('STOP')) return 'sl';
  if (hay.includes('TIME') || hay.includes('MAX BAR') || hay.includes('MAX_BAR')) return 'time';
  return null;
}

// Aggregate a completed backtest into the discovery metric row. Prefers raw
// per-trade data (matching the desktop aggregation) and falls back to the
// result-level summary fields when trades are absent.
export function aggregateMetrics(result: BacktestResult): ScenarioMetrics {
  const metrics: ScenarioMetrics = {
    trades: 0,
    winRate: 0,
    totalPnl: 0,
    avgPnl: 0,
    sharpe: 0,
    tp1: 0,
    tp2: 0,
    tp3: 0,
    sl: 0,
    time: 0,
    avgBars: 0,
    maxDd: 0,
  };

  const trades = result.trades ?? [];
  if (trades.length === 0) {
    // Fall back to summary metrics from the backtest result.
    metrics.trades = result.totalTrades ?? 0;
    metrics.winRate = result.winRate ?? 0;
    metrics.totalPnl = result.totalReturn ?? 0;
    metrics.avgPnl = metrics.trades > 0 ? metrics.totalPnl / metrics.trades : 0;
    metrics.sharpe = result.sharpeRatio ?? 0;
    metrics.maxDd = result.maxDrawdown ?? 0;
    return metrics;
  }

  const pnls = trades.map(t => t.pnl ?? 0);
  const bars = trades.map(t => t.bars ?? 0);
  metrics.trades = trades.length;
  metrics.totalPnl = pnls.reduce((a, b) => a + b, 0);
  metrics.winRate = (pnls.filter(p => p > 0).length / trades.length) * 100;
  metrics.avgPnl = metrics.totalPnl / trades.length;
  metrics.avgBars = bars.reduce((a, b) => a + b, 0) / bars.length;

  if (trades.length > 1) {
    const mean = metrics.avgPnl;
    const variance =
      pnls.reduce((acc, p) => acc + (p - mean) ** 2, 0) / (trades.length - 1);
    const std = variance > 0 ? Math.sqrt(variance) : 0;
    metrics.sharpe = std > 0 ? (mean / std) * Math.sqrt(trades.length) : 0;
  }

  for (const t of trades) {
    const bucket = classifyExit(t);
    if (bucket) metrics[bucket] += 1;
  }

  let peak = 0;
  let cum = 0;
  let maxDd = 0;
  for (const p of pnls) {
    cum += p;
    if (cum > peak) peak = cum;
    const dd = peak - cum;
    if (dd > maxDd) maxDd = dd;
  }
  metrics.maxDd = maxDd;

  return metrics;
}

export interface AggregatedScenario {
  spec: DiscoveryScenarioSpec;
  metrics: ScenarioMetrics;
}

// Build the ranked DiscoveryScenario[] for the results dialog. The baseline row
// (current config) is pinned first; discovery rows are ranked by total PnL
// descending with gold/silver/bronze badges for the top three.
export function buildDiscoveryRows(
  baseline: ScenarioMetrics | null,
  scenarios: AggregatedScenario[],
): DiscoveryScenario[] {
  const rows: DiscoveryScenario[] = [];

  if (baseline) {
    rows.push({
      ...metricsToRow(baseline),
      rank: 0,
      badge: 'baseline',
      scenario: '[BASELINE] Current config',
      type: 'baseline',
    });
  }

  const ranked = [...scenarios].sort((a, b) => b.metrics.totalPnl - a.metrics.totalPnl);
  const badges: Array<DiscoveryScenario['badge']> = ['gold', 'silver', 'bronze'];
  ranked.forEach(({ spec, metrics }, i) => {
    rows.push({
      ...metricsToRow(metrics),
      rank: i + 1,
      badge: i < 3 ? badges[i] : '',
      scenario: spec.description,
      type: 'discovery',
    });
  });

  return rows;
}

function metricsToRow(m: ScenarioMetrics): Omit<DiscoveryScenario, 'rank' | 'badge' | 'scenario' | 'type'> {
  return {
    trades: m.trades,
    winRate: m.winRate,
    totalPnl: m.totalPnl,
    avgPnl: m.avgPnl,
    sharpe: m.sharpe,
    tp1: m.tp1,
    tp2: m.tp2,
    tp3: m.tp3,
    sl: m.sl,
    time: m.time,
    avgBars: m.avgBars,
    maxDd: m.maxDd,
  };
}
