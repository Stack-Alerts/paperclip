/**
 * Stream 7 (BTCAAAAA-38468) — feedbackCapture unit tests.
 *
 * Three test cases as required by the acceptance criteria:
 *   1. setFeedback persists to sessionStorage under the composite key;
 *      getFeedback reads it back; clearFeedback removes it.
 *   2. window.__AI_RECS_FEEDBACK__ exposes the full feedback map across
 *      multiple analyses.
 *   3. parseCompositeKey splits on the FIRST colon so UUIDs / composite IDs
 *      containing colons survive; rejects malformed input.
 */

import {
  clearFeedback,
  getAllFeedback,
  getFeedback,
  parseCompositeKey,
  setFeedback,
  storageKey,
} from '../feedbackCapture';

describe('feedbackCapture (BTCAAAAA-38468)', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    // Reset the window getter so each test starts from a clean map.
    delete (window as unknown as Record<string, unknown>).__AI_RECS_FEEDBACK__;
  });

  it('persists per-card feedback under the composite key and clears it', () => {
    const analysisId = 'an-1';
    const recId = 'rec-a';

    // Initially no feedback.
    expect(getFeedback(analysisId, recId)).toBeNull();

    // setFeedback stores the value under the composite key.
    setFeedback(analysisId, recId, 'up');
    expect(window.sessionStorage.getItem(storageKey(analysisId, recId))).toBe('up');
    expect(getFeedback(analysisId, recId)).toBe('up');

    // getAllFeedback returns the full map keyed by composite key.
    expect(getAllFeedback()).toEqual({ [`${analysisId}:${recId}`]: 'up' });

    // Re-setting overwrites the previous value.
    setFeedback(analysisId, recId, 'down');
    expect(getFeedback(analysisId, recId)).toBe('down');
    expect(window.sessionStorage.getItem(storageKey(analysisId, recId))).toBe('down');

    // clearFeedback removes the entry.
    clearFeedback(analysisId, recId);
    expect(getFeedback(analysisId, recId)).toBeNull();
    expect(window.sessionStorage.getItem(storageKey(analysisId, recId))).toBeNull();
    expect(getAllFeedback()).toEqual({});
  });

  it('exposes the full feedback map on window.__AI_RECS_FEEDBACK__', () => {
    // Three cards across two analyses.
    setFeedback('an-1', 'rec-a', 'up');
    setFeedback('an-1', 'rec-b', 'down');
    setFeedback('an-2', 'rec-c', 'up');

    // getAllFeedback returns all three.
    const all = getAllFeedback();
    expect(all).toEqual({
      'an-1:rec-a': 'up',
      'an-1:rec-b': 'down',
      'an-2:rec-c': 'up',
    });

    // window.__AI_RECS_FEEDBACK__ reflects the same map.
    const fromWindow = (window as unknown as Record<string, unknown>)
      .__AI_RECS_FEEDBACK__ as Record<string, string>;
    expect(fromWindow).toEqual(all);

    // Removing one entry refreshes the window getter.
    clearFeedback('an-1', 'rec-b');
    const after = (window as unknown as Record<string, unknown>)
      .__AI_RECS_FEEDBACK__ as Record<string, string>;
    expect(after).toEqual({
      'an-1:rec-a': 'up',
      'an-2:rec-c': 'up',
    });
  });

  it('parseCompositeKey splits on the FIRST colon and rejects malformed input', () => {
    // Normal case: two parts.
    expect(parseCompositeKey('an-1:rec-a')).toEqual({
      analysisId: 'an-1',
      recId: 'rec-a',
    });

    // UUID-style rec ID containing a colon — split on FIRST colon so the
    // recId preserves its UUID-with-colon shape.
    const uuidWithColon = 'urn:uuid:550e8400-e29b-41d4-a716-446655440000';
    const composite = `an-7:${uuidWithColon}`;
    const parsed = parseCompositeKey(composite);
    expect(parsed).not.toBeNull();
    expect(parsed!.analysisId).toBe('an-7');
    expect(parsed!.recId).toBe(uuidWithColon);

    // Rejects: empty string, no colon, leading colon, trailing colon.
    expect(parseCompositeKey('')).toBeNull();
    expect(parseCompositeKey('no-colon-here')).toBeNull();
    expect(parseCompositeKey(':rec-only')).toBeNull();
    expect(parseCompositeKey('analysis-only:')).toBeNull();

    // Rejects: non-string input.
    expect(parseCompositeKey(null as unknown as string)).toBeNull();
    expect(parseCompositeKey(undefined as unknown as string)).toBeNull();
    expect(parseCompositeKey(42 as unknown as string)).toBeNull();
  });
});
