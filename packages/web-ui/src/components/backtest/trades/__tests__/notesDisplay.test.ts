/**
 * BTCAAAAA-39062: surface the engine's `partial_exit` bool as a "(partial)"
 * suffix in the per-leg NOTES cell so users can see at-a-glance whether a
 * leg fully closed the parent position or only partially. Mirrors
 * `partial_size` / `partial_exit_breakdown` already forwarded by BTC-39058.
 *
 * The fix is one line of pure logic at the bottom of `notesDisplay`:
 *
 *   if (t.partialExit === true && exitNote !== '—') {
 *     exitNote = `${exitNote} (partial)`;
 *   }
 *
 * Verified end-to-end contract:
 *   1. Partial-exit legs of EVERY supported exit kind (TP1/TP2/TP3, SL,
 *      STOP_LOSS, MAX_BARS, TIME_LIMIT) get the ` (partial)` suffix.
 *   2. Single-leg full closes AND the closing leg of a multi-leg group
 *      (engine sets `partial_exit: False` for both) render with the bare
 *      copy — no suffix.
 *   3. The suffix is placed BEFORE the entry-signal concatenation, so the
 *      canonical shape stays uniform: `<exit> (partial) | SIGNAL(...)`.
 *   4. Non-abbrev `notes` (engine free text) pass through unchanged when
 *      `partialExit` is true — gets ` (partial)` appended.
 *   5. Defensive: missing `partialExit` (legacy rows from before this fix)
 *      and `partialExit: false` both produce bare copy — no accidental
 *      suffix on old data.
 *   6. Defensive: bare em-dash fallback (truly empty trade) does NOT get
 *      the suffix — "—" stays "—".
 */

import { Trade } from '@/lib/strategy-builder/types';
import { notesDisplay } from '../TradesPanel';

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

describe('notesDisplay — BTCAAAAA-39062 (partial exit suffix)', () => {
  // === THE core fix: partial SL leg ===

  it('appends "(partial)" to a partial SL leg (the explicit wake example)', () => {
    expect(notesDisplay(makeTrade({ exitType: 'SL', partialExit: true }))).toBe(
      'Stop Loss Hit (partial)'
    );
  });

  it('appends "(partial)" to a partial STOP_LOSS leg (engine full-name variant)', () => {
    // Engine emits both "SL" and "STOP_LOSS" depending on the calling path;
    // the suffix must apply to both.
    expect(notesDisplay(makeTrade({ exitType: 'STOP_LOSS', partialExit: true }))).toBe(
      'Stop Loss Hit (partial)'
    );
  });

  it('appends "(partial)" to a partial TP1 leg', () => {
    expect(notesDisplay(makeTrade({ exitType: 'TP1', partialExit: true }))).toBe(
      'TP1 Hit (partial)'
    );
  });

  it('appends "(partial)" to a partial TP2 leg (regression: every TPn gets the suffix)', () => {
    expect(notesDisplay(makeTrade({ exitType: 'TP2', partialExit: true }))).toBe(
      'TP2 Hit (partial)'
    );
  });

  it('appends "(partial)" to a partial TP3 leg (closing leg of a 3-leg group)', () => {
    expect(notesDisplay(makeTrade({ exitType: 'TP3', partialExit: true }))).toBe(
      'TP3 Hit (partial)'
    );
  });

  it('appends "(partial)" to a partial MAX_BARS leg (time-based exit)', () => {
    expect(
      notesDisplay(makeTrade({ exitType: 'MAX_BARS', partialExit: true, bars: 12 }))
    ).toBe('Max Hold Time (12 bars) (partial)');
  });

  it('appends "(partial)" to a partial TIME_LIMIT leg (engine full-name variant)', () => {
    expect(
      notesDisplay(makeTrade({ exitType: 'TIME_LIMIT', partialExit: true, bars: 50 }))
    ).toBe('Max Hold Time (50 bars) (partial)');
  });

  // === Full close / closing leg: bare copy (no suffix) ===

  it('returns bare "Stop Loss Hit" when partialExit=false (full single-leg close)', () => {
    // The wake explicitly accepts "(or just X if it was the only/closing leg)".
    // Engine sets `partial_exit: False` for both single-leg closes and the
    // chronological closing leg of a multi-leg group, so we cannot distinguish
    // them in the per-row helper — the bare copy is the correct fallback.
    expect(notesDisplay(makeTrade({ exitType: 'SL', partialExit: false }))).toBe(
      'Stop Loss Hit'
    );
  });

  it('returns bare "TP3 Hit" when partialExit=false (closing leg of multi-leg group)', () => {
    expect(notesDisplay(makeTrade({ exitType: 'TP3', partialExit: false }))).toBe('TP3 Hit');
  });

  it('returns bare "Max Hold Time (N bars)" when partialExit=false', () => {
    expect(
      notesDisplay(makeTrade({ exitType: 'MAX_BARS', partialExit: false, bars: 8 }))
    ).toBe('Max Hold Time (8 bars)');
  });

  // === Legacy rows (pre-fix, no partialExit field) ===

  it('returns bare copy when partialExit is undefined (legacy rows from before the fix)', () => {
    // Old trades from the API before BTC-39062 land with no `partialExit`
    // field at all. They must render unchanged — the strict `=== true` guard
    // is what prevents accidental suffixing here.
    expect(notesDisplay(makeTrade({ exitType: 'SL' }))).toBe('Stop Loss Hit');
    expect(notesDisplay(makeTrade({ exitType: 'TP1' }))).toBe('TP1 Hit');
    expect(notesDisplay(makeTrade({ exitType: 'MAX_BARS', bars: 3 }))).toBe(
      'Max Hold Time (3 bars)'
    );
  });

  // === Defensive: em-dash fallback does NOT get the suffix ===

  it('does NOT append "(partial)" to the em-dash fallback (truly empty trade)', () => {
    // No notes, no exitType, but partialExit=true (engine would never emit
    // this combination, but if it did the row is genuinely empty and the
    // em-dash must stay as-is — the suffix would be meaningless noise).
    expect(
      notesDisplay(makeTrade({ notes: undefined, exitType: undefined, partialExit: true }))
    ).toBe('—');
  });

  // === Non-abbrev notes (engine free text) — pass-through with suffix ===

  it('appends "(partial)" to a non-abbrev free-text note (e.g. "trailed stop hit")', () => {
    // Engine can emit a free-text note instead of a code. The note is
    // preserved verbatim and gets the "(partial)" suffix appended.
    expect(
      notesDisplay(
        makeTrade({ notes: 'trailed stop hit on breakout', partialExit: true })
      )
    ).toBe('trailed stop hit on breakout (partial)');
  });

  it('returns non-abbrev free-text note bare when partialExit is false', () => {
    expect(
      notesDisplay(makeTrade({ notes: 'trailed stop hit on breakout' }))
    ).toBe('trailed stop hit on breakout');
  });

  // === Entry-signal concatenation: suffix comes BEFORE the SIGNAL pipe ===

  it('places "(partial)" BEFORE the entry-signal concatenation (canonical shape)', () => {
    // The wake's contract requires "<exit> (partial) | SIGNAL(...)" so the
    // shape stays uniform across all four exit kinds. The suffix must come
    // before the pipe, not after the signal list.
    expect(
      notesDisplay(
        makeTrade({
          exitType: 'SL',
          partialExit: true,
          entrySignals: ['BULLISH_BREAK'],
        })
      )
    ).toBe('Stop Loss Hit (partial) | SIGNAL(BULLISH_BREAK)');
  });

  it('joins multiple entry signals with commas after the "(partial)" suffix', () => {
    expect(
      notesDisplay(
        makeTrade({
          exitType: 'TP1',
          partialExit: true,
          entrySignals: ['BULLISH_BREAK', 'TREND_UP'],
        })
      )
    ).toBe('TP1 Hit (partial) | SIGNAL(BULLISH_BREAK), SIGNAL(TREND_UP)');
  });

  it('does NOT append "(partial)" before the signal pipe when partialExit is false (regression)', () => {
    // The full-close leg of a multi-leg group has entrySignals but no
    // partialExit. The bare copy with the signal pipe still applies.
    expect(
      notesDisplay(
        makeTrade({
          exitType: 'TP3',
          partialExit: false,
          entrySignals: ['BULLISH_BREAK'],
        })
      )
    ).toBe('TP3 Hit | SIGNAL(BULLISH_BREAK)');
  });

  it('handles signals on the em-dash fallback (still no "(partial)" suffix, signals-only)', () => {
    // Defensive: an em-dash exitNote with signals still emits just the
    // signal pipe — the suffix never applies to the em-dash, even when
    // partialExit is true. This is the same defensive guard as the no-
    // signal case above.
    expect(
      notesDisplay(
        makeTrade({
          notes: undefined,
          exitType: undefined,
          partialExit: true,
          entrySignals: ['BULLISH_BREAK'],
        })
      )
    ).toBe('SIGNAL(BULLISH_BREAK)');
  });

  // === Casing / engine quirks ===

  it('uppercases lowercase exitType before applying the "(partial)" suffix', () => {
    // Engine emits inconsistent casing — the suffix must still apply after
    // the upper-cased pretty-print.
    expect(notesDisplay(makeTrade({ exitType: 'sl', partialExit: true }))).toBe(
      'Stop Loss Hit (partial)'
    );
    expect(notesDisplay(makeTrade({ exitType: 'tp2', partialExit: true }))).toBe(
      'TP2 Hit (partial)'
    );
  });

  it('still emits the "(partial)" suffix when `notes` is an abbrev code (e.g. notes="SL", partialExit=true)', () => {
    // The exitType lookup falls back to rawNotes when exitType is absent;
    // the suffix must still apply on the resolved pretty-print.
    expect(notesDisplay(makeTrade({ notes: 'SL', exitType: undefined, partialExit: true }))).toBe(
      'Stop Loss Hit (partial)'
    );
  });
});
