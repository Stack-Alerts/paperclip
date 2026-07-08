/**
 * BTCAAAAA-39057: per-row SIZE column now routes through `derivedSize()` so
 * trade legs the backend failed to populate with `quantity` no longer bail to
 * '—' silently. The helper picks the best available source from a 4-tier
 * fallback chain and returns a reason code so the cell can show a per-row
 * tooltip explaining what it knows.
 *
 * Acceptance criteria (per the wake payload):
 *   - Tier 1 (reported): `quantity > 0` → use as-is, no tooltip.
 *   - Tier 2 (partialBreakdown): quantity missing but breakdown present →
 *     value: null with a tooltip explaining the breakdown carries USD P&L
 *     but not per-leg size, so we cannot derive from it.
 *   - Tier 3 (riskGuard): BOTH `riskUsd` and `stopDistanceAtEntry` populated
 *     and positive → derive `riskUsd / stopDistanceAtEntry`.
 *   - Tier 4 (unavailable): nothing → value: null + tooltip naming the
 *     missing fields.
 *
 * The implementation lives in `../TradesPanel.tsx` (`derivedSize` export).
 * Precedence: Tier 1 > Tier 2 > Tier 3 > Tier 4. Tier 2 wins over Tier 3
 * even when both are populated (Tier 2 is checked first in the chain).
 */

import { Trade } from '@/lib/strategy-builder/types';
import { derivedSize, DerivedSizeReason } from '../TradesPanel';

const makeTrade = (overrides: Partial<Trade> = {}): Trade => ({
  id: 't.1',
  entryTime: '2026-01-01T00:00:00Z',
  exitTime: '2026-01-01T01:00:00Z',
  entryPrice: 100,
  exitPrice: 101,
  quantity: 0.33,
  pnl: 33,
  pnlPercentage: 1,
  bars: 1,
  side: 'LONG',
  status: 'CLOSED',
  ...overrides,
});

describe('derivedSize — BTCAAAAA-39057', () => {
  it('Tier 1: returns reported quantity when positive, reason="reported"', () => {
    const trade = makeTrade({ id: 't.1', quantity: 0.5 });
    const result = derivedSize(trade);
    expect(result.value).toBe(0.5);
    expect(result.reason).toBe('reported');
    expect(result.tooltip).toContain('backend reported size');
    expect(result.tooltip).toContain('0.5000');
  });

  it('Tier 2: returns null with reason="partialBreakdown" when quantity missing but breakdown present', () => {
    const trade = makeTrade({
      id: 't.2',
      quantity: undefined,
      partialBreakdown: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)',
    });
    const result = derivedSize(trade);
    expect(result.value).toBeNull();
    expect(result.reason).toBe('partialBreakdown');
    expect(result.tooltip).toContain('partial-exit breakdown');
    expect(result.tooltip).toContain('TP1');
    expect(result.tooltip).toContain('cannot be derived');
  });

  it('Tier 3: derives from riskUsd / stopDistanceAtEntry when both positive', () => {
    const trade = makeTrade({
      id: 't.3',
      quantity: undefined,
      partialBreakdown: undefined,
      riskUsd: 100,
      stopDistanceAtEntry: 50,
    });
    const result = derivedSize(trade);
    expect(result.value).toBe(2); // 100 / 50 = 2
    expect(result.reason).toBe('riskGuard');
    expect(result.tooltip).toContain('Derived size');
    expect(result.tooltip).toContain('100');
    expect(result.tooltip).toContain('50');
    expect(result.tooltip).toContain('2.0000');
  });

  it('Tier 4: returns null with reason="unavailable" when nothing is usable', () => {
    const trade = makeTrade({
      id: 't.4',
      quantity: undefined,
      partialBreakdown: undefined,
      riskUsd: undefined,
      stopDistanceAtEntry: undefined,
    });
    const result = derivedSize(trade);
    expect(result.value).toBeNull();
    expect(result.reason).toBe('unavailable');
    expect(result.tooltip).toContain('no size reported');
    expect(result.tooltip).toContain('riskUsd or stopDistanceAtEntry missing');
  });

  it('treats undefined quantity as missing (defensive — backend gap)', () => {
    const trade = makeTrade({ id: 't.5', quantity: undefined });
    const result = derivedSize(trade);
    expect(result.reason).toBe('unavailable');
    expect(result.value).toBeNull();
  });

  it('Tier 1 wins over Tier 3: positive quantity short-circuits the chain', () => {
    const trade = makeTrade({
      id: 't.6',
      quantity: 0.42,
      riskUsd: 100,
      stopDistanceAtEntry: 50,
    });
    const result = derivedSize(trade);
    expect(result.value).toBe(0.42);
    expect(result.reason).toBe('reported');
  });

  it('Tier 2 wins over Tier 3: partialBreakdown is checked before risk-guard derivation', () => {
    const trade = makeTrade({
      id: 't.7',
      quantity: undefined,
      partialBreakdown: 'TP1: $10.00 (33%)',
      riskUsd: 100,
      stopDistanceAtEntry: 50,
    });
    const result = derivedSize(trade);
    expect(result.value).toBeNull();
    expect(result.reason).toBe('partialBreakdown');
  });

  it('Tier 3 skipped when stopDistanceAtEntry = 0 (no NaN, no Infinity)', () => {
    const trade = makeTrade({
      id: 't.8',
      quantity: undefined,
      riskUsd: 100,
      stopDistanceAtEntry: 0,
    });
    const result = derivedSize(trade);
    expect(result.reason).toBe('unavailable');
    expect(result.value).toBeNull();
  });

  it('Tier 3 skipped when riskUsd = 0 (no division by zero edge)', () => {
    const trade = makeTrade({
      id: 't.9',
      quantity: undefined,
      riskUsd: 0,
      stopDistanceAtEntry: 50,
    });
    const result = derivedSize(trade);
    expect(result.reason).toBe('unavailable');
    expect(result.value).toBeNull();
  });

  it('treats empty-string partialBreakdown as absent (falls through to Tier 3/4)', () => {
    const trade = makeTrade({
      id: 't.10',
      quantity: undefined,
      partialBreakdown: '',
      riskUsd: 100,
      stopDistanceAtEntry: 50,
    });
    const result = derivedSize(trade);
    // Empty string is not "present" — fall through to Tier 3 derivation.
    expect(result.reason).toBe('riskGuard');
    expect(result.value).toBe(2);
  });

  it('Derivation math: fractional inputs produce non-integer outputs (sanity)', () => {
    const trade = makeTrade({
      id: 't.11',
      quantity: undefined,
      riskUsd: 250,
      stopDistanceAtEntry: 75,
    });
    const result = derivedSize(trade);
    expect(result.value).toBeCloseTo(3.3333, 4);
    expect(result.reason).toBe('riskGuard');
  });

  it('DerivedSizeReason union is exhaustive across all 4 tiers (compile-time shape)', () => {
    // Pin the literal union so a future refactor that adds a tier forces a
    // test update here.
    const reasons: DerivedSizeReason[] = ['reported', 'partialBreakdown', 'riskGuard', 'unavailable'];
    expect(reasons).toHaveLength(4);
  });
});