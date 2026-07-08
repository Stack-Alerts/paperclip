/**
 * BTCAAAAA-39027: Partial % column bailed to '—' whenever a leg came back
 * without an `exitType` field, even if `exitPercentage` was populated. The
 * Partial % column should reflect what the engine actually computed —
 * '—' is reserved for the truly-empty case (no exit type AND no percentage).
 *
 * Verifies the new fallback chain:
 *   1. `partialBreakdown` (parent row pre-formatted multi-exit string) wins
 *      over everything.
 *   2. `exitType` shapes: TP1/TP2/SL/STOP_LOSS/MAX_BARS/TIME_LIMIT, with
 *      optional `exitPercentage` appended as " (33%)".
 *   3. **NEW** — `exitType` missing + `exitPercentage > 0` → "Partial (33%): $X"
 *      instead of the old "—". This is the regression covered here.
 *   4. `exitType` missing + `exitPercentage` 0/missing → bare "—" (honest fallback).
 */

import { Trade } from '@/lib/strategy-builder/types';
import { partialDisplay } from '../TradesPanel';

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
  status: 'closed',
  ...overrides,
});

describe('partialDisplay — BTCAAAAA-39027', () => {
  it('returns the parent partialBreakdown verbatim when present (covers every leg in one string)', () => {
    expect(
      partialDisplay(
        makeTrade({
          partialBreakdown: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)',
          exitType: 'TP3',
          exitPercentage: 1,
          pnl: 33,
        })
      )
    ).toBe('TP1: $33.00 (33%) | TP2: $66.00 (66%)');
  });

  it('formats exitType=TP1 with exitPercentage as "TP1 (33%): $X"', () => {
    expect(partialDisplay(makeTrade({ exitType: 'TP1', exitPercentage: 0.33, pnl: 33 }))).toBe(
      'TP1 (33%): $33.00'
    );
  });

  it('formats exitType=SL with exitPercentage as "SL (50%): $X"', () => {
    expect(partialDisplay(makeTrade({ exitType: 'SL', exitPercentage: 0.5, pnl: -50 }))).toBe(
      'SL (50%): $-50.00'
    );
  });

  it('formats exitType=MAX_BARS with exitPercentage as "Max Bars (100%): $X"', () => {
    expect(partialDisplay(makeTrade({ exitType: 'MAX_BARS', exitPercentage: 1, pnl: 0 }))).toBe(
      'Max Bars (100%): $0.00'
    );
  });

  it('accepts exitType variant STOP_LOSS (engine full-name), same as SL', () => {
    expect(partialDisplay(makeTrade({ exitType: 'STOP_LOSS', exitPercentage: 0.5, pnl: -50 }))).toBe(
      'SL (50%): $-50.00'
    );
  });

  it('uppercases lowercase exitType (engine emits inconsistent casing)', () => {
    expect(partialDisplay(makeTrade({ exitType: 'tp2', exitPercentage: 0.5, pnl: 50 }))).toBe(
      'TP2 (50%): $50.00'
    );
  });

  it('omits the (NN%) suffix when exitPercentage is 0 (not a partial — whole position)', () => {
    expect(partialDisplay(makeTrade({ exitType: 'SL', exitPercentage: 0, pnl: -100 }))).toBe(
      'SL: $-100.00'
    );
  });

  // === The BTC-39027 regression: missing exitType but exitPercentage present ===

  it('renders "Partial (33%): $X" when exitType is missing but exitPercentage > 0 (NOT "—")', () => {
    // The fix: previously this exact case bailed to '—' on line 104. With the
    // new fallback chain the percentage survives so the Partial % column
    // reflects the engine's actual partial-exit share.
    expect(
      partialDisplay(makeTrade({ exitType: undefined, exitPercentage: 0.33, pnl: 33 }))
    ).toBe('Partial (33%): $33.00');
  });

  it('renders "Partial (50%): $X" for an unlabeled 50% partial (SL partial missing exit_type)', () => {
    expect(
      partialDisplay(makeTrade({ exitType: undefined, exitPercentage: 0.5, pnl: -50 }))
    ).toBe('Partial (50%): $-50.00');
  });

  it('renders "Partial (100%): $X" for an unlabeled full-position exit (last leg of multi-exit)', () => {
    expect(
      partialDisplay(makeTrade({ exitType: undefined, exitPercentage: 1, pnl: 100 }))
    ).toBe('Partial (100%): $100.00');
  });

  it('still returns bare "—" when BOTH exitType and exitPercentage are missing (truly empty)', () => {
    // This is the only case where "—" is honest: the backend reported nothing.
    expect(partialDisplay(makeTrade({ exitType: undefined, exitPercentage: undefined }))).toBe('—');
    expect(partialDisplay(makeTrade({ exitType: '', exitPercentage: 0 }))).toBe('—');
  });

  it('falls back to "Partial (NN%): $X" for exitType values outside the TP/SL/MAX_BARS vocabulary', () => {
    // E.g. "PARTIAL_TRAILING" — engine added a new code that TradesPanel
    // doesn't know about yet. With the percentage we still render the partial share.
    expect(partialDisplay(makeTrade({ exitType: 'PARTIAL_TRAILING', exitPercentage: 0.4, pnl: 12 }))).toBe(
      'Partial (40%): $12.00'
    );
    // …but no percentage at all → "—" (nothing useful to say).
    expect(partialDisplay(makeTrade({ exitType: 'PARTIAL_TRAILING', exitPercentage: undefined }))).toBe('—');
  });
});
