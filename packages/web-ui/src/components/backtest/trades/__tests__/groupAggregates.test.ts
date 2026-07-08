/**
 * BTCAAAAA-39028: collapsed-view Total row used to render literal '—' for
 * STATUS, PARTIAL %, and NOTES regardless of the group's actual data, leaving
 * the totals row uninformative. These helpers feed the Total row so it shows
 * the same shape of group aggregates the thick client renders, and the NOTES
 * cell gets a hover-expand via BTC-39021's institutional tooltip.
 *
 * Acceptance criteria (per the wake payload):
 *   - STATUS  → group's effective status (OPEN if any leg open, PARTIAL if
 *               partials + not all closed, otherwise the closing leg's status).
 *   - PARTIAL % → count of legs in the group (e.g. "3 partials").
 *   - NOTES  → first 3-5 words of the closing leg's notesDisplay() + "…",
 *              with full text on hover via RichTooltip (BTC-39021).
 *
 * Single-trade groups skip TotalRow entirely at the rendering layer
 * (`group.trades.length > 1` guard in TradesPanel.tsx), so these helpers are
 * only ever called with 2+ legs — but the tests still cover the 1-trade edge
 * case so the helpers behave defensively if the guard ever changes.
 */

import { Trade } from '@/lib/strategy-builder/types';
import {
  groupEffectiveStatus,
  groupPartialCount,
  groupNotesPreview,
} from '../TradesPanel';

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

describe('groupEffectiveStatus — BTCAAAAA-39028', () => {
  it('returns OPEN when any leg is open (group not yet fully exited)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', status: 'CLOSED', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', status: 'OPEN',    exitTime: '2026-01-02T01:00:00Z' }),
      makeTrade({ id: '5.3', status: 'CLOSED', exitTime: '2026-01-03T01:00:00Z' }),
    ];
    expect(groupEffectiveStatus(legs)).toBe('OPEN');
  });

  it('returns PARTIAL when some legs are partial and not all closed', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', status: 'CLOSED', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', status: 'PARTIAL', exitTime: '2026-01-02T01:00:00Z' }),
    ];
    expect(groupEffectiveStatus(legs)).toBe('PARTIAL');
  });

  it('returns CLOSED when every leg is closed (2-leg TP1+TP2 trade)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', status: 'CLOSED', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', status: 'CLOSED', exitTime: '2026-01-02T01:00:00Z' }),
    ];
    expect(groupEffectiveStatus(legs)).toBe('CLOSED');
  });

  it('returns CLOSED when every leg is closed (3-leg TP1+TP2+TP3 trade)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', status: 'CLOSED', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', status: 'CLOSED', exitTime: '2026-01-02T01:00:00Z' }),
      makeTrade({ id: '5.3', status: 'CLOSED', exitTime: '2026-01-03T01:00:00Z' }),
    ];
    expect(groupEffectiveStatus(legs)).toBe('CLOSED');
  });

  it('returns CLOSED for a single CLOSED trade (defensive — TotalRow skips single-trade groups)', () => {
    expect(groupEffectiveStatus([makeTrade({ status: 'CLOSED' })])).toBe('CLOSED');
  });

  it('returns CLOSED for an empty array (defensive — should never happen at render time)', () => {
    expect(groupEffectiveStatus([])).toBe('CLOSED');
  });

  it('normalizes lowercase status strings from the engine', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', status: 'closed', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', status: 'open',   exitTime: '2026-01-02T01:00:00Z' }),
    ];
    expect(groupEffectiveStatus(legs)).toBe('OPEN');
  });
});

describe('groupPartialCount — BTCAAAAA-39028', () => {
  it('returns "3 partials" for a 3-leg group', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1' }),
      makeTrade({ id: '5.2' }),
      makeTrade({ id: '5.3' }),
    ];
    expect(groupPartialCount(legs)).toBe('3 partials');
  });

  it('returns "2 partials" for a 2-leg group (TP1+TP2)', () => {
    const legs: Trade[] = [makeTrade({ id: '5.1' }), makeTrade({ id: '5.2' })];
    expect(groupPartialCount(legs)).toBe('2 partials');
  });

  it('returns "0 partials" for an empty group (defensive)', () => {
    expect(groupPartialCount([])).toBe('0 partials');
  });

  it('returns "1 partial" for a single trade (defensive — TotalRow skips these)', () => {
    expect(groupPartialCount([makeTrade()])).toBe('1 partial');
  });
});

describe('groupNotesPreview — BTCAAAAA-39028', () => {
  it('returns a truncated preview + full text for the closing leg', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', exitType: 'TP1', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({
        id: '5.2',
        exitType: 'TP2',
        exitTime: '2026-01-02T01:00:00Z',
        notes: 'TP2 Hit — second target reached after TP1 confirmed momentum',
        entrySignals: ['BULLISH_BREAK'],
      }),
    ];
    const { preview, full } = groupNotesPreview(legs);
    // Preview should be a few words + ellipsis, not the full sentence.
    expect(preview.endsWith('…')).toBe(true);
    expect(preview.length).toBeLessThan(full.length);
    // Full should contain the full notesDisplay output for the closing leg,
    // including any entry-signal annotation appended by notesDisplay().
    expect(full).toContain('TP2 Hit');
    expect(full).toContain('SIGNAL(BULLISH_BREAK)');
  });

  it('uses the LAST leg (closing leg) for the notes — not the first', () => {
    // 3-leg group: only the last leg has notes. If we accidentally picked the
    // first leg, the preview/full would be based on TP1, not TP3.
    const legs: Trade[] = [
      makeTrade({ id: '5.1', exitType: 'TP1', exitTime: '2026-01-01T01:00:00Z', notes: 'TP1' }),
      makeTrade({ id: '5.2', exitType: 'TP2', exitTime: '2026-01-02T01:00:00Z', notes: 'TP2' }),
      makeTrade({
        id: '5.3',
        exitType: 'TP3',
        exitTime: '2026-01-03T01:00:00Z',
        notes: 'TP3 Hit',
      }),
    ];
    const { full } = groupNotesPreview(legs);
    expect(full).toContain('TP3');
    expect(full).not.toContain('TP2 Hit');
    expect(full).not.toContain('TP1');
  });

  it('returns "—" for preview and "" for full when no leg has notes', () => {
    // Engine emits TP exit codes via exitType, not notes; notesDisplay()
    // expands those into "TP1 Hit" / "Stop Loss Hit" etc., so the helper
    // should still produce a non-empty full text in that case. This test
    // covers the truly-empty path: no notes AND no exitType.
    const legs: Trade[] = [
      makeTrade({ id: '5.1', notes: undefined, exitType: undefined }),
      makeTrade({ id: '5.2', notes: undefined, exitType: undefined }),
    ];
    const { preview, full } = groupNotesPreview(legs);
    expect(preview).toBe('—');
    expect(full).toBe('');
  });

  it('returns a preview of approximately 3-5 words before the ellipsis', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({
        id: '5.2',
        exitTime: '2026-01-02T01:00:00Z',
        notes: 'alpha beta gamma delta epsilon zeta eta theta',
      }),
    ];
    const { preview } = groupNotesPreview(legs);
    // Strip the trailing ellipsis, then count words.
    const wordCount = preview.replace(/…$/, '').trim().split(/\s+/).length;
    expect(wordCount).toBeGreaterThanOrEqual(3);
    expect(wordCount).toBeLessThanOrEqual(5);
  });

  it('returns a defensive "—" preview for an empty group (should not happen at render)', () => {
    expect(groupNotesPreview([])).toEqual({ preview: '—', full: '' });
  });
});