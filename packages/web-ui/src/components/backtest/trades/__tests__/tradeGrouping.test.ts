/**
 * BTCAAAAA-39025: group P&L % math must be derived from entry notional, not by
 * summing per-leg percentages. The previous implementation accumulated
 * `t.pnlPercentage` across legs which is wrong for mixed-direction or
 * asymmetric-partial multi-leg trades.
 *
 * Verifies the new aggregate-PnL-% rule with a synthetic 3-leg trade:
 *   leg1: +1% on 33% of $10k notional = +$33
 *   leg2: -2% on 33% of $10k notional = -$66
 *   leg3: +3% on 34% of $10k notional = +$102
 *   sum(USD) = +$69
 *   (sum(USD) / $10,000) * 100 = 0.69% (NOT 2.0% from summing per-leg pcts)
 *
 * The old bug would have reported (1 - 2 + 3) = 2.0% — coincidentally equal
 * to the sum of percentages because the per-leg pcts were computed against
 * the same $10k notional. Asymmetric partial sizes (33/33/34 instead of
 * 33.33/33.33/33.34) break that coincidence and surface the bug.
 */

import { Trade } from '@/lib/strategy-builder/types';
import { groupTradesById, baseTradeId } from '../tradeGrouping';

const makeLeg = (
  id: string,
  entryPrice: number,
  quantity: number,
  pnl: number,
  pnlPercentage: number
): Trade => ({
  id,
  entryTime: '2026-01-01T00:00:00Z',
  exitTime: '2026-01-01T01:00:00Z',
  entryPrice,
  exitPrice: entryPrice * (1 + pnlPercentage / 100),
  quantity,
  pnl,
  pnlPercentage,
  bars: 1,
  side: 'LONG',
  status: 'closed',
});

/**
 * BTCAAAAA-39061: like makeLeg but takes an overrides object so each test
 * can pin distinct entryTime / exitTime / status values. The engine can
 * emit partial-exit legs out of chronological order, so the within-group
 * sort tests need to vary timestamps per leg.
 */
const makeTimedLeg = (overrides: {
  id: string;
  entryTime?: string;
  exitTime?: string;
  entryPrice?: number;
  exitPrice?: number;
  quantity?: number;
  pnl?: number;
  pnlPercentage?: number;
  bars?: number;
  side?: 'LONG' | 'SHORT' | string;
  status?: string;
}): Trade => ({
  id: overrides.id,
  entryTime: overrides.entryTime ?? '2026-01-01T00:00:00Z',
  exitTime: overrides.exitTime ?? '2026-01-01T01:00:00Z',
  entryPrice: overrides.entryPrice ?? 100,
  exitPrice: overrides.exitPrice ?? 100,
  quantity: overrides.quantity ?? 0.33,
  pnl: overrides.pnl ?? 0,
  pnlPercentage: overrides.pnlPercentage ?? 0,
  bars: overrides.bars ?? 1,
  side: overrides.side ?? 'LONG',
  status: overrides.status ?? 'CLOSED',
});

describe('tradeGrouping — BTCAAAAA-39025', () => {
  describe('baseTradeId', () => {
    it('strips numeric / decimal / underscore suffixes so child leg IDs collapse to the parent base', () => {
      expect(baseTradeId('abc')).toBe('abc');
      expect(baseTradeId('abc.1')).toBe('abc');
      expect(baseTradeId('abc_2')).toBe('abc');
      expect(baseTradeId('trade-7.3')).toBe('trade-7');
      expect(baseTradeId('parent-1.2.3')).toBe('parent-1.2');
    });

    it('coerces non-string IDs to string before stripping', () => {
      expect(baseTradeId(123)).toBe('123');
      expect(baseTradeId(null)).toBe('');
    });
  });

  describe('groupTradesById — totalPnlPct math', () => {
    it('mixed-direction 3-leg trade on $10k notional reports 0.69%, NOT the sum of per-leg pcts', () => {
      // 33/33/34 split so the sum-of-pcts and the notional-derived result diverge
      const leg1 = makeLeg('t.1', 100, 33, 33, 1);
      const leg2 = makeLeg('t.2', 100, 33, -66, -2);
      const leg3 = makeLeg('t.3', 100, 34, 102, 3);

      const groups = groupTradesById([leg1, leg2, leg3]);
      expect(groups).toHaveLength(1);

      const g = groups[0];
      expect(g.baseId).toBe('t');
      expect(g.trades).toHaveLength(3);
      // USD P&L: 33 - 66 + 102 = 69
      expect(g.totalPnl).toBeCloseTo(69, 5);
      // entryNotional: first leg entryPrice (100) * totalQty (33+33+34=100) = 10,000
      // (g.totalPnl / entryNotional) * 100 = 0.69
      expect(g.totalPnlPct).toBeCloseTo(0.69, 5);
      // The bug would have produced: 1 + (-2) + 3 = 2.0
      expect(g.totalPnlPct).not.toBeCloseTo(2.0, 1);
    });

    it('single-leg trade: aggregate equals the leg pnlPercentage', () => {
      const leg = makeLeg('solo', 50, 2, 4, 4);
      const groups = groupTradesById([leg]);
      expect(groups[0].totalPnl).toBe(4);
      // notional = 50 * 2 = 100; (4 / 100) * 100 = 4%
      expect(groups[0].totalPnlPct).toBeCloseTo(4, 5);
    });

    it('all-positive 3-leg trade: matches USD sum over notional', () => {
      const legs = [
        makeLeg('x.1', 200, 10, 20, 1),
        makeLeg('x.2', 200, 10, 40, 2),
        makeLeg('x.3', 200, 10, 60, 3),
      ];
      const groups = groupTradesById(legs);
      // notional = 200 * 30 = 6000; sum = 120; pct = 2.0
      expect(groups[0].totalPnl).toBeCloseTo(120, 5);
      expect(groups[0].totalPnlPct).toBeCloseTo(2.0, 5);
    });

    it('loss single-leg: negative PnL propagates as negative pct', () => {
      const leg = makeLeg('loser', 100, 5, -25, -5);
      const groups = groupTradesById([leg]);
      // notional = 100 * 5 = 500; -25/500 = -5%
      expect(groups[0].totalPnl).toBe(-25);
      expect(groups[0].totalPnlPct).toBeCloseTo(-5, 5);
    });

    it('zero notional (entry price 0 or quantity 0) returns 0% rather than NaN/Inf', () => {
      const leg: Trade = {
        ...makeLeg('zero.1', 0, 0, 0, 0),
        entryPrice: 0,
        quantity: 0,
      };
      const groups = groupTradesById([leg]);
      expect(groups[0].totalPnl).toBe(0);
      expect(groups[0].totalPnlPct).toBe(0);
    });

    it('groups by base ID and preserves first-seen insertion order', () => {
      const a1 = makeLeg('a.1', 10, 1, 1, 10);
      const b1 = makeLeg('b.1', 10, 1, 2, 20);
      const a2 = makeLeg('a.2', 10, 1, 3, 30);
      const c1 = makeLeg('c.1', 10, 1, 4, 40);

      const groups = groupTradesById([a1, b1, a2, c1]);
      expect(groups.map(g => g.baseId)).toEqual(['a', 'b', 'c']);
      // 'a' has both legs collapsed
      const aGroup = groups[0];
      expect(aGroup.trades).toHaveLength(2);
      // notional = 10 * (1 + 1) = 20; sum = 4; pct = 20
      expect(aGroup.totalPnl).toBeCloseTo(4, 5);
      expect(aGroup.totalPnlPct).toBeCloseTo(20, 5);
    });
  });

  /**
   * BTCAAAAA-39061: the engine can emit partial-exit legs for the same parent
   * out of chronological order (e.g. a 100% SL close on a TP1 leg followed by
   * later TP partials from the same parent bar). The local-board report was
   * "trade 2.1 has 100% stop loss close but then it has partials and other
   * closes" — confusing because a 100% SL should be the final exit. The fix
   * sorts legs within each group by exitTime ascending so downstream helpers
   * that pick `legs[legs.length - 1]` as the chronological close
   * (`groupNotesPreview`, `groupRowSummary.exitPrice`, TotalRow tooltip,
   * `sortGroupValue` 'status' branch) reliably get the real closing leg.
   * Outer group order (first-seen insertion) is preserved.
   */
  describe('groupTradesById — within-group chronological sort (BTCAAAAA-39061)', () => {
    it('sorts legs within a group by exitTime ascending so the last leg is the chronological close', () => {
      // Engine emits: 2.1 at 02:00, 2.3 at 03:00, 2.2 at 04:00 (out of order)
      const leg1 = makeTimedLeg({ id: '2.1', entryTime: '2026-02-01T00:00:00Z', exitTime: '2026-02-01T02:00:00Z' });
      const leg2 = makeTimedLeg({ id: '2.3', entryTime: '2026-02-01T00:00:00Z', exitTime: '2026-02-01T03:00:00Z' });
      const leg3 = makeTimedLeg({ id: '2.2', entryTime: '2026-02-01T00:00:00Z', exitTime: '2026-02-01T04:00:00Z' });
      const groups = groupTradesById([leg1, leg2, leg3]);
      expect(groups).toHaveLength(1);
      expect(groups[0].trades.map(t => t.id)).toEqual(['2.1', '2.3', '2.2']);
    });

    it('places a late 100% SL close at the END when the engine emits it FIRST (BTC-39061 reproducer)', () => {
      // Engine emits the 100% SL close first (e.g. on the parent bar's SL trigger)
      // then emits earlier TP partials from the same parent — the 100% SL is
      // chronologically LAST (latest exitTime), so the sort places it LAST and
      // the partials (which exited earlier) come first. This matches the
      // local-board report where trade 2.1 (100% SL) was followed by 2.2-2.6
      // (TP partials) on screen; the SL is the real closing leg.
      const sl = makeTimedLeg({
        id: '2.1', entryTime: '2026-02-01T14:00:00Z', exitTime: '2026-02-01T22:00:00Z',
        pnl: -100, pnlPercentage: -100,
      });
      const tp1 = makeTimedLeg({
        id: '2.2', entryTime: '2026-02-01T14:00:00Z', exitTime: '2026-02-01T16:00:00Z',
        pnl: 50, pnlPercentage: 50,
      });
      const tp2 = makeTimedLeg({
        id: '2.3', entryTime: '2026-02-01T14:00:00Z', exitTime: '2026-02-01T18:00:00Z',
        pnl: 60, pnlPercentage: 60,
      });
      const tp3 = makeTimedLeg({
        id: '2.4', entryTime: '2026-02-01T14:00:00Z', exitTime: '2026-02-01T20:00:00Z',
        pnl: 70, pnlPercentage: 70,
      });
      const groups = groupTradesById([sl, tp1, tp2, tp3]);
      expect(groups).toHaveLength(1);
      // After sort: TPs in chronological order, then the 100% SL as the last/closing leg
      expect(groups[0].trades.map(t => t.id)).toEqual(['2.2', '2.3', '2.4', '2.1']);
    });

    it('does NOT reorder the OUTER group sequence (first-seen insertion preserved across groups)', () => {
      // Outer emission order is a, b, a, c — groups must come out as [a, b, c].
      // Within group 'a', legs are sorted by exitTime: a.2 (01:00) before a.1 (05:00).
      const a1 = makeTimedLeg({ id: 'a.1', exitTime: '2026-02-01T05:00:00Z' });
      const b1 = makeTimedLeg({ id: 'b.1', exitTime: '2026-02-01T01:00:00Z' });
      const a2 = makeTimedLeg({ id: 'a.2', exitTime: '2026-02-01T03:00:00Z' });
      const c1 = makeTimedLeg({ id: 'c.1', exitTime: '2026-02-01T10:00:00Z' });
      const groups = groupTradesById([a1, b1, a2, c1]);
      expect(groups.map(g => g.baseId)).toEqual(['a', 'b', 'c']);
      // Within 'a': a.2 (03:00) < a.1 (05:00) — sorted chronologically
      expect(groups[0].trades.map(t => t.id)).toEqual(['a.2', 'a.1']);
    });

    it('falls back to entryTime when two legs share the same exitTime (same-bar partials)', () => {
      // x.1 enters first (00:00) and x.2 enters second (00:30); both close at 05:00.
      // Tie-breaker: entryTime ascending preserves the within-bar entry order.
      const leg1 = makeTimedLeg({
        id: 'x.1', entryTime: '2026-02-01T00:00:00Z', exitTime: '2026-02-01T05:00:00Z',
      });
      const leg2 = makeTimedLeg({
        id: 'x.2', entryTime: '2026-02-01T00:30:00Z', exitTime: '2026-02-01T05:00:00Z',
      });
      const groups = groupTradesById([leg1, leg2]);
      expect(groups[0].trades.map(t => t.id)).toEqual(['x.1', 'x.2']);
    });

    it('preserves single-leg groups unchanged (sort is a no-op on arrays of length 1)', () => {
      const leg = makeTimedLeg({ id: 'solo', exitTime: '2026-02-01T05:00:00Z' });
      const groups = groupTradesById([leg]);
      expect(groups[0].trades.map(t => t.id)).toEqual(['solo']);
    });

    it('handles an empty input array defensively', () => {
      expect(groupTradesById([])).toEqual([]);
    });
  });
});
