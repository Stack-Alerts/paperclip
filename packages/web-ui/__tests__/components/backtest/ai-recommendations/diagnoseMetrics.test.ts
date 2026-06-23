import {
  buildDiagnoseRows,
  buildStagedRecsSentence,
  computePerEntryStats,
} from '@/components/backtest/ai-recommendations/diagnoseMetrics';
import type { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';

function tr(pnl: number): Trade {
  return {
    id: `t${pnl}`,
    entryTime: '',
    exitTime: '',
    entryPrice: 0,
    exitPrice: 0,
    quantity: 0,
    pnl,
    pnlPercentage: 0,
    bars: 0,
  };
}

describe('computePerEntryStats', () => {
  it('returns empty stats for empty trades', () => {
    const s = computePerEntryStats([]);
    expect(s.entries).toBe(0);
    expect(s.winRate).toBeNull();
    expect(s.profitFactor).toBeNull();
    expect(s.sharpe).toBeNull();
    expect(s.maxDrawdown).toBeNull();
  });

  it('computes per-trade win rate and profit factor', () => {
    const s = computePerEntryStats([tr(100), tr(-50), tr(75), tr(-25)]);
    expect(s.entries).toBe(4);
    expect(s.wins).toBe(2);
    expect(s.winRate).toBeCloseTo(0.5);
    expect(s.profitFactor).toBeCloseTo(175 / 75);
  });

  it('tracks peak-to-trough max drawdown', () => {
    const s = computePerEntryStats([tr(100), tr(50), tr(-80), tr(-30)]);
    expect(s.maxDrawdown).toBeCloseTo(110);
  });
});

describe('buildDiagnoseRows', () => {
  const result: BacktestResult = {
    id: 'r',
    strategyId: 's',
    runId: 'run',
    status: 'completed',
    startDate: '',
    endDate: '',
    initialCapital: 0,
    finalCapital: 0,
    totalTrades: 4,
    winningTrades: 2,
    losingTrades: 2,
    winRate: 0.5,
    totalReturn: 100,
    returnPercentage: 10,
    maxDrawdown: 0.1,
    sharpeRatio: 1.23,
    sortino_ratio: 0,
    profitFactor: 2.33,
    averageWin: 0,
    averageLoss: 0,
    createdAt: '',
  };

  it('builds 5 metric rows in canonical order', () => {
    const rows = buildDiagnoseRows(result, [tr(100), tr(-50), tr(75), tr(-25)]);
    expect(rows.map((r) => r.key)).toEqual(['pf', 'wr', 'sharpe', 'dd', 'entries']);
  });

  it('flags divergent rows when reported and per-entry differ', () => {
    const rows = buildDiagnoseRows(result, [tr(100)]);
    const entriesRow = rows.find((r) => r.key === 'entries')!;
    expect(entriesRow.divergent).toBe(true);
    expect(entriesRow.reported).toBe('4');
    expect(entriesRow.perEntry).toBe('1');
  });

  it('renders dashes for ratio rows when both inputs are missing', () => {
    const rows = buildDiagnoseRows(null, null);
    for (const row of rows) {
      expect(row.reported).toBe('—');
      expect(row.divergent).toBe(false);
      // Ratio/percent rows have no trades to compute against → dash.
      // The entries row legitimately reports zero in this case.
      if (row.key === 'entries') {
        expect(row.perEntry).toBe('0');
      } else {
        expect(row.perEntry).toBe('—');
      }
    }
  });
});

describe('buildStagedRecsSentence', () => {
  const strategy = {
    id: 's',
    name: 'S',
    status: 'draft',
    strategyType: 'manual',
    blocks: [
      { id: 'b1', type: 'signal', index: 0, data: { ema_window: 50 } },
      { id: 'b2', type: 'risk', index: 1, data: { stop_atr_multiple: 2.0 } },
    ],
    settings: {},
  } as unknown as Strategy;

  it('prompts when there are no staged recs', () => {
    expect(buildStagedRecsSentence([], strategy)).toContain('No staged recommendations');
  });

  it('names a single rec inline', () => {
    const sentence = buildStagedRecsSentence(
      [
        {
          id: 'r1',
          title: 'Widen EMA',
          suggestedParams: [{ key: 'ema_window', value: '100' }],
        },
      ],
      strategy,
    );
    expect(sentence).toContain('Widen EMA');
    expect(sentence).toContain('1 parameter');
    expect(sentence).toContain('1 block');
  });

  it('summarises multiple staged recs with parameter + block counts', () => {
    const sentence = buildStagedRecsSentence(
      [
        { id: 'r1', title: 'A', suggestedParams: [{ key: 'ema_window', value: '100' }] },
        {
          id: 'r2',
          title: 'B',
          suggestedParams: [
            { key: 'stop_atr_multiple', value: '1.5' },
            { key: 'ema_window', value: '120' },
          ],
        },
      ],
      strategy,
    );
    expect(sentence).toContain('2 staged recommendations');
    expect(sentence).toContain('3 parameters');
    expect(sentence).toContain('2 blocks');
  });

  it('falls back gracefully when strategy is null', () => {
    const sentence = buildStagedRecsSentence(
      [{ id: 'r1', title: 'A', suggestedParams: [{ key: 'x', value: '1' }] }],
      null,
    );
    expect(sentence).toContain('1 parameter');
    expect(sentence).not.toContain('block');
  });
});
