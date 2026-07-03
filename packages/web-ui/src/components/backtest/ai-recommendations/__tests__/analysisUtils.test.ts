/**
 * BTCAAAAA-37771: `parseAnalysisResponse` hardening.
 *
 * The board ran a completed Re-analyze and saw a blank Recommendations box.
 * That happens when the parser extracts an empty `recommendations` string,
 * which then yields zero cards. These tests pin the deviations that used to
 * leave the box blank so they now split out a non-empty recommendations
 * section, plus regression guards for the formats that already worked.
 */

import { parseAnalysisResponse } from '../analysisUtils';

describe('parseAnalysisResponse — BTCAAAAA-37771 blank-box hardening', () => {
  it('regression: plain DIAGNOSIS: / RECOMMENDATIONS: form still splits', () => {
    const { diagnosis, recommendations } = parseAnalysisResponse(
      'DIAGNOSIS: Win rate is low.\nRECOMMENDATIONS:\n1. Widen the EMA window.',
    );
    expect(diagnosis).toContain('Win rate is low');
    expect(recommendations).toContain('Widen the EMA window');
  });

  it('bold synonym heading `**Recommended Changes:**` is treated as the recs header', () => {
    const { recommendations } = parseAnalysisResponse(
      '**Diagnosis:** Chop is hurting entries.\n\n**Recommended Changes:**\n1. Raise ATR filter.',
    );
    expect(recommendations).toContain('Raise ATR filter');
  });

  it('markdown heading `## Suggested Improvements` is treated as the recs header', () => {
    const { recommendations } = parseAnalysisResponse(
      '## Diagnosis\nDrawdown too high.\n\n## Suggested Improvements\n1. Tighten stop loss.',
    );
    expect(recommendations).toContain('Tighten stop loss');
  });

  it('singular `## Recommendation` heading is recognized', () => {
    const { recommendations } = parseAnalysisResponse(
      '## Diagnosis\nOverfit.\n\n## Recommendation\n1. Add walk-forward split.',
    );
    expect(recommendations).toContain('walk-forward split');
  });

  it('bulleted recs under DIAGNOSIS with no recs header are promoted (>=2 bullets)', () => {
    const { diagnosis, recommendations } = parseAnalysisResponse(
      'DIAGNOSIS: The strategy underperforms in trending regimes.\n' +
        '- Increase the trend-filter lookback to 100.\n' +
        '- Lower the take-profit multiple to 1.5.',
    );
    expect(recommendations).toContain('trend-filter lookback');
    expect(recommendations).toContain('take-profit multiple');
    expect(diagnosis).toContain('underperforms in trending regimes');
    expect(diagnosis).not.toContain('trend-filter lookback');
  });

  it('a single incidental dash in the diagnosis is NOT promoted to recommendations', () => {
    const { recommendations } = parseAnalysisResponse(
      'DIAGNOSIS: Win rate is 42% - below the 50% target for this regime.',
    );
    // Only one dash / no bullet list -> nothing promoted.
    expect(recommendations).toBe('');
  });

  it('numbered list still wins over bullets when both branches could match', () => {
    const { recommendations } = parseAnalysisResponse(
      'DIAGNOSIS: Issues below.\n1. First numbered rec.\n- a stray bullet.',
    );
    expect(recommendations).toContain('First numbered rec');
  });
});
