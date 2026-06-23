import { computeReanalyzeHash } from '@/components/backtest/ai-recommendations/dirtyHash';

describe('computeReanalyzeHash', () => {
  it('returns the same hash for equal inputs', () => {
    const a = computeReanalyzeHash({ id: 's1', blocks: [{ k: 1 }] }, { tf: '1h' });
    const b = computeReanalyzeHash({ id: 's1', blocks: [{ k: 1 }] }, { tf: '1h' });
    expect(a).toBe(b);
  });

  it('is invariant to key ordering in objects', () => {
    const a = computeReanalyzeHash({ a: 1, b: 2 }, { x: 'y', z: 9 });
    const b = computeReanalyzeHash({ b: 2, a: 1 }, { z: 9, x: 'y' });
    expect(a).toBe(b);
  });

  it('changes when the strategy changes', () => {
    const before = computeReanalyzeHash({ id: 's1', blocks: [{ k: 1 }] }, { tf: '1h' });
    const after = computeReanalyzeHash({ id: 's1', blocks: [{ k: 2 }] }, { tf: '1h' });
    expect(after).not.toBe(before);
  });

  it('changes when the backtest config changes', () => {
    const before = computeReanalyzeHash({ id: 's1' }, { tf: '1h' });
    const after = computeReanalyzeHash({ id: 's1' }, { tf: '4h' });
    expect(after).not.toBe(before);
  });

  it('is array-order sensitive', () => {
    const a = computeReanalyzeHash({ blocks: [1, 2] }, null);
    const b = computeReanalyzeHash({ blocks: [2, 1] }, null);
    expect(a).not.toBe(b);
  });

  it('handles null inputs without throwing', () => {
    expect(() => computeReanalyzeHash(null, null)).not.toThrow();
    expect(computeReanalyzeHash(null, null)).toBe(computeReanalyzeHash(null, null));
  });
});
