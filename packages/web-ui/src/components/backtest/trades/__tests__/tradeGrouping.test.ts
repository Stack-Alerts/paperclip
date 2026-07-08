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
});
