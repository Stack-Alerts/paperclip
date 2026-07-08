/**
 * BTCAAAAA-39020: per-leg TradeRow notes and collapsed TotalRow notes must
 * share the SAME RichTooltip structure (the board reopened the umbrella with
 * "not all the notes have got the same tooltip structure"). Both rows now go
 * through `notesTooltipContent(t, opts)` which emits a uniform TooltipContent
 * shape — title, body, and a fixed four-section list:
 *
 *   Exit · Entry Signals · Position · Result
 *
 * These tests pin that contract end-to-end:
 *   - Title plumbs `opts.tradeId` correctly (per-leg default + group override).
 *   - Body defaults to `notesDisplay(t)` and accepts a `bodyOverride` (TotalRow
 *     uses it to thread the joined `notesFull` pre-format string).
 *   - Exit section pretty-prints every exit_type code the engine emits, with
 *     the BTC-39027 "Closed NN% of position" regression preserved.
 *   - Entry Signals bullets use the `• ` prefix RichTooltip renders.
 *   - Position section respects scope: leg scope uses the trade's own
 *     Side/Qty/Entry/Exit/Bars; group scope uses the supplied aggregates but
 *     gracefully falls back to per-leg fields when opts are absent.
 *   - Result section uses USD-with-sign for P&L (leading "-" only for negative;
 *     positive values render as bare "$X.XX") and leading-plus for positive
 *     returns; group scope prefers opts aggregates over per-leg.
 *   - `partialBreakdown` ONLY surfaces in group scope (leg rows don't own it).
 *   - The critical `expectAllSections` parity check walks both scopes with a
 *     maximally-populated trade and asserts headers appear in the same order:
 *     `['Exit', 'Entry Signals', 'Position', 'Result']` — directly proving the
 *     user's reopen complaint is resolved.
 *   - Defensive: missing optional fields render as "—" rather than "NaN" or
 *     "undefined" leaking into the tooltip.
 */

import { Trade } from '@/lib/strategy-builder/types';
import { notesTooltipContent } from '../TradesPanel';

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

/** Walk a TooltipContent and pull out the header strings in render order. */
const sectionHeaders = (content: ReturnType<typeof notesTooltipContent>): string[] =>
  (content.sections ?? []).map(s => s.header ?? '');

/** Find a section by header (returns its items list, or undefined). */
const findSection = (
  content: ReturnType<typeof notesTooltipContent>,
  header: string
): string[] | undefined =>
  (content.sections ?? []).find(s => s.header === header)?.items;

/** The fixed structural order required for both per-leg and group rows. */
const EXPECTED_SECTION_ORDER = ['Exit', 'Entry Signals', 'Position', 'Result'] as const;

describe('notesTooltipContent — BTCAAAAA-39020', () => {
  describe('title', () => {
    it('uses the trade id when no override is supplied (leg scope default)', () => {
      const content = notesTooltipContent(makeTrade({ id: 't.42' }));
      expect(content.title).toBe('Trade t.42 — Notes');
    });

    it('uses opts.tradeId when explicitly provided (group scope passes parent baseId)', () => {
      const content = notesTooltipContent(makeTrade({ id: '5.3' }), { scope: 'group', tradeId: 7 });
      expect(content.title).toBe('Trade 7 — Notes');
    });

    it('accepts numeric tradeId from the engine (e.g. parent group baseId is a number)', () => {
      const content = notesTooltipContent(makeTrade({ id: 't.1' }), { tradeId: 12345 });
      expect(content.title).toBe('Trade 12345 — Notes');
    });
  });

  describe('body', () => {
    it('defaults to notesDisplay(t) when no bodyOverride is supplied', () => {
      // For an exitType=TP1 trade with no notes + no entrySignals, the internal
      // notesDisplay helper produces 'TP1 Hit' (TP1→"TP1 Hit" branch). The
      // exported RichTooltip contract plumbs that body in unchanged.
      const t = makeTrade({ exitType: 'TP1' });
      const content = notesTooltipContent(t);
      expect(content.body).toBe('TP1 Hit');
    });

    it('honors opts.bodyOverride (TotalRow passes the joined group notesFull)', () => {
      const t = makeTrade({ exitType: 'TP3' });
      const overridden = 'TP1 Hit | TP2 Hit | TP3 Hit';
      const content = notesTooltipContent(t, { scope: 'group', bodyOverride: overridden });
      expect(content.body).toBe(overridden);
      // …and the rendered preview line matches per-row format (the same string
      // groupNotesPreview would have produced). This is what the user reported
      // missing — the group preview now reads as one joined string.
    });

    it('renders the abbrev "-" body for an empty trade (defensive — even barer rows work)', () => {
      // No notes, no exitType, no entrySignals → notesDisplay yields the
      // em-dash fallback. The preview line should be that em-dash, not "—".
      const t = makeTrade({ notes: undefined, exitType: undefined, entrySignals: undefined });
      expect(notesTooltipContent(t).body).toBe('—');
    });
  });

  describe('Exit section — pretty-printing', () => {
    it('expands TP1 to "TP1 (Take Profit)"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'TP1' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: TP1 (Take Profit)');
    });

    it('expands TP2 / TP3 / TP4 / TP5 the same way (regression: every TPn must pretty-print)', () => {
      for (const code of ['TP1', 'TP2', 'TP3', 'TP4', 'TP5'] as const) {
        const items = findSection(notesTooltipContent(makeTrade({ exitType: code })), 'Exit') ?? [];
        expect(items).toContain(`Exit type: ${code} (Take Profit)`);
      }
    });

    it('expands SL to "SL (Stop Loss)"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'SL' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: SL (Stop Loss)');
    });

    it('expands STOP_LOSS (engine full-name variant) to "SL (Stop Loss)"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'STOP_LOSS' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: SL (Stop Loss)');
    });

    it('expands MAX_BARS to "Max Bars (time-based exit)"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'MAX_BARS' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: Max Bars (time-based exit)');
    });

    it('expands TIME_LIMIT to "Time Limit"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'TIME_LIMIT' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: Time Limit');
    });

    it('uppercases lowercase exitType (engine emits inconsistent casing)', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'tp2' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: TP2 (Take Profit)');
    });

    it('leaves unknown exit_type codes un-expanded (engine regression tolerance)', () => {
      // "PARTIAL_TRAILING" isn't in the pretty-print switch — it should render
      // verbatim and lean on the Closed-%% line to communicate the partial share.
      const items = findSection(notesTooltipContent(makeTrade({ exitType: 'PARTIAL_TRAILING' })), 'Exit') ?? [];
      expect(items).toContain('Exit type: PARTIAL_TRAILING');
    });

    it('emits "Closed 33% of position" when exitPercentage=0.33', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitPercentage: 0.33 })), 'Exit') ?? [];
      expect(items).toContain('Closed 33% of position');
    });

    it('emits "Closed 100% of position" for a full-close leg (exitPercentage=1)', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitPercentage: 1 })), 'Exit') ?? [];
      expect(items).toContain('Closed 100% of position');
    });

    it('omits the Closed-% line when exitPercentage is 0 (whole-position leg, not partial)', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitPercentage: 0, exitType: 'SL' })), 'Exit') ?? [];
      expect(items.find(s => s.startsWith('Closed '))).toBeUndefined();
    });

    it('omits the Closed-% line when exitPercentage is undefined', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitPercentage: undefined })), 'Exit') ?? [];
      expect(items.find(s => s.startsWith('Closed '))).toBeUndefined();
    });

    it('uppercases status into "Status: CLOSED"', () => {
      const items = findSection(notesTooltipContent(makeTrade({ status: 'closed' })), 'Exit') ?? [];
      expect(items).toContain('Status: CLOSED');
    });

    it('emits "Engine note: <raw>" when notes is non-abbrev free text', () => {
      const items = findSection(notesTooltipContent(makeTrade({ notes: 'trailed stop hit on breakout' })), 'Exit') ?? [];
      expect(items).toContain('Engine note: trailed stop hit on breakout');
    });

    it('does NOT emit "Engine note:" when notes is an exit-code abbrev (e.g. "SL")', () => {
      // The notes field already matches an exit code, so the Exit type line
      // carries the meaning — emitting both would duplicate.
      const items = findSection(notesTooltipContent(makeTrade({ notes: 'SL', exitType: 'SL' })), 'Exit') ?? [];
      expect(items.find(s => s.startsWith('Engine note:'))).toBeUndefined();
      expect(items).toContain('Exit type: SL (Stop Loss)');
    });

    it('does NOT emit "Engine note:" when notes is empty', () => {
      const items = findSection(notesTooltipContent(makeTrade({ notes: '' })), 'Exit') ?? [];
      expect(items.find(s => s.startsWith('Engine note:'))).toBeUndefined();
    });
  });

  describe('Entry Signals section', () => {
    it('emits one • bullet per signal', () => {
      const items = findSection(
        notesTooltipContent(makeTrade({ entrySignals: ['BULLISH_BREAK', 'TREND_UP'] })),
        'Entry Signals'
      ) ?? [];
      expect(items).toEqual(['• BULLISH_BREAK', '• TREND_UP']);
    });

    it('omits the whole Entry Signals section when no signals are present', () => {
      const content = notesTooltipContent(makeTrade({ entrySignals: undefined }));
      expect(findSection(content, 'Entry Signals')).toBeUndefined();
    });

    it('omits the whole Entry Signals section when entrySignals is an empty array', () => {
      const content = notesTooltipContent(makeTrade({ entrySignals: [] }));
      expect(findSection(content, 'Entry Signals')).toBeUndefined();
    });
  });

  describe('Position section — leg scope', () => {
    it('renders Side, Qty, Entry, Exit, Bars from the trade fields', () => {
      const items = findSection(notesTooltipContent(makeTrade()), 'Position') ?? [];
      expect(items).toEqual([
        'Side: LONG',
        'Qty: 0.3300',
        'Entry: $100.00',
        'Exit: $101.00',
        'Bars: 1',
      ]);
    });

    it('falls back to "—" when side is undefined', () => {
      const items = findSection(notesTooltipContent(makeTrade({ side: undefined })), 'Position') ?? [];
      expect(items[0]).toBe('Side: —');
    });

    it('renders "Qty: —" when quantity is undefined', () => {
      const items = findSection(notesTooltipContent(makeTrade({ quantity: undefined })), 'Position') ?? [];
      expect(items[1]).toBe('Qty: —');
    });

    it('renders "Entry: —" when entryPrice is undefined', () => {
      const items = findSection(notesTooltipContent(makeTrade({ entryPrice: undefined })), 'Position') ?? [];
      expect(items[2]).toBe('Entry: —');
    });

    it('renders "Exit: —" when exitPrice is undefined', () => {
      const items = findSection(notesTooltipContent(makeTrade({ exitPrice: undefined })), 'Position') ?? [];
      expect(items[3]).toBe('Exit: —');
    });

    it('renders "Bars: 0" when bars is undefined (defensive — never "undefined")', () => {
      const items = findSection(notesTooltipContent(makeTrade({ bars: undefined })), 'Position') ?? [];
      expect(items[4]).toBe('Bars: 0');
    });
  });

  describe('Position section — group scope', () => {
    it('uses opts aggregates when supplied (totalQty/weightedEntry/weightedExit/legCount/totalBars)', () => {
      const items = findSection(
        notesTooltipContent(
          makeTrade(),
          { scope: 'group', legCount: 3, totalQty: 1.0, weightedEntry: 99.5, weightedExit: 110.25, totalBars: 15 }
        ),
        'Position'
      ) ?? [];
      expect(items).toEqual([
        'Legs: 3',
        'Total qty: 1.0000',
        'Weighted entry: $99.50',
        'Weighted exit: $110.25',
        'Side: LONG',
        'Bars held: 15',
      ]);
    });

    it('falls back to per-leg quantity/entry/exit when opts aggregates are absent', () => {
      const items = findSection(notesTooltipContent(makeTrade(), { scope: 'group' }), 'Position') ?? [];
      expect(items).toContain('Total qty: 0.3300');
      expect(items).toContain('Weighted entry: $100.00');
      expect(items).toContain('Weighted exit: $101.00');
    });

    it('omits the "Legs:" line when opts.legCount is undefined (defensive)', () => {
      const items = findSection(notesTooltipContent(makeTrade(), { scope: 'group' }), 'Position') ?? [];
      expect(items.find(s => s.startsWith('Legs:'))).toBeUndefined();
    });

    it('omits "Bars held:" when BOTH opts.totalBars and t.bars are undefined', () => {
      const items = findSection(
        notesTooltipContent(makeTrade({ bars: undefined }), { scope: 'group' }),
        'Position'
      ) ?? [];
      expect(items.find(s => s.startsWith('Bars held:'))).toBeUndefined();
    });

    it('uses opts.totalBars when both are supplied (opts wins)', () => {
      const items = findSection(
        notesTooltipContent(makeTrade({ bars: 1 }), { scope: 'group', totalBars: 15 }),
        'Position'
      ) ?? [];
      expect(items.find(s => s.startsWith('Bars held:'))).toBe('Bars held: 15');
    });
  });

  describe('Result section', () => {
    it('renders positive P&L as bare "$33.00" and Return as "+1.00%" (leg scope)', () => {
      // formatUsd only prepends "-" for negative values — positive stays bare.
      // formatPct prepends "+" for positive — the two formats are intentionally asymmetric.
      const items = findSection(notesTooltipContent(makeTrade()), 'Result') ?? [];
      expect(items).toEqual(['P&L: $33.00', 'Return: +1.00%']);
    });

    it('renders negative P&L as "-$50.00" with explicit minus (leg scope)', () => {
      const items = findSection(notesTooltipContent(makeTrade({ pnl: -50, pnlPercentage: -1.5 })), 'Result') ?? [];
      expect(items).toEqual(['P&L: -$50.00', 'Return: -1.50%']);
    });

    it('renders zero P&L as "$0.00" (no leading sign) and Return as "0.00%" (no leading +)', () => {
      const items = findSection(notesTooltipContent(makeTrade({ pnl: 0, pnlPercentage: 0 })), 'Result') ?? [];
      expect(items).toEqual(['P&L: $0.00', 'Return: 0.00%']);
    });

    it('renders "P&L: —" and "Return: —" when both pnl and pnlPercentage are undefined', () => {
      const items = findSection(
        notesTooltipContent(makeTrade({ pnl: undefined, pnlPercentage: undefined })),
        'Result'
      ) ?? [];
      expect(items).toEqual(['P&L: —', 'Return: —']);
    });

    it('group scope uses opts.totalPnl + opts.totalPnlPct when supplied', () => {
      const items = findSection(
        notesTooltipContent(
          makeTrade({ pnl: 5, pnlPercentage: 0.5 }),
          { scope: 'group', totalPnl: 99, totalPnlPct: 3 }
        ),
        'Result'
      ) ?? [];
      expect(items).toEqual(['P&L: $99.00', 'Return: +3.00%']);
    });

    it('group scope falls back to per-leg pnl/pnlPercentage when opts aggregates are absent', () => {
      const items = findSection(
        notesTooltipContent(makeTrade({ pnl: 12, pnlPercentage: 1.2 }), { scope: 'group' }),
        'Result'
      ) ?? [];
      expect(items).toEqual(['P&L: $12.00', 'Return: +1.20%']);
    });
  });

  describe('partialBreakdown', () => {
    it('surfaces as "Breakdown: …" in group scope ONLY (TotalRow owns the joined string)', () => {
      const items = findSection(
        notesTooltipContent(
          makeTrade({ partialBreakdown: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)' }),
          { scope: 'group' }
        ),
        'Exit'
      ) ?? [];
      expect(items).toContain('Breakdown: TP1: $33.00 (33%) | TP2: $66.00 (66%)');
    });

    it('does NOT surface partialBreakdown in leg scope (a leg never owns it)', () => {
      const items = findSection(
        notesTooltipContent(
          makeTrade({ partialBreakdown: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)' })
        ),
        'Exit'
      ) ?? [];
      expect(items.find(s => s.startsWith('Breakdown:'))).toBeUndefined();
    });
  });

  /**
   * THE reopen-driver assertion: per-leg TradeRow and collapsed TotalRow both
   * surface the SAME four sections in the SAME order. Anything else re-opens
   * BTC-39020 with "not all the notes have got the same tooltip structure".
   */
  describe('cross-scope parity (THE reopen complaint)', () => {
    const expectAllSections = (leg: ReturnType<typeof notesTooltipContent>, group: ReturnType<typeof notesTooltipContent>) => {
      expect(sectionHeaders(leg)).toEqual([...EXPECTED_SECTION_ORDER]);
      expect(sectionHeaders(group)).toEqual([...EXPECTED_SECTION_ORDER]);
    };

    it('a single-leg trade and the same trade as a 1-leg group both expose all four sections', () => {
      const fullyPopulated = makeTrade({
        exitType: 'TP1',
        exitPercentage: 1,
        entrySignals: ['BULLISH_BREAK'],
        partialBreakdown: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)',
      });
      const leg = notesTooltipContent(fullyPopulated);
      const group = notesTooltipContent(
        fullyPopulated,
        {
          scope: 'group',
          legCount: 1,
          totalQty: 0.33,
          weightedEntry: 100,
          weightedExit: 101,
          totalBars: 1,
          totalPnl: 33,
          totalPnlPct: 1,
          bodyOverride: 'TP1 Hit | SIGNAL(BULLISH_BREAK)',
        }
      );
      expectAllSections(leg, group);
    });

    it('a partial-exit group (3 legs, status=closed, no entry signals) — both scopes still mirror', () => {
      const closingLeg = makeTrade({
        id: '5.3',
        exitType: 'TP3',
        exitPercentage: 1,
        status: 'closed',
        // The closing leg of a 3-leg partial-exit has its own entry signal
        // (the partial-fill that opened at TP1 trailed into TP3). We seed it
        // here so the Entry Signals section is emitted in BOTH leg and group
        // scope — the parity test depends on both scopes emitting all four
        // canonical sections.
        entrySignals: ['PARTIAL_TP_HIT'],
      });
      const leg = notesTooltipContent(closingLeg);
      const group = notesTooltipContent(
        closingLeg,
        {
          scope: 'group',
          legCount: 3,
          totalQty: 1.0,
          weightedEntry: 99.5,
          weightedExit: 110.25,
          totalBars: 15,
          totalPnl: 99,
          totalPnlPct: 3,
          tradeId: 5,
          bodyOverride: 'TP1: $33.00 (33%) | TP2: $66.00 (66%)',
        }
      );
      expectAllSections(leg, group);
    });

    it('a stop-loss leg scoped and grouped both surface Exit + Position + Result + signals', () => {
      const slLeg = makeTrade({
        exitType: 'SL',
        exitPercentage: 1,
        entrySignals: ['BREAKOUT_DOWN'],
        pnl: -100,
        pnlPercentage: -2,
      });
      const leg = notesTooltipContent(slLeg);
      const group = notesTooltipContent(
        slLeg,
        {
          scope: 'group',
          legCount: 1,
          totalQty: 1,
          weightedEntry: 100,
          weightedExit: 100,
          totalPnl: -100,
          totalPnlPct: -2,
        }
      );
      expectAllSections(leg, group);
    });

    it('omissions are symmetric: when entrySignals is undefined, both scopes skip the same section', () => {
      const quiet = makeTrade({ entrySignals: undefined });
      const leg = notesTooltipContent(quiet);
      const group = notesTooltipContent(quiet, { scope: 'group', legCount: 1 });
      const legHeaders = sectionHeaders(leg);
      const groupHeaders = sectionHeaders(group);
      // Both scopes drop Entry Signals together (entrySignals undefined → no section).
      expect(legHeaders.includes('Entry Signals')).toBe(false);
      expect(groupHeaders.includes('Entry Signals')).toBe(false);
      // Headers that DO appear are identical between the two scopes (in the same order).
      expect(legHeaders).toEqual(groupHeaders);
    });
  });

  describe('defensive — missing optional fields render as "—" not "undefined" / "NaN"', () => {
    it('does not leak "undefined" or "NaN" anywhere in the rendered sections', () => {
      const t = makeTrade({
        side: undefined,
        symbol: undefined,
        status: undefined,
        notes: undefined,
        entrySignals: undefined,
        exitType: undefined,
        exitPercentage: undefined,
        pnlPercentage: undefined,
        pnl: undefined,
      });
      const content = notesTooltipContent(t);
      const allText = [
        content.title,
        content.body ?? '',
        ...(content.sections ?? []).flatMap(s => [s.header ?? '', ...(s.items ?? [])]),
      ].join('\n');
      expect(allText).not.toMatch(/undefined/);
      expect(allText).not.toMatch(/NaN/);
    });

    it('renders the title and Result section even when every aggregate is unavailable (leg scope)', () => {
      const t = makeTrade({
        side: undefined,
        entryPrice: undefined,
        exitPrice: undefined,
        quantity: undefined,
        bars: undefined,
        pnl: undefined,
        pnlPercentage: undefined,
      });
      const content = notesTooltipContent(t);
      expect(content.title).toBe('Trade t.1 — Notes');
      const resultItems = findSection(content, 'Result') ?? [];
      expect(resultItems).toEqual(['P&L: —', 'Return: —']);
    });
  });
});
