import {
  DEFAULT_PARAMETER_RANGES,
  rangeValues,
  setNested,
  applyDelta,
  generateSingleAxisScenarios,
  aggregateMetrics,
  buildDiscoveryRows,
  type ParameterRange,
  type AggregatedScenario,
} from '../config-discovery';
import type { BacktestConfigFull, BacktestResult, Trade } from '../types';

function baseConfig(): BacktestConfigFull {
  return {
    strategyId: 's1',
    startDate: '2026-01-01',
    endDate: '2026-02-01',
    initialCapital: 10000,
    mode: 'historical',
    tpslMode: 'Fibonacci',
    slAdjustmentMode: 'static',
    adaptiveSLPreset: 'default',
    adaptiveSL: {
      enabled: true,
      delayEnabled: false,
      delayBars: 0,
      emergencySlPct: 5,
      volatilityLookback: 14,
      volatilityMultiplier: 1.0,
      minSlPct: 0.5,
      maxSlPct: 2.0,
      useStructureSl: false,
    },
    riskPerTradePct: 1,
    minRiskRewardRatio: 1.5,
    maxBarsHeld: 100,
  };
}

function result(trades: Partial<Trade>[], summary: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: 'r',
    strategyId: 's1',
    runId: 'run',
    status: 'completed',
    startDate: '2026-01-01',
    endDate: '2026-02-01',
    initialCapital: 10000,
    finalCapital: 11000,
    totalTrades: trades.length,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalReturn: 0,
    returnPercentage: 0,
    maxDrawdown: 0,
    sharpeRatio: 0,
    sortino_ratio: 0,
    profitFactor: 0,
    averageWin: 0,
    averageLoss: 0,
    createdAt: '2026-01-01',
    trades: trades as Trade[],
    ...summary,
  };
}

describe('rangeValues', () => {
  it('linspaces min/max across steps inclusive of endpoints', () => {
    expect(rangeValues({ key: 'k', label: 'L', minVal: 10, maxVal: 30, steps: 3, fmt: String })).toEqual([10, 20, 30]);
  });

  it('returns explicit values verbatim', () => {
    expect(rangeValues({ key: 'k', label: 'L', values: ['A', 'B'], fmt: String })).toEqual(['A', 'B']);
  });

  it('collapses to single value when steps < 2', () => {
    expect(rangeValues({ key: 'k', label: 'L', minVal: 5, maxVal: 9, steps: 1, fmt: String })).toEqual([5]);
  });
});

describe('setNested / applyDelta', () => {
  it('sets a nested key without mutating the source', () => {
    const cfg = baseConfig();
    const next = setNested(cfg, 'adaptiveSL.volatilityLookback', 22);
    expect(next.adaptiveSL.volatilityLookback).toBe(22);
    expect(cfg.adaptiveSL.volatilityLookback).toBe(14);
  });

  it('sets a top-level key', () => {
    const next = setNested(baseConfig(), 'maxBarsHeld', 200);
    expect(next.maxBarsHeld).toBe(200);
  });

  it('applies a multi-key delta', () => {
    const next = applyDelta(baseConfig(), { tpslMode: 'Hybrid', 'adaptiveSL.minSlPct': 0.8 });
    expect(next.tpslMode).toBe('Hybrid');
    expect(next.adaptiveSL.minSlPct).toBe(0.8);
  });
});

describe('generateSingleAxisScenarios', () => {
  it('produces one scenario per axis value with a single-key delta', () => {
    const scenarios = generateSingleAxisScenarios(DEFAULT_PARAMETER_RANGES);
    // 3 + 3 + 3 + 3 + 3 + 3 = 18 across the six default axes.
    expect(scenarios).toHaveLength(18);
    for (const s of scenarios) {
      expect(Object.keys(s.configDelta)).toHaveLength(1);
      expect(s.paramLabels).toHaveLength(1);
    }
    expect(scenarios[0].scenarioId).toBe('DISC_0001');
    expect(scenarios[0].description).toBe('Vol Lookback=10 bars');
  });
});

describe('aggregateMetrics', () => {
  it('aggregates per-trade pnl, win rate, exits, and drawdown', () => {
    const m = aggregateMetrics(
      result([
        { pnl: 100, bars: 10, exitType: 'TP1' },
        { pnl: -50, bars: 5, exitType: 'SL', notes: 'Stop Loss Hit' },
        { pnl: 200, bars: 20, exitType: 'TP3' },
        { pnl: 0, bars: 100, exitType: 'TIME', notes: 'Max bars held' },
      ]),
    );
    expect(m.trades).toBe(4);
    expect(m.totalPnl).toBe(250);
    expect(m.winRate).toBe(50); // 2 of 4 positive
    expect(m.tp1).toBe(1);
    expect(m.tp3).toBe(1);
    expect(m.sl).toBe(1);
    expect(m.time).toBe(1);
    expect(m.avgBars).toBeCloseTo(33.75);
    // Peak 100 -> dip to 50 (dd 50) -> 250; max drawdown is 50.
    expect(m.maxDd).toBe(50);
    expect(Number.isFinite(m.sharpe)).toBe(true);
  });

  it('falls back to summary metrics when no trades are present', () => {
    const m = aggregateMetrics(
      result([], { totalTrades: 7, winRate: 42, totalReturn: 900, sharpeRatio: 1.3, maxDrawdown: 120 }),
    );
    expect(m.trades).toBe(7);
    expect(m.winRate).toBe(42);
    expect(m.totalPnl).toBe(900);
    expect(m.avgPnl).toBeCloseTo(900 / 7);
    expect(m.sharpe).toBe(1.3);
    expect(m.maxDd).toBe(120);
  });
});

describe('buildDiscoveryRows', () => {
  const mk = (totalPnl: number, scenarioId: string): AggregatedScenario => ({
    spec: { scenarioId, description: scenarioId, configDelta: {}, paramLabels: [] },
    metrics: aggregateMetrics(result([{ pnl: totalPnl, bars: 1, exitType: 'TP1' }])),
  });

  it('pins baseline first and ranks discovery rows by total PnL desc with medals', () => {
    const baseline = aggregateMetrics(result([{ pnl: 10, bars: 1, exitType: 'TP1' }]));
    const rows = buildDiscoveryRows(baseline, [mk(50, 'A'), mk(300, 'B'), mk(150, 'C'), mk(20, 'D')]);

    expect(rows[0].type).toBe('baseline');
    expect(rows[0].badge).toBe('baseline');

    const discovery = rows.slice(1);
    expect(discovery.map(r => r.scenario)).toEqual(['B', 'C', 'A', 'D']);
    expect(discovery.map(r => r.badge)).toEqual(['gold', 'silver', 'bronze', '']);
    expect(discovery.map(r => r.rank)).toEqual([1, 2, 3, 4]);
  });

  it('omits the baseline row when no baseline is supplied', () => {
    const rows = buildDiscoveryRows(null, [mk(50, 'A')]);
    expect(rows).toHaveLength(1);
    expect(rows[0].type).toBe('discovery');
  });
});

describe('DEFAULT_PARAMETER_RANGES', () => {
  it('targets real BacktestConfigFull paths', () => {
    const keys = DEFAULT_PARAMETER_RANGES.map((r: ParameterRange) => r.key);
    expect(keys).toContain('adaptiveSL.volatilityLookback');
    expect(keys).toContain('tpslMode');
    expect(keys).toContain('maxBarsHeld');
  });
});
