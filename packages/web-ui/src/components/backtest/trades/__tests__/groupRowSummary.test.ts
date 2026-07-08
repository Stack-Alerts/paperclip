/**
 * BTCAAAAA-39020: collapsed-view Total row used to render a single
 * `<td colSpan={7}>` spanning Date/Time, Symbol, Side, Size, Entry, Exit, and
 * Duration with only "{N} partial exits (collapsed)" text — leaving six of the
 * seven columns visually empty. These helpers feed those cells so the totals
 * row mirrors the same per-row shape TradeRow renders (entry time from first
 * leg, total quantity sum, closing-leg exit price, total duration, etc.).
 *
 * Acceptance criteria (per the wake payload + the BTC-39020 sibling of the
 * BTC-39028 collapsed-totals fix):
 *   - DATE/TIME  → first leg's entryTime (every leg of the same parent shares
 *                  the entry bar, so first-leg is canonical).
 *   - SYMBOL     → first leg's symbol, defaulting to BTC.P/USDT when absent.
 *   - SIDE       → first leg's side, normalized via normalizeSide (LONG/SHORT/—).
 *   - SIZE       → sum of every leg's quantity (gross parent position size).
 *   - ENTRY      → first leg's entryPrice (parent entry price).
 *   - EXIT       → CLOSING leg's exitPrice (last leg by exit-time order).
 *   - DURATION   → sum of every leg's `bars` (total bars held across legs).
 *
 * Single-trade groups skip TotalRow entirely at the rendering layer
 * (`group.trades.length > 1` guard), so this helper is only ever called with
 * 2+ legs — but the tests still cover the 1-trade and 0-trade edge cases so
 * the helper behaves defensively if the guard ever changes.
 */

import { Trade } from '@/lib/strategy-builder/types';
import { groupRowSummary } from '../TradesPanel';

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

describe('groupRowSummary — BTCAAAAA-39020', () => {
  it('returns entryTime from the FIRST leg (canonical parent entry bar)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-01T01:00:00Z' }),
      makeTrade({ id: '5.2', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-02T01:00:00Z' }),
      makeTrade({ id: '5.3', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-03T01:00:00Z' }),
    ];
    expect(groupRowSummary(legs).entryTime).toBe('2026-01-01T00:00:00Z');
  });

  it('returns exitPrice from the CLOSING leg (last leg by exit-time order), not the first', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-01T01:00:00Z', exitPrice: 101 }),
      makeTrade({ id: '5.2', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-02T01:00:00Z', exitPrice: 105 }),
      makeTrade({ id: '5.3', entryTime: '2026-01-01T00:00:00Z', exitTime: '2026-01-03T01:00:00Z', exitPrice: 110 }),
    ];
    const summary = groupRowSummary(legs);
    expect(summary.exitPrice).toBe(110);
  });

  it('returns entryPrice from the first leg (all legs share the parent entry)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryPrice: 100, exitPrice: 101 }),
      makeTrade({ id: '5.2', entryPrice: 100, exitPrice: 105 }),
    ];
    expect(groupRowSummary(legs).entryPrice).toBe(100);
  });

  it('sums quantities across all legs (gross parent position size)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', quantity: 0.33 }),
      makeTrade({ id: '5.2', quantity: 0.33 }),
      makeTrade({ id: '5.3', quantity: 0.34 }),
    ];
    // Total = 1.0 BTC-equivalent across TP1/TP2/TP3 at 33/33/34% splits.
    expect(groupRowSummary(legs).totalQty).toBeCloseTo(1.0, 6);
  });

  it('sums bars across all legs (total bars held across partial exits)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', bars: 5 }),
      makeTrade({ id: '5.2', bars: 3 }),
      makeTrade({ id: '5.3', bars: 7 }),
    ];
    // Total = 15 bars across the three legs.
    expect(groupRowSummary(legs).totalBars).toBe(15);
  });

  it('preserves the first-leg symbol', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', symbol: 'ETH/USDT' }),
      makeTrade({ id: '5.2', symbol: 'ETH/USDT' }),
    ];
    expect(groupRowSummary(legs).symbol).toBe('ETH/USDT');
  });

  it('defaults symbol to BTC.P/USDT when the engine omits it', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1' }),
      makeTrade({ id: '5.2' }),
    ];
    expect(groupRowSummary(legs).symbol).toBe('BTC.P/USDT');
  });

  it('normalizes side strings via normalizeSide (LONG preserved)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', side: 'LONG' }),
      makeTrade({ id: '5.2', side: 'LONG' }),
    ];
    expect(groupRowSummary(legs).side).toBe('LONG');
  });

  it('normalizes side strings via normalizeSide (SHORT preserved)', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', side: 'SHORT' }),
      makeTrade({ id: '5.2', side: 'SHORT' }),
    ];
    expect(groupRowSummary(legs).side).toBe('SHORT');
  });

  it('normalizes lowercase side strings from the engine', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', side: 'short' }),
      makeTrade({ id: '5.2', side: 'short' }),
    ];
    expect(groupRowSummary(legs).side).toBe('SHORT');
  });

  it('returns "—" for side when first leg has no side field', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', side: undefined }),
      makeTrade({ id: '5.2', side: undefined }),
    ];
    expect(groupRowSummary(legs).side).toBe('—');
  });

  it('uses the first leg for entryPrice even when later legs differ (defensive)', () => {
    // Engine should never emit differing entryPrices within the same parent
    // group, but if it does we want the FIRST leg's value (parent fill price).
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryPrice: 100, exitPrice: 101 }),
      makeTrade({ id: '5.2', entryPrice: 999, exitPrice: 105 }),
    ];
    expect(groupRowSummary(legs).entryPrice).toBe(100);
  });

  it('falls back to 0 for entryPrice when the first leg is missing the field', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryPrice: undefined, exitPrice: 101 }),
      makeTrade({ id: '5.2', entryPrice: 100, exitPrice: 105 }),
    ];
    // entryPrice undefined becomes 0; TotalRow renders '—' via the `> 0 ? ... : '—'` guard.
    expect(groupRowSummary(legs).entryPrice).toBe(0);
  });

  it('falls back to 0 for exitPrice when the closing leg is missing the field', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryPrice: 100, exitPrice: 101 }),
      makeTrade({ id: '5.2', entryPrice: 100, exitPrice: undefined }),
    ];
    // exitPrice undefined becomes 0; TotalRow renders '—' via the `> 0 ? ... : '—'` guard.
    expect(groupRowSummary(legs).exitPrice).toBe(0);
  });

  it('sums bars across legs and treats undefined bars as 0', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', bars: undefined }),
      makeTrade({ id: '5.2', bars: 4 }),
      makeTrade({ id: '5.3', bars: 6 }),
    ];
    expect(groupRowSummary(legs).totalBars).toBe(10);
  });

  it('sums quantities and treats undefined quantity as 0', () => {
    const legs: Trade[] = [
      makeTrade({ id: '5.1', quantity: undefined }),
      makeTrade({ id: '5.2', quantity: 0.5 }),
      makeTrade({ id: '5.3', quantity: 0.25 }),
    ];
    expect(groupRowSummary(legs).totalQty).toBeCloseTo(0.75, 6);
  });

  it('returns an empty/zero-filled row for an empty legs array (defensive)', () => {
    const summary = groupRowSummary([]);
    expect(summary.entryTime).toBe('');
    expect(summary.symbol).toBe('BTC.P/USDT');
    expect(summary.side).toBe('—');
    expect(summary.totalQty).toBe(0);
    expect(summary.entryPrice).toBe(0);
    expect(summary.exitPrice).toBe(0);
    expect(summary.totalBars).toBe(0);
  });

  it('returns first-leg primitives for a single-leg group (defensive, never rendered)', () => {
    // TotalRow is gated by `group.trades.length > 1`, but the helper must still
    // produce sane values if the guard changes.
    const legs: Trade[] = [
      makeTrade({ id: '5.1', entryTime: '2026-02-01T00:00:00Z', entryPrice: 50, exitPrice: 55 }),
    ];
    const summary = groupRowSummary(legs);
    expect(summary.entryTime).toBe('2026-02-01T00:00:00Z');
    expect(summary.entryPrice).toBe(50);
    expect(summary.exitPrice).toBe(55);
    expect(summary.totalQty).toBeCloseTo(0.33, 6);
    expect(summary.totalBars).toBe(1);
  });
});