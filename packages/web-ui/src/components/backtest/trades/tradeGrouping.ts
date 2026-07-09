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
//
// BTCAAAAA-39063: the engine's per-trade counter is global, NOT per-position,
// so a fresh position opened weeks later can be emitted with the same base ID
// as an earlier position that has already closed (e.g. "2", "2.1", "2.2" for
// the 12/07 single-leg trade, then "2.1", "2.2" for the 03/21 two-leg chain,
// then "2.1", "2.2", "2.3" for the 05/26 three-leg chain). `baseTradeId`
// strips ANY trailing `.N` suffix, so without a defensive check these three
// distinct positions collapse into one "Trade 2" parent whose P&L aggregates
// are nonsense and whose leg ordering mixes unrelated exits (the local-board
// screenshot showed leg 2.3 displaying "SL 67%" because the 03/21 67% SL
// close and the 05/26 TP legs all shared the same parent). The fix groups by
// a COMPOSITE key (engineBaseId, entryTime, entryPrice) — the same position
// shares all three, but unrelated positions differ on at least entryTime.
// After all trades are bucketed, we detect engine-base collisions: if the
// engine base "2" produced multiple composite-key groups, every one of those
// groups gets an `mmdd` discriminator (e.g. "2-1207", "2-0321", "2-0526")
// so React keys, collapse state, sort, and TotalRow display stay unique.
// Engine bases that produced exactly one group (the common case — a single
// position) keep their bare engine baseId for visual continuity with engine
// numbering.

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
 * Format an entry-time string as `mmdd` (zero-padded month+day) for use as a
 * position discriminator. Engine base IDs collide across positions (BTC-39063)
 * so the date suffix lets the UI tell 2025-12-07's "Trade 2" apart from
 * 2026-03-21's "Trade 2" and 2026-05-26's "Trade 2" at a glance. Tolerates
 * full ISO strings (`2025-12-07T14:00:00Z`) by parsing only the leading
 * `YYYY-MM-DD`; falls back to `0000` for missing or malformed inputs so the
 * discriminator shape stays consistent (rather than risking an empty suffix
 * that would collide with the bare engine baseId).
 */
function formatMmdd(entryTime: string): string {
  if (!entryTime) return '0000';
  const m = entryTime.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return '0000';
  return `${m[2]}${m[3]}`;
}

/**
 * Internal bookkeeping record for one composite-key bucket during grouping.
 * Stripped from the public return — only `baseId`, `trades`, `totalPnl`,
 * `totalPnlPct` are exposed via the public `TradeGroup` shape. The
 * `engineBase` field is the pre-discriminator id used solely for collision
 * detection; `entryTime` and `entryPrice` are the canonical values of the
 * composite key (every leg in the same group shares them by construction).
 */
interface InternalGroup {
  baseId: string;
  engineBase: string;
  entryTime: string;
  entryPrice: number;
  trades: Trade[];
  totalPnl: number;
  totalPnlPct: number;
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
 *
 * BTCAAAAA-39063 defense: grouping is keyed by the COMPOSITE
 * (engineBaseId, entryTime, entryPrice) tuple, not by `baseTradeId` alone.
 * The engine's per-trade counter is global, so distinct positions opened
 * weeks apart can be emitted with the same base id ("2", "2.1", "2.2"…).
 * Without the composite key those positions would collapse into one "Trade 2"
 * parent. After bucketing, we count how many buckets share each engine base:
 * if exactly one bucket has that engine base, we keep the bare id for visual
 * parity with engine numbering; if multiple buckets share an engine base,
 * we suffix every colliding bucket's `baseId` with its entry-time `mmdd`
 * (e.g. "2-1207", "2-0321", "2-0526") so React keys, collapse state, sort,
 * and TotalRow display stay unique. The composite key intentionally uses
 * `entryTime` (not `exitTime`) because the bug is about positions — and a
 * position's identity is anchored at its entry bar, not its close.
 */
export function groupTradesById(raw: Trade[]): TradeGroup[] {
  // Phase 1: bucket by composite key (engineBase, entryTime, entryPrice).
  // We keep insertion order in `order` so the outer group list follows the
  // engine's natural trade sequence, matching prior behavior.
  const map = new Map<string, InternalGroup>();
  const order: string[] = [];

  for (const t of raw) {
    const engineBase = baseTradeId(t.id);
    const entryTime = t.entryTime ?? '';
    const entryPrice = t.entryPrice ?? 0;
    const compositeKey = `${engineBase}|${entryTime}|${entryPrice}`;
    let g = map.get(compositeKey);
    if (!g) {
      g = {
        baseId: engineBase,
        engineBase,
        entryTime,
        entryPrice,
        trades: [],
        totalPnl: 0,
        totalPnlPct: 0,
      };
      map.set(compositeKey, g);
      order.push(compositeKey);
    }
    g.trades.push(t);
    g.totalPnl += t.pnl ?? 0;
  }

  // Phase 2: detect engine-base collisions and apply the mmdd discriminator
  // ONLY to groups that share their engine base with at least one other group.
  // Bare engine bases (the common single-position case) are left untouched so
  // the visual label "Trade 5" still matches engine numbering.
  const engineBaseCounts = new Map<string, number>();
  for (const key of order) {
    const g = map.get(key)!;
    engineBaseCounts.set(g.engineBase, (engineBaseCounts.get(g.engineBase) ?? 0) + 1);
  }
  for (const key of order) {
    const g = map.get(key)!;
    if (engineBaseCounts.get(g.engineBase)! > 1) {
      g.baseId = `${g.engineBase}-${formatMmdd(g.entryTime)}`;
    }
  }

  // Phase 3: sort legs within each group by chronological close, then compute
  // the notional-derived aggregate percentage. Leg sort and P&L math are
  // unchanged from BTC-39025 / BTC-39061; we keep them post-relabel so the
  // `entryNotionalForGroup` helper still reads the first leg's `entryPrice`
  // (every leg of the same composite group shares it).
  for (const key of order) {
    const g = map.get(key)!;
    g.trades.sort(compareLegsByCloseTime);
    const notional = entryNotionalForGroup(g.trades);
    g.totalPnlPct = notional > 0 ? (g.totalPnl / notional) * 100 : 0;
  }

  // Phase 4: strip the internal-only fields so consumers see the public
  // `TradeGroup` shape unchanged.
  return order.map(key => {
    const g = map.get(key)!;
    return {
      baseId: g.baseId,
      trades: g.trades,
      totalPnl: g.totalPnl,
      totalPnlPct: g.totalPnlPct,
    };
  });
}
