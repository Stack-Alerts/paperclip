// BTCAAAAA-39020: shared helpers for grouping partial-exit trades by base ID
// and computing their aggregate fields. Pure functions, no React — extracted
// from TradesPanel.tsx so the math can be unit-tested without rendering.
//
// BTCAAAAA-39025: group `totalPnlPct` is computed from the entry notional
// (first leg's entry price × parent quantity across all legs) divided by the
// USD P&L sum, NOT by summing per-leg `pnlPercentage` values. The old sum-of-
// pcts approach produced wrong totals whenever a multi-leg trade had mixed
// directions or asymmetric partial sizes (e.g. TP1/TP2/TP3 at 33/33/34%).

import { Trade } from '@/lib/strategy-builder/types';

/**
 * Strip a trailing numeric suffix (with optional `.` or `_` separator) from a
 * trade id so child leg rows of a multi-leg parent collapse to the same base.
 *
 * Examples:
 *   'abc.1'    -> 'abc'
 *   'abc_2'    -> 'abc'
 *   'trade-7.3'-> 'trade-7'
 */
export function baseTradeId(id: string | number | null | undefined): string {
  if (id === null || id === undefined) return '';
  return String(id).replace(/[._]\d+$/, '');
}

export interface TradeGroup {
  baseId: string;
  trades: Trade[];
  totalPnl: number;
  totalPnlPct: number;
}

/**
 * Derive the parent-trade notional for a group. The engine emits each partial-
 * exit leg with `quantity` = the partial-exit size, so summing the leg
 * quantities gives the parent position size (the gross capital committed to
 * the trade). The first leg's `entryPrice` is the parent entry price (every
 * leg of the same parent shares the same entry).
 *
 * Defensive guards:
 *  - empty group → 0
 *  - non-positive entry price → 0 (avoids division-by-zero / sign flip)
 */
function entryNotionalForGroup(trades: Trade[]): number {
  if (trades.length === 0) return 0;
  const first = trades[0];
  const entryPrice = first?.entryPrice ?? 0;
  if (entryPrice <= 0) return 0;

  const totalQty = trades.reduce((s, t) => s + (t.quantity ?? 0), 0);
  return entryPrice * totalQty;
}

/**
 * Group partial-exit trade rows by their parent base ID and compute the
 * aggregate P&L fields. `totalPnlPct` is the USD P&L sum divided by the
 * parent-trade entry notional (BTCAAAAA-39025), so the displayed group
 * percentage matches the actual money-weighted return.
 */
export function groupTradesById(raw: Trade[]): TradeGroup[] {
  const map = new Map<string, TradeGroup>();
  const order: string[] = [];

  for (const t of raw) {
    const b = baseTradeId(t.id);
    let g = map.get(b);
    if (!g) {
      g = { baseId: b, trades: [], totalPnl: 0, totalPnlPct: 0 };
      map.set(b, g);
      order.push(b);
    }
    g.trades.push(t);
    g.totalPnl += t.pnl ?? 0;
  }

  for (const b of order) {
    const g = map.get(b)!;
    const notional = entryNotionalForGroup(g.trades);
    g.totalPnlPct = notional > 0 ? (g.totalPnl / notional) * 100 : 0;
  }

  return order.map(b => map.get(b)!);
}
