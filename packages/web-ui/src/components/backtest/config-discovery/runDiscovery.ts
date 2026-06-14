'use client';

// Config Discovery runner: loops scenario configs through the existing backtest
// REST API one at a time, records a Compare card per run (so "every single run
// naturally creates a compare card"), reports live progress, and returns the
// ranked DiscoveryScenario[] for ConfigDiscoveryResultsDialog.

import { runBacktest as apiRunBacktest, getBacktestResults as apiGetBacktestResults } from '@/lib/strategy-builder/api';
import { addRunRecord } from '@/lib/backtest-history';
import {
  DEFAULT_PARAMETER_RANGES,
  applyDelta,
  generateSingleAxisScenarios,
  aggregateMetrics,
  buildDiscoveryRows,
  type ParameterRange,
  type AggregatedScenario,
  type ScenarioMetrics,
} from '@/lib/strategy-builder/config-discovery';
import type { DiscoveryScenario } from '@/components/strategy-builder/ConfigDiscoveryResultsDialog';
import type { BacktestConfigFull, BacktestResult } from '@/lib/strategy-builder/types';

export interface DiscoveryProgress {
  current: number; // scenarios completed so far (baseline counts as 0 of total)
  total: number;
  message: string;
}

export interface RunDiscoveryOptions {
  strategyId: string;
  strategyName: string;
  baseConfig: BacktestConfigFull;
  ranges?: ParameterRange[];
  onProgress?: (p: DiscoveryProgress) => void;
  // Live results stream (BTCAAAAA-36309): called after the baseline and after
  // each scenario completes so the results dialog can show every finished test
  // the moment it lands instead of waiting for the whole sweep.
  onRowsUpdate?: (rows: DiscoveryScenario[]) => void;
  // Cancellation signal — checked between scenarios.
  shouldStop?: () => boolean;
}

// Flatten a run's config into the label/value pairs the results-dialog tooltip
// renders (BTCAAAAA-36309: "details of all the configuration in the Run").
function summarizeConfig(c: BacktestConfigFull): Array<[string, string]> {
  const sl = c.adaptiveSL;
  const pairs: Array<[string, string | number | undefined]> = [
    ['Date range', c.startDate && c.endDate ? `${c.startDate} → ${c.endDate}` : undefined],
    ['Timeframe', c.timeframe],
    ['Mode', c.mode],
    ['Initial capital', c.initialCapital != null ? `$${c.initialCapital.toLocaleString()}` : undefined],
    ['TP/SL mode', c.tpslMode],
    ['SL adjustment', c.slAdjustmentMode],
    ['Adaptive SL preset', c.adaptiveSLPreset],
    ['Vol lookback', sl ? `${sl.volatilityLookback} bars` : undefined],
    ['Vol multiplier', sl ? `${sl.volatilityMultiplier}x` : undefined],
    ['Min SL', sl ? `${sl.minSlPct}%` : undefined],
    ['Max SL', sl ? `${sl.maxSlPct}%` : undefined],
    ['Emergency SL', sl ? `${sl.emergencySlPct}%` : undefined],
    ['Delay stop-loss', sl ? (sl.delayEnabled ? `on (${sl.delayBars} bars)` : 'off') : undefined],
    ['Structure SL', sl ? (sl.useStructureSl ? 'on' : 'off') : undefined],
    ['Risk per trade', c.riskPerTradePct != null ? `${c.riskPerTradePct}%` : undefined],
    ['Min risk:reward', c.minRiskRewardRatio != null ? `${c.minRiskRewardRatio}x` : undefined],
    ['Max leverage', c.maxLeverage != null ? `${c.maxLeverage}x` : undefined],
    ['Max bars held', c.maxBarsHeld],
    ['Confluence', c.confluenceThreshold],
  ];
  return pairs
    .filter((p): p is [string, string | number] => p[1] !== undefined && p[1] !== '')
    .map(([k, v]) => [k, String(v)]);
}

const POLL_INTERVAL_MS = 1000;
const POLL_CEILING_MS = 30 * 60_000;

interface BacktestStatus {
  runId: string;
  status: string;
  progress?: number;
  trades?: unknown[];
  metrics?: Record<string, unknown>;
  error?: string | null;
  startedAt?: string;
  completedAt?: string | null;
}

function toResult(runId: string, config: BacktestConfigFull, status: BacktestStatus): BacktestResult {
  const m = status.metrics ?? {};
  const initial = config.initialCapital ?? 10000;
  return {
    id: runId,
    strategyId: config.strategyId,
    runId,
    status: 'completed',
    startDate: config.startDate ?? '',
    endDate: config.endDate ?? '',
    initialCapital: initial,
    finalCapital: initial * (1 + Number(m.returnPercentage ?? 0) / 100),
    totalTrades: Number(m.totalTrades ?? (status.trades as unknown[])?.length ?? 0),
    winningTrades: Number(m.winningTrades ?? 0),
    losingTrades: Number(m.losingTrades ?? 0),
    winRate: Number(m.winRate ?? 0),
    totalReturn: Number(m.returnPercentage ?? 0),
    returnPercentage: Number(m.returnPercentage ?? 0),
    maxDrawdown: Number(m.maxDrawdown ?? 0),
    sharpeRatio: Number(m.sharpeRatio ?? 0),
    sortino_ratio: Number(m.sortinoRatio ?? 0),
    profitFactor: Number(m.profitFactor ?? 0),
    averageWin: Number(m.averageWin ?? 0),
    averageLoss: Number(m.averageLoss ?? 0),
    totalBars: Number(m.totalBars ?? 0),
    trades: (status.trades as BacktestResult['trades']) ?? [],
    createdAt: status.startedAt ?? new Date().toISOString(),
    completedAt: status.completedAt ?? new Date().toISOString(),
  };
}

// Run a single backtest to completion and return the typed result.
async function runOne(config: BacktestConfigFull): Promise<BacktestResult> {
  const startResp = (await apiRunBacktest(config.strategyId, config)) as { runId: string };
  const runId = startResp.runId;
  if (!runId) throw new Error('Config Discovery: backend did not return a runId');

  const deadline = Date.now() + POLL_CEILING_MS;
  for (;;) {
    if (Date.now() > deadline) throw new Error('Config Discovery: scenario timed out after 30 minutes');
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    const status = (await apiGetBacktestResults(config.strategyId, runId)) as BacktestStatus;
    if (status.status === 'error') throw new Error(status.error || 'Config Discovery: scenario failed');
    if (status.status === 'done') return toResult(runId, config, status);
  }
}

function recordCompareCard(
  opts: RunDiscoveryOptions,
  label: string,
  fullConfig: BacktestConfigFull,
  result: BacktestResult,
): void {
  addRunRecord({
    runId: result.runId,
    strategyId: opts.strategyId,
    strategyName: `${opts.strategyName} · ${label}`,
    savedAt: new Date().toISOString(),
    config: {
      startDate: fullConfig.startDate,
      endDate: fullConfig.endDate,
      initialCapital: fullConfig.initialCapital ?? 10000,
      commissionPercentage: fullConfig.commissionPercentage,
      slippagePercentage: fullConfig.slippagePercentage,
      maxConcurrentPositions: fullConfig.maxConcurrentPositions,
      timeframe: fullConfig.timeframe,
    },
    fullConfig,
    result,
  });
}

export async function runDiscovery(opts: RunDiscoveryOptions): Promise<DiscoveryScenario[]> {
  const ranges = opts.ranges ?? DEFAULT_PARAMETER_RANGES;
  const specs = generateSingleAxisScenarios(ranges);
  const total = specs.length;
  const report = (current: number, message: string) =>
    opts.onProgress?.({ current, total, message });

  // Per-scenario config so each finished row can surface its full configuration
  // on hover. Keyed by the row's display `scenario` string built downstream.
  const configByScenario = new Map<string, BacktestConfigFull>();
  const attachConfig = (rows: DiscoveryScenario[]): DiscoveryScenario[] =>
    rows.map(row => {
      const cfg = configByScenario.get(row.scenario);
      return cfg ? { ...row, configDetail: summarizeConfig(cfg) } : row;
    });
  // buildDiscoveryRows labels the baseline row with this exact scenario string.
  const BASELINE_LABEL = '[BASELINE] Current config';
  const emit = (metrics: ScenarioMetrics, aggregated: AggregatedScenario[]) =>
    opts.onRowsUpdate?.(attachConfig(buildDiscoveryRows(metrics, aggregated)));

  // Baseline run (current config) — pinned comparison row + its own compare card.
  report(0, 'Running baseline scenario…');
  const baselineConfig: BacktestConfigFull = { ...opts.baseConfig, strategyId: opts.strategyId };
  const baselineResult = await runOne(baselineConfig);
  recordCompareCard(opts, 'Baseline', baselineConfig, baselineResult);
  const baselineMetrics = aggregateMetrics(baselineResult);
  configByScenario.set(BASELINE_LABEL, baselineConfig);

  const aggregated: AggregatedScenario[] = [];
  // Surface the baseline row immediately so the dialog is never empty.
  emit(baselineMetrics, aggregated);

  for (let i = 0; i < specs.length; i++) {
    if (opts.shouldStop?.()) break;
    const spec = specs[i];
    report(i, `Scenario ${i + 1}/${total}: ${spec.description}`);

    const scenarioConfig: BacktestConfigFull = {
      ...applyDelta(baselineConfig, spec.configDelta),
      strategyId: opts.strategyId,
    };
    const result = await runOne(scenarioConfig);
    // Each scenario run naturally creates a Compare card.
    recordCompareCard(opts, spec.description, scenarioConfig, result);
    configByScenario.set(spec.description, scenarioConfig);
    aggregated.push({ spec, metrics: aggregateMetrics(result) });
    // Push the freshly completed test into the live results list.
    emit(baselineMetrics, aggregated);
  }

  report(total, 'Discovery complete');
  return attachConfig(buildDiscoveryRows(baselineMetrics, aggregated));
}
