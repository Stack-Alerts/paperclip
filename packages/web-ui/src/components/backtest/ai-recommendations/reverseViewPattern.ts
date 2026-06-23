/**
 * Pure-function extractor for the A4 "Reverse view — what the winners share"
 * banner (BTCAAAAA-37777). Takes the same recommendation payload the row
 * already renders, isolates the top-quartile by uplift, and surfaces the
 * categories and parameter keys those winners have in common. Deterministic
 * for a fixed input — no time, no randomness, no I/O.
 */

export interface ReverseViewInput {
  id: string;
  /** Uplift in percent. Positive = improves the strategy. Missing/NaN = 0. */
  uplift?: number;
  /** Free-form category label (e.g. "risk", "entry"). */
  category?: string;
  /** Parameter keys this recommendation would change. */
  paramKeys?: ReadonlyArray<string>;
}

export interface ReverseViewPattern {
  /** Number of recs that landed in the top quartile. */
  sampleSize: number;
  /** Total recs considered. */
  totalSize: number;
  /** Average uplift across the top-quartile sample (percent). */
  avgUplift: number;
  /** Top-quartile categories ordered by frequency desc, then label asc. */
  topCategories: string[];
  /** Top-quartile parameter keys ordered by frequency desc, then key asc. */
  topParamKeys: string[];
  /** One-line summary suitable for the banner headline. */
  headline: string;
}

const EMPTY_PATTERN: ReverseViewPattern = {
  sampleSize: 0,
  totalSize: 0,
  avgUplift: 0,
  topCategories: [],
  topParamKeys: [],
  headline: 'Not enough recommendations yet to surface a shared pattern.',
};

const MAX_LIST_ITEMS = 3;

function safeUplift(value: number | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function rankByFrequency(values: ReadonlyArray<string>): string[] {
  const counts = new Map<string, number>();
  for (const v of values) {
    if (!v) continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .slice(0, MAX_LIST_ITEMS)
    .map(([k]) => k);
}

function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function extractReverseViewPattern(
  recommendations: ReadonlyArray<ReverseViewInput>,
): ReverseViewPattern {
  if (!recommendations || recommendations.length === 0) return EMPTY_PATTERN;

  const sorted = [...recommendations].sort(
    (a, b) => safeUplift(b.uplift) - safeUplift(a.uplift),
  );
  const totalSize = sorted.length;
  const sampleSize = Math.max(1, Math.ceil(totalSize / 4));
  const top = sorted.slice(0, sampleSize);

  const sumUplift = top.reduce((acc, r) => acc + safeUplift(r.uplift), 0);
  const avgUplift = sumUplift / sampleSize;

  const topCategories = rankByFrequency(
    top.map((r) => (r.category ?? '').trim()).filter((s) => s.length > 0),
  );
  const topParamKeys = rankByFrequency(
    top
      .flatMap((r) => (r.paramKeys ?? []).map((k) => k.trim()))
      .filter((s) => s.length > 0),
  );

  const headline =
    `Top quartile (${sampleSize} of ${totalSize}) lifts the strategy by ` +
    `${formatPercent(avgUplift)} on average.`;

  return {
    sampleSize,
    totalSize,
    avgUplift,
    topCategories,
    topParamKeys,
    headline,
  };
}
