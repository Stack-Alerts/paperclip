import {
  detectConflicts,
  ConflictRecShape,
  RecConflictInfo,
} from '@/components/backtest/ai-recommendations/conflictDetector';

const LOSER_TOOLTIP =
  'Another higher-confidence recommendation targets the same parameter';

function makeRec(
  over: Partial<ConflictRecShape> & { id: string },
): ConflictRecShape {
  return {
    id: over.id,
    confidence: over.confidence,
    suggestedParams: over.suggestedParams ?? [],
    parameter: over.parameter,
  };
}

describe('detectConflicts', () => {
  it('case 1 — no conflict: each rec targets a unique parameter', () => {
    const recs: ConflictRecShape[] = [
      makeRec({ id: 'r1', confidence: 'high', parameter: 'window' }),
      makeRec({ id: 'r2', confidence: 'medium', parameter: 'rsi_period' }),
      makeRec({ id: 'r3', confidence: 'low', parameter: 'macd_fast' }),
    ];
    const map = detectConflicts(recs);
    expect(map.size).toBe(3);
    for (const info of map.values()) {
      expect(info.isConflictLoser).toBe(false);
      expect(info.conflictTooltip).toBeUndefined();
    }
  });

  it('case 2 — 2-way conflict: same param, different confidence → low one loses', () => {
    const recs: ConflictRecShape[] = [
      makeRec({ id: 'r1', confidence: 'high', parameter: 'window' }),
      makeRec({ id: 'r2', confidence: 'low', parameter: 'window' }),
    ];
    const map = detectConflicts(recs);
    expect(map.size).toBe(2);

    const winner = map.get('r1') as RecConflictInfo;
    expect(winner.isConflictLoser).toBe(false);
    expect(winner.groupSize).toBe(2);
    expect(winner.winnerId).toBe('r1');

    const loser = map.get('r2') as RecConflictInfo;
    expect(loser.isConflictLoser).toBe(true);
    expect(loser.conflictTooltip).toBe(LOSER_TOOLTIP);
    expect(loser.groupSize).toBe(2);
    expect(loser.winnerId).toBe('r1');
  });

  it('case 3 — 3-way conflict: same param, mixed confidence → only high wins', () => {
    const recs: ConflictRecShape[] = [
      makeRec({ id: 'r1', confidence: 'medium', parameter: 'window' }),
      makeRec({ id: 'r2', confidence: 'low', parameter: 'window' }),
      makeRec({ id: 'r3', confidence: 'high', parameter: 'window' }),
    ];
    const map = detectConflicts(recs);
    expect(map.size).toBe(3);

    const winner = map.get('r3') as RecConflictInfo;
    expect(winner.isConflictLoser).toBe(false);
    expect(winner.winnerId).toBe('r3');
    expect(winner.groupSize).toBe(3);

    const medium = map.get('r1') as RecConflictInfo;
    expect(medium.isConflictLoser).toBe(true);
    expect(medium.conflictTooltip).toBe(LOSER_TOOLTIP);
    expect(medium.winnerId).toBe('r3');

    const low = map.get('r2') as RecConflictInfo;
    expect(low.isConflictLoser).toBe(true);
    expect(low.conflictTooltip).toBe(LOSER_TOOLTIP);
    expect(low.winnerId).toBe('r3');
  });

  it('treats the `parameter` field as a target key when suggestedParams is empty', () => {
    const recs: ConflictRecShape[] = [
      makeRec({ id: 'a', confidence: 'low', parameter: 'window' }),
      makeRec({
        id: 'b',
        confidence: 'high',
        suggestedParams: [{ key: 'window', value: '20' }],
      }),
    ];
    const map = detectConflicts(recs);
    const a = map.get('a') as RecConflictInfo;
    const b = map.get('b') as RecConflictInfo;
    expect(b.isConflictLoser).toBe(false);
    expect(a.isConflictLoser).toBe(true);
    expect(a.winnerId).toBe('b');
  });

  it('returns an empty map for an empty input', () => {
    const map = detectConflicts([]);
    expect(map.size).toBe(0);
  });

  it('does not flag a rec with no target keys as a loser', () => {
    const recs: ConflictRecShape[] = [
      makeRec({ id: 'a', confidence: 'high' }),
      makeRec({ id: 'b', confidence: 'low', parameter: 'window' }),
    ];
    const map = detectConflicts(recs);
    const a = map.get('a') as RecConflictInfo;
    const b = map.get('b') as RecConflictInfo;
    expect(a.isConflictLoser).toBe(false);
    expect(b.isConflictLoser).toBe(false);
  });
});
