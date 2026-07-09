// BTCAAAAA-39020: shared helpers for grouping partial-exit trades by base ID
// and computing their aggregate fields. Pure functions, no React — extracted
// from TradesPanel.tsx so the math can be unit-tested without rendering.
//
// BTCAAAAA-39025: group `totalPnlPct` is computed from the entry notional
// (first leg's entry price × parent quantity across all legs) divided by the
// USD P&L sum, NOT by summing per-leg `pnlPercentage` values. The old sum-of-
// pcts approach produced wrong totals whenever a multi-leg trade had mixed
// directions or asymmetric partial sizes (e.g. TP1/TP2/TP3 at 33/33/34%).
//
// BTCAAAAA-39061: groups are ordered by first-seen insertion (outer order),
// but LEGS WITHIN A GROUP are sorted by exitTime ascending so the closing leg
// is reliably `legs[legs.length - 1]`. The engine can emit partial-exit legs
// out of chronological order (e.g. a 100% SL close on a TP1 leg followed by
// later TP legs from the same parent bar), so downstream consumers
// (`groupNotesPreview`, `groupRowSummary.exitPrice`, TotalRow tooltip,
// `sortGroupValue` 'status' branch) all assume the array ends at the
// chronological close. Without this sort, a 100% SL "close" can appear in the
// middle of a TP sequence and confuse the user (the BTC-39061 board report).
// Ties on exitTime fall back to entryTime so two legs that closed on the same
// bar stay in entry order; `Array.prototype.sort` is stable in modern engines
// so any further tie preserves the original emission order.

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
 * Compare two legs for chronological ordering. Primary key is exitTime
 * (chronological close); secondary key is entryTime so two legs that closed
 * on the same bar keep their entry order. `Array.prototype.sort` is stable in
 * V8/SpiderMonkey/JavaScriptCore so any further tie preserves the engine's
 * original emission order — which is what the BTC-39061 fix relies on for
 * downstream consumers that pick `legs[legs.length - 1]` as the closing leg.
 *
 * Defensive: missing timestamps are coerced to '' so they sort first (early
 * in the array), matching the engine's emission order rather than risking
 * an `undefined > '2026-...'` coercion that would push them to the tail.
 */
function compareLegsByCloseTime(a: Trade, b: Trade): number {
  const ae = a.exitTime ?? '';
  const be = b.exitTime ?? '';
  if (ae < be) return -1;
  if (ae > be) return 1;
  const ai = a.entryTime ?? '';
  const bi = b.entryTime ?? '';
  if (ai < bi) return -1;
  if (ai > bi) return 1;
  return 0;
}

/**
 * Group partial-exit trade rows by their parent base ID and compute the
 * aggregate P&L fields. `totalPnlPct` is the USD P&L sum divided by the
 * parent-trade entry notional (BTCAAAAA-39025), so the displayed group
 * percentage matches the actual money-weighted return.
 *
 * Outer group order follows first-seen insertion (preserves the engine's
 * natural trade sequence in the trades table); legs WITHIN each group are
 * sorted by exitTime ascending (BTCAAAAA-39061) so `legs[legs.length - 1]`
 * is reliably the chronological closing leg for downstream consumers
 * (`groupNotesPreview`, `groupRowSummary.exitPrice`, TotalRow tooltip,
 * `sortGroupValue` 'status' branch).
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
    // BTCAAAAA-39061: sort legs within each group by chronological close so
    // `legs[length - 1]` is the real closing leg, not whatever the engine
    // emitted last. The engine can interleave 100% SL closes with later TP
    // partials, which previously made a parent group's "closing leg" point
    // at an earlier partial rather than the actual final exit.
    g.trades.sort(compareLegsByCloseTime);
    const notional = entryNotionalForGroup(g.trades);
    g.totalPnlPct = notional > 0 ? (g.totalPnl / notional) * 100 : 0;
  }

  return order.map(b => map.get(b)!);
}
