import {
  extractReverseViewPattern,
  ReverseViewInput,
} from '@/components/backtest/ai-recommendations/reverseViewPattern';

const FIXTURE: ReverseViewInput[] = [
  { id: 'r1', uplift: 5.0, category: 'risk', paramKeys: ['stop_atr_multiple'] },
  { id: 'r2', uplift: 4.0, category: 'risk', paramKeys: ['stop_atr_multiple', 'min_atr'] },
  { id: 'r3', uplift: 2.0, category: 'entry', paramKeys: ['ema_window'] },
  { id: 'r4', uplift: 1.0, category: 'entry', paramKeys: ['ema_window'] },
  { id: 'r5', uplift: -1.0, category: 'exit', paramKeys: ['take_profit'] },
  { id: 'r6', uplift: -2.0, category: 'regime', paramKeys: ['regime_threshold'] },
  { id: 'r7', uplift: -3.0, category: 'signal', paramKeys: ['atr_period'] },
  { id: 'r8', uplift: -4.0, category: 'signal', paramKeys: ['atr_period'] },
];

describe('extractReverseViewPattern', () => {
  it('returns the empty pattern for an empty list', () => {
    const out = extractReverseViewPattern([]);
    expect(out.sampleSize).toBe(0);
    expect(out.totalSize).toBe(0);
    expect(out.avgUplift).toBe(0);
    expect(out.topCategories).toEqual([]);
    expect(out.topParamKeys).toEqual([]);
    expect(out.headline).toMatch(/not enough/i);
  });

  it('picks the top quartile by uplift and averages it', () => {
    const out = extractReverseViewPattern(FIXTURE);
    expect(out.totalSize).toBe(8);
    expect(out.sampleSize).toBe(2); // ceil(8 / 4)
    expect(out.avgUplift).toBeCloseTo(4.5, 5); // (5.0 + 4.0) / 2
    expect(out.topCategories).toEqual(['risk']);
    expect(out.topParamKeys).toEqual(['stop_atr_multiple', 'min_atr']);
    expect(out.headline).toBe(
      'Top quartile (2 of 8) lifts the strategy by +4.5% on average.',
    );
  });

  it('always keeps at least one rec in the sample even with three inputs', () => {
    const out = extractReverseViewPattern(FIXTURE.slice(0, 3));
    expect(out.totalSize).toBe(3);
    expect(out.sampleSize).toBe(1); // ceil(3 / 4) = 1
    expect(out.avgUplift).toBeCloseTo(5.0, 5);
    expect(out.topCategories).toEqual(['risk']);
  });

  it('is deterministic — same input produces the same output', () => {
    const a = extractReverseViewPattern(FIXTURE);
    const b = extractReverseViewPattern(FIXTURE);
    expect(b).toEqual(a);
  });

  it('does not mutate the caller array', () => {
    const input = [...FIXTURE];
    const snapshot = JSON.stringify(input);
    extractReverseViewPattern(input);
    expect(JSON.stringify(input)).toBe(snapshot);
  });

  it('treats missing uplift as 0', () => {
    const out = extractReverseViewPattern([
      { id: 'a', category: 'risk', paramKeys: ['k1'] },
      { id: 'b', uplift: 3, category: 'entry', paramKeys: ['k2'] },
    ]);
    expect(out.sampleSize).toBe(1);
    expect(out.topCategories).toEqual(['entry']);
    expect(out.avgUplift).toBeCloseTo(3, 5);
  });

  it('ranks categories and params by frequency then alphabetically on ties', () => {
    const out = extractReverseViewPattern([
      { id: 'a', uplift: 9, category: 'beta', paramKeys: ['p1'] },
      { id: 'b', uplift: 8, category: 'alpha', paramKeys: ['p1'] },
      { id: 'c', uplift: 7, category: 'alpha', paramKeys: ['p2'] },
      { id: 'd', uplift: 6, category: 'beta', paramKeys: ['p1'] },
      { id: 'e', uplift: 1, category: 'gamma' },
      { id: 'f', uplift: 0, category: 'gamma' },
      { id: 'g', uplift: -1, category: 'delta' },
      { id: 'h', uplift: -2, category: 'delta' },
    ]);
    // sample = 2 — top two are uplift 9 (beta) and 8 (alpha), each once →
    // alphabetical tiebreak: alpha first, then beta.
    expect(out.sampleSize).toBe(2);
    expect(out.topCategories).toEqual(['alpha', 'beta']);
    expect(out.topParamKeys).toEqual(['p1']);
  });

  it('caps the topCategories and topParamKeys lists at three items', () => {
    const recs: ReverseViewInput[] = Array.from({ length: 20 }, (_, i) => ({
      id: `r${i}`,
      uplift: 20 - i,
      category: `c${i % 5}`,
      paramKeys: [`p${i % 4}`],
    }));
    const out = extractReverseViewPattern(recs);
    expect(out.sampleSize).toBe(5);
    expect(out.topCategories.length).toBeLessThanOrEqual(3);
    expect(out.topParamKeys.length).toBeLessThanOrEqual(3);
  });

  it('formats a negative average uplift without a leading +', () => {
    const out = extractReverseViewPattern([
      { id: 'a', uplift: -1, category: 'risk' },
      { id: 'b', uplift: -2, category: 'risk' },
      { id: 'c', uplift: -3, category: 'risk' },
      { id: 'd', uplift: -4, category: 'risk' },
    ]);
    expect(out.headline).toBe(
      'Top quartile (1 of 4) lifts the strategy by -1.0% on average.',
    );
  });
});
