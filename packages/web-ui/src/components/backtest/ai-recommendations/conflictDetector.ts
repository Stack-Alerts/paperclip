/**
 * BTCAAAAA-38469 (Stream 8, L2/M2): single-winner guard for conflicting AI recs.
 *
 * Two recommendations "conflict" when they target the same parameter
 * (case-insensitive, trimmed). Within each conflict group, the
 * highest-confidence recommendation wins; the rest are flagged as
 * "conflict losers" so the UI can:
 *   - render a "Conflict" badge on the losers,
 *   - disable the apply toggle on the losers,
 *   - surface a "Why disabled?" tooltip pointing at the winner.
 *
 * A recommendation with NO target keys (empty suggestedParams AND no
 * `parameter` field) is never a loser — it has nothing to collide with.
 *
 * Confidence ranking (matches `confidenceToUplift` semantics, but in a
 * numeric form usable by `Array#sort`):
 *   high     -> 3
 *   medium   -> 2
 *   med      -> 2  (alias)
 *   low      -> 1
 *   (none)   -> 0
 *
 * Ties on confidence fall back to the original rec order so the
 * detector is deterministic across runs (the first rec in the array
 * keeps the slot when scores are equal).
 */

export interface ConflictRecShape {
  id: string;
  confidence?: string;
  suggestedParams?: Array<{ key: string; value: string }>;
  parameter?: string;
}

export interface RecConflictInfo {
  isConflictLoser: boolean;
  conflictTooltip?: string;
  groupSize: number;
  winnerId?: string;
}

export const CONFLICT_LOSER_TOOLTIP =
  'Another higher-confidence recommendation targets the same parameter';

function targetKeysFor(rec: ConflictRecShape): Set<string> {
  const keys = new Set<string>();
  if (Array.isArray(rec.suggestedParams)) {
    for (const p of rec.suggestedParams) {
      if (p && typeof p.key === 'string') {
        const trimmed = p.key.trim().toLowerCase();
        if (trimmed !== '') keys.add(trimmed);
      }
    }
  }
  if (typeof rec.parameter === 'string') {
    const trimmed = rec.parameter.trim().toLowerCase();
    if (trimmed !== '') keys.add(trimmed);
  }
  return keys;
}

function confidenceScore(rec: ConflictRecShape): number {
  const c = (rec.confidence ?? '').trim().toLowerCase();
  if (c === 'high') return 3;
  if (c === 'medium' || c === 'med') return 2;
  if (c === 'low') return 1;
  return 0;
}

/**
 * Walks the rec list, groups by target param key, and returns a Map
 * from rec id to its conflict info. Recs that are not in any conflict
 * group get `{ isConflictLoser: false, groupSize: 0 }`.
 *
 * The function is pure: same input -> same output, no side effects.
 */
export function detectConflicts(
  recs: ConflictRecShape[],
): Map<string, RecConflictInfo> {
  const result = new Map<string, RecConflictInfo>();
  for (const rec of recs) {
    result.set(rec.id, { isConflictLoser: false, groupSize: 0 });
  }

  // Group rec ids by lowercase target key.
  const groupByKey = new Map<string, string[]>();
  for (const rec of recs) {
    const keys = targetKeysFor(rec);
    if (keys.size === 0) continue;
    for (const k of keys) {
      const bucket = groupByKey.get(k);
      if (bucket) bucket.push(rec.id);
      else groupByKey.set(k, [rec.id]);
    }
  }

  // Resolve each group with 2+ members: pick the winner, flag the rest.
  const recById = new Map<string, ConflictRecShape>();
  for (const rec of recs) recById.set(rec.id, rec);

  for (const [, ids] of groupByKey) {
    if (ids.length < 2) continue;

    const ranked = ids.map((id, originalIndex) => ({
      id,
      originalIndex,
      score: confidenceScore(recById.get(id) as ConflictRecShape),
    }));
    ranked.sort(
      (a, b) => b.score - a.score || a.originalIndex - b.originalIndex,
    );

    const winnerId = ranked[0].id;
    const groupSize = ids.length;

    for (const { id } of ranked) {
      const cur = result.get(id);
      if (!cur) continue;
      cur.groupSize = groupSize;
      cur.winnerId = winnerId;
      if (id !== winnerId) {
        cur.isConflictLoser = true;
        cur.conflictTooltip = CONFLICT_LOSER_TOOLTIP;
      }
    }
  }

  return result;
}