/**
 * BTCAAAAA-38464 (Stream 3, L2): confidence-floor helpers for AI recs.
 *
 * `AiRecommendationsPanel` parses the AI's free-form `Confidence:` field into
 * the string values "high" / "medium" / "med" / "low" (see
 * `confidenceToUplift` in the panel). This module assigns those tags a numeric
 * 0-1 score so the panel can filter out low-confidence recs behind a
 * "Show low-confidence recs" disclosure.
 *
 * Mapping rationale (default floor = 0.4):
 *   high    -> 1.00  shown
 *   medium  -> 0.66  shown
 *   med     -> 0.66  shown (alias)
 *   unknown -> 0.50  shown by default (AI did not label — friendly default;
 *                      the user can still hide unknown recs by raising the
 *                      floor in a future iteration)
 *   low     -> 0.33  hidden by default
 *
 * "Medium" and "high" pass the default floor; "low" and explicit "0" do not.
 * Unknown recs are visible by default because the model simply failed to
 * report a label — not because it signaled low confidence.
 */

export const DEFAULT_CONFIDENCE_FLOOR = 0.4;

/** Parsed confidence tags we recognize. Lowercased + trimmed before compare. */
const CONFIDENCE_MAP: Record<string, number> = {
  high: 1.0,
  medium: 0.66,
  med: 0.66,
  low: 0.33,
};

/**
 * Convert the free-form `Confidence:` field from an AI rec to a 0-1 score.
 * Returns `null` (NOT a number) when the rec has no confidence label so
 * callers can distinguish "AI said nothing" from "AI said low (= 0.33)".
 */
export function confidenceToScore(confidence: string | undefined): number | null {
  if (typeof confidence !== 'string') return null;
  const key = confidence.trim().toLowerCase();
  if (key === '') return null;
  if (key in CONFIDENCE_MAP) return CONFIDENCE_MAP[key];
  // Numeric passthrough — some AI outputs use 0-1 or 0-100.
  const numeric = Number(key);
  if (Number.isFinite(numeric)) {
    if (numeric > 1) return Math.min(numeric / 100, 1);
    return Math.max(0, Math.min(numeric, 1));
  }
  return null;
}

/** True when the rec clears the floor. Unknown confidence never clears. */
export function meetsConfidenceFloor(
  confidence: string | undefined,
  floor: number = DEFAULT_CONFIDENCE_FLOOR,
): boolean {
  const score = confidenceToScore(confidence);
  if (score === null) return false;
  return score >= floor;
}

/**
 * Returns a stable numeric score for rec ordering / filtering. Falls back to
 * 0 (hidden by default) for unknown confidence so consumers do not have to
 * branch on null.
 */
export function recConfidenceScore(
  confidence: string | undefined,
): number {
  return confidenceToScore(confidence) ?? 0;
}
