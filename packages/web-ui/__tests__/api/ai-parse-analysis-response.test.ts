import { parseAnalysisResponse, SYSTEM_PROMPT } from '../../app/api/ai/analyze/analyzer';
import {
  ALL_BLOCK_TYPES,
  BLOCK_TYPE_VOCABULARY,
} from '@/lib/strategy-builder/blockTypeVocabulary';

describe('SYSTEM_PROMPT block vocabulary (BTCAAAAA-38730)', () => {
  it('uses the canonical BlockType vocabulary, not the old category names', () => {
    // The static analyze prompt and the dynamic buildAiRecsSystemPrompt reach
    // the model in the same call; both must name the same block vocabulary so
    // an ADD_BLOCK suggestion is always matchable by the auto-apply path.
    expect(SYSTEM_PROMPT).toContain(BLOCK_TYPE_VOCABULARY);
    for (const type of ALL_BLOCK_TYPES) {
      expect(SYSTEM_PROMPT).toContain(type);
    }
  });

  it('no longer references the conflicting category taxonomy', () => {
    for (const category of [
      'PATTERNS',
      'OSCILLATORS',
      'MOVING_AVERAGES',
      'SMC_ICT',
      'WYCKOFF',
    ]) {
      expect(SYSTEM_PROMPT).not.toContain(category);
    }
  });
});

describe('parseAnalysisResponse (BTCAAAAA-37067)', () => {
  it('parses plain "RECOMMENDATIONS:" header', () => {
    const text = `DIAGNOSIS: Strategy is sound.

RECOMMENDATIONS:
1. Reduce position size
2. Tighten stop-loss`;

    const result = parseAnalysisResponse(text);
    expect(result.diagnosis).toContain('Strategy is sound');
    expect(result.recommendations).toContain('Reduce position size');
    expect(result.recommendations).toContain('Tighten stop-loss');
  });

  it('parses markdown "## RECOMMENDATIONS" header', () => {
    const text = `## DIAGNOSIS
Strategy is sound.

## RECOMMENDATIONS
1. Reduce position size`;

    const result = parseAnalysisResponse(text);
    expect(result.diagnosis).toContain('Strategy is sound');
    expect(result.recommendations).toContain('Reduce position size');
  });

  it('parses markdown "## Actionable Recommendations" header (DeepSeek default)', () => {
    const text = `## DIAGNOSIS
Strategy is too aggressive.

## Actionable Recommendations
1. Reduce position size
   Type: signal
   Parameter: maxAllocation
   Suggested Value: 15

2. Tighten stop-loss
   Type: risk
   Parameter: stopLossPct
   Suggested Value: 1.5`;

    const result = parseAnalysisResponse(text);
    expect(result.diagnosis).toContain('Strategy is too aggressive');
    expect(result.recommendations).toContain('Reduce position size');
    expect(result.recommendations).toContain('Tighten stop-loss');
    expect(result.recommendations).toContain('Suggested Value: 15');
  });

  it('parses bold "**Actionable RECOMMENDATIONS:**" header', () => {
    const text = `DIAGNOSIS: x

**Actionable RECOMMENDATIONS:**
1. First item`;

    const result = parseAnalysisResponse(text);
    expect(result.recommendations).toContain('First item');
  });

  it('parses "#" through "######" header depths with Actionable prefix', () => {
    const depths = ['#', '##', '###', '####', '#####', '######'];
    for (const depth of depths) {
      const text = `Diagnosis text.

${depth} Actionable Recommendations
1. Item for ${depth}`;

      const result = parseAnalysisResponse(text);
      expect(result.recommendations).toContain(`Item for ${depth}`);
    }
  });

  it('parses "## Actionable Recommendations:" with trailing colon', () => {
    const text = `## DIAGNOSIS
d

## Actionable Recommendations:
1. Item one`;

    const result = parseAnalysisResponse(text);
    expect(result.recommendations).toContain('Item one');
  });

  it('falls back to numbered-list split when no headers are present', () => {
    const text = `Some leading diagnosis prose.

1. First rec
2. Second rec`;

    const result = parseAnalysisResponse(text);
    expect(result.diagnosis).toContain('Some leading diagnosis prose');
    expect(result.recommendations).toContain('First rec');
    expect(result.recommendations).toContain('Second rec');
  });
});
