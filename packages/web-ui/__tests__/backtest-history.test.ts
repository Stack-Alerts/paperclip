import {
  addRunRecord,
  loadAllRunRecords,
  deleteRunRecord,
  deleteRunRecords,
  clearAllRunRecords,
} from '@/lib/backtest-history';
import type { BacktestRunRecord } from '@/lib/strategy-builder/types';

function makeRecord(runId: string, savedAt: string): BacktestRunRecord {
  return {
    runId,
    strategyId: `strat-${runId}`,
    strategyName: `Strategy ${runId}`,
    savedAt,
    result: { finalCapital: 1000, initialCapital: 1000 } as BacktestRunRecord['result'],
  } as BacktestRunRecord;
}

describe('backtest-history bulk deletion', () => {
  beforeEach(() => {
    localStorage.clear();
    addRunRecord(makeRecord('a', '2026-06-14T10:00:00Z'));
    addRunRecord(makeRecord('b', '2026-06-14T11:00:00Z'));
    addRunRecord(makeRecord('c', '2026-06-14T12:00:00Z'));
  });

  it('deleteRunRecords removes only the listed runs', () => {
    deleteRunRecords(['a', 'c']);
    const ids = loadAllRunRecords().map(r => r.runId);
    expect(ids).toEqual(['b']);
  });

  it('deleteRunRecords ignores unknown ids and is a no-op for an empty list', () => {
    deleteRunRecords([]);
    expect(loadAllRunRecords()).toHaveLength(3);
    deleteRunRecords(['does-not-exist']);
    expect(loadAllRunRecords()).toHaveLength(3);
  });

  it('clearAllRunRecords empties the history', () => {
    clearAllRunRecords();
    expect(loadAllRunRecords()).toEqual([]);
  });

  it('deleteRunRecord still removes a single run', () => {
    deleteRunRecord('b');
    const ids = loadAllRunRecords().map(r => r.runId).sort();
    expect(ids).toEqual(['a', 'c']);
  });
});
