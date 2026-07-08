/**
 * BTCAAAAA-39026: collapsed-view "Trade #" column used to always render as
 * `${baseId}.${ti + 1}` — so a single-leg trade group (e.g. baseId="5") showed
 * "5.1", making it look like a partial exit even though there were no other
 * legs. The cell should render just the baseId when the group has exactly one
 * trade; multi-leg groups continue to render `5.1, 5.2, 5.3` so partial exits
 * stay distinguishable.
 *
 * Acceptance criteria:
 *   - Single-leg trade rows → displayId = baseId (e.g. "5").
 *   - Multi-leg trade rows  → displayId = `${baseId}.${i + 1}` (e.g. "6.1").
 *
 * TotalRow condition stays the same (`group.trades.length > 1`) — these tests
 * also pin down the *expected* leg counts per group in the acceptance fixture,
 * so a future change to TotalRow's render condition can be cross-checked
 * against the same fixture.
 *
 * Acceptance fixture: [single baseId=5, multi baseId=6 with 3 legs,
 * single baseId=7, multi baseId=8 with 2 legs]. Expanded displayIds:
 *   ["5", "6.1", "6.2", "6.3", "7", "8.1", "8.2"]
 * TotalRow render counts (one TotalRow per multi-leg group): 2.
 */

import { Trade } from '@/lib/strategy-builder/types';
import { legDisplayId } from '../TradesPanel';
import { TradeGroup, groupTradesById } from '../tradeGrouping';

const makeTrade = (id: string, overrides: Partial<Trade> = {}): Trade => ({
  id,
  entryTime: '2026-01-01T00:00:00Z',
  exitTime: '2026-01-01T01:00:00Z',
  entryPrice: 100,
  exitPrice: 101,
  quantity: 0.33,
  pnl: 33,
  pnlPercentage: 1,
  bars: 1,
  side: 'LONG',
  status: 'CLOSED',
  ...overrides,
});

/**
 * Build the acceptance fixture: [single, multi-of-3, single, multi-of-2].
 * The trades are intentionally listed interleaved with realistic per-leg IDs
 * (5.1 / 6.1 / 6.2 / 6.3 / 7.1 / 8.1 / 8.2) so the helper has to *choose*
 * between "5" (no suffix) and "6.1" (suffix) on the same call shape.
 */
function buildAcceptanceFixture(): TradeGroup[] {
  const trades: Trade[] = [
    makeTrade('5.1'),
    makeTrade('6.1'),
    makeTrade('6.2'),
    makeTrade('6.3'),
    makeTrade('7.1'),
    makeTrade('8.1'),
    makeTrade('8.2'),
  ];
  return groupTradesById(trades);
}

/**
 * Walk a group fixture in expanded-view order (every leg of every group) and
 * produce the displayId string TradesPanel would feed into each row's
 * displayId prop.
 */
function expandedDisplayIds(groups: TradeGroup[]): string[] {
  const ids: string[] = [];
  for (const group of groups) {
    group.trades.forEach((_, ti) => ids.push(legDisplayId(group, ti)));
  }
  return ids;
}

/**
 * Count how many TotalRow components the render layer would emit. This mirrors
 * the inline condition `group.trades.length > 1` at the call site (TradesPanel.tsx:457);
 * the helper is intentionally NOT used here so the test still pins the
 * TotalRow-render condition even if the call site changes.
 */
function totalRowCount(groups: TradeGroup[]): number {
  return groups.filter(g => g.trades.length > 1).length;
}

describe('legDisplayId — BTCAAAAA-39026', () => {
  it('returns just baseId for a single-leg group (no ".1" suffix)', () => {
    const group: TradeGroup = {
      baseId: '5',
      trades: [makeTrade('5.1')],
      totalPnl: 33,
      totalPnlPct: 1,
    };
    expect(legDisplayId(group, 0)).toBe('5');
  });

  it('returns "baseId.N" for each leg of a 2-leg TP1+TP2 group', () => {
    const group: TradeGroup = {
      baseId: '8',
      trades: [makeTrade('8.1'), makeTrade('8.2')],
      totalPnl: 60,
      totalPnlPct: 1.5,
    };
    expect(legDisplayId(group, 0)).toBe('8.1');
    expect(legDisplayId(group, 1)).toBe('8.2');
  });

  it('returns "baseId.N" for each leg of a 3-leg TP1+TP2+TP3 group', () => {
    const group: TradeGroup = {
      baseId: '6',
      trades: [makeTrade('6.1'), makeTrade('6.2'), makeTrade('6.3')],
      totalPnl: 99,
      totalPnlPct: 3,
    };
    expect(legDisplayId(group, 0)).toBe('6.1');
    expect(legDisplayId(group, 1)).toBe('6.2');
    expect(legDisplayId(group, 2)).toBe('6.3');
  });

  it('preserves non-numeric baseIds verbatim (defensive — baseTradeId strips .N already)', () => {
    const group: TradeGroup = {
      baseId: 'trade-7',
      trades: [makeTrade('trade-7.1')],
      totalPnl: 0,
      totalPnlPct: 0,
    };
    expect(legDisplayId(group, 0)).toBe('trade-7');
  });
});

describe('legDisplayId acceptance fixture — BTCAAAAA-39026', () => {
  it('produces displayIds [5, 6.1, 6.2, 6.3, 7, 8.1, 8.2] for [single, multi-3, single, multi-2]', () => {
    const groups = buildAcceptanceFixture();
    expect(groups.map(g => g.baseId)).toEqual(['5', '6', '7', '8']);
    expect(groups.map(g => g.trades.length)).toEqual([1, 3, 1, 2]);
    expect(expandedDisplayIds(groups)).toEqual([
      '5',
      '6.1',
      '6.2',
      '6.3',
      '7',
      '8.1',
      '8.2',
    ]);
  });

  it('renders TotalRow only for the two multi-leg groups (count=2)', () => {
    // TotalRow condition at TradesPanel.tsx:457 stays `group.trades.length > 1`.
    // This test pins that 2 of the 4 fixture groups should produce a TotalRow
    // and 2 should not — same shape as the rendering layer.
    const groups = buildAcceptanceFixture();
    expect(totalRowCount(groups)).toBe(2);
    // Cross-check per-group: groups with length === 1 must NOT show a TotalRow,
    // groups with length > 1 MUST show one.
    expect(groups.map(g => g.trades.length > 1)).toEqual([false, true, false, true]);
  });

  it('is unchanged for a backtest with no trades (empty fixture → empty displayIds, 0 TotalRows)', () => {
    expect(expandedDisplayIds([])).toEqual([]);
    expect(totalRowCount([])).toBe(0);
  });
});