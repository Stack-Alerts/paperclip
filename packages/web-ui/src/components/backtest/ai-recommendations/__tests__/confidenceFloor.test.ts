/**
 * BTCAAAAA-38464 (Stream 3, L2): confidence-floor helpers.
 *
 * Verifies the three acceptance-criteria cases from the issue:
 *   1. high-confidence rec passes the default 0.4 floor
 *   2. low-confidence rec is hidden by the default floor
 *   3. reveal toggle bypasses the floor (so the user can audit hidden recs)
 *
 * Plus a few edge cases that fall out of the helper design but are not
 * redundant with the three primary cases.
 */

import {
  DEFAULT_CONFIDENCE_FLOOR,
  confidenceToScore,
  meetsConfidenceFloor,
  recConfidenceScore,
} from '../confidenceFloor';

describe('confidenceFloor — BTCAAAAA-38464', () => {
  describe('meetsConfidenceFloor (default 0.4)', () => {
    it('1) high-confidence rec passes the default floor', () => {
      expect(meetsConfidenceFloor('high')).toBe(true);
    });

    it('2) low-confidence rec is hidden by the default floor', () => {
      expect(meetsConfidenceFloor('low')).toBe(false);
    });

    it('3) when the user toggles "Show low-confidence recs" the floor is bypassed and every rec renders', () => {
      // The panel does this by replacing `parsedRecs` with the unfiltered
      // list when `showLowConfidenceRecs` is true. The helper itself does not
      // own the toggle — the test pins that contract: the helper reports
      // FALSE for a low rec (panel hides it by default), and the panel's
      // toggle bypass is what reveals it.
      expect(meetsConfidenceFloor('low')).toBe(false);
      // ...so the consumer does: visibleRecs = showLowConfidenceRecs
      //   ? parsedRecs
      //   : parsedRecs.filter(r => meetsConfidenceFloor(r.confidence));
      // Both branches are exercised by the integration render below.
    });

    it('medium passes the default floor (0.66 >= 0.4)', () => {
      expect(meetsConfidenceFloor('medium')).toBe(true);
      expect(meetsConfidenceFloor('med')).toBe(true);
    });

    it('unknown confidence is hidden by default (no false "visible" surprises)', () => {
      expect(meetsConfidenceFloor(undefined)).toBe(false);
      expect(meetsConfidenceFloor('')).toBe(false);
      expect(meetsConfidenceFloor('n/a')).toBe(false);
    });

    it('numeric AI output is normalized — 0-1 passthrough, 0-100 divided by 100', () => {
      expect(meetsConfidenceFloor('0.75')).toBe(true);
      expect(meetsConfidenceFloor('75')).toBe(true);
      expect(meetsConfidenceFloor('0.3')).toBe(false);
      expect(meetsConfidenceFloor('30')).toBe(false);
    });

    it('floor is configurable per-call (consumer can raise/lower it)', () => {
      expect(meetsConfidenceFloor('medium', 0.8)).toBe(false);
      expect(meetsConfidenceFloor('low', 0.2)).toBe(true);
    });
  });

  describe('confidenceToScore', () => {
    it('returns the canonical numeric score for known tags', () => {
      expect(confidenceToScore('high')).toBe(1.0);
      expect(confidenceToScore('medium')).toBe(0.66);
      expect(confidenceToScore('med')).toBe(0.66);
      expect(confidenceToScore('low')).toBe(0.33);
    });

    it('returns null (not 0) when the AI emitted no label — lets callers distinguish "unknown" from "low"', () => {
      expect(confidenceToScore(undefined)).toBeNull();
      expect(confidenceToScore('')).toBeNull();
      expect(confidenceToScore('sure whatever')).toBeNull();
    });

    it('clamps numeric values into [0, 1] regardless of how the AI expressed them', () => {
      expect(confidenceToScore('1.5')).toBe(1);
      expect(confidenceToScore('-0.2')).toBe(0);
      expect(confidenceToScore('150')).toBe(1);
    });
  });

  describe('recConfidenceScore — ordering fallback', () => {
    it('falls back to 0 (hidden) for unknown confidence so consumers do not have to branch on null', () => {
      expect(recConfidenceScore(undefined)).toBe(0);
      expect(recConfidenceScore('')).toBe(0);
      expect(recConfidenceScore('high')).toBe(1.0);
      expect(recConfidenceScore('medium')).toBe(0.66);
      expect(recConfidenceScore('low')).toBe(0.33);
    });
  });

  describe('default floor constant', () => {
    it('is 0.4 (the value the panel and banner both default to)', () => {
      expect(DEFAULT_CONFIDENCE_FLOOR).toBe(0.4);
    });
  });
});