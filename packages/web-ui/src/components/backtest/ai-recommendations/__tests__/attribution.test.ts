/**
 * BTCAAAAA-38731: performance attribution for the analyze prompt.
 *
 * These tests pin the two attribution signals the analyze payload now carries:
 * per-entry vs reported metric divergence, and entry-signal / exit-type usage
 * with net-PnL attribution.
 */

import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { buildAttribution } from '../attribution';

function trade(over: Partial<Trade>): Trade {
  return {
    id: over.id ?? 't',
    entryTime: '2026-06-25T00:00:00.000Z',
    exitTime: '2026-06-25T01:00:00.000Z',
    entryPrice: 50000,
    exitPrice: 50500,
    quantity: 1,
    pnl: 0,
    pnlPercentage: 0,
    bars: 4,
    ...over,
  };
}

describe('buildAttribution', () => {
  it('returns null when there are no trades', () => {
    expect(buildAttribution({ trades: [] } as unknown as BacktestResult, null)).toBeNull();
    expect(buildAttribution(null, null)).toBeNull();
  });

  it('aggregates entry-signal usage with wins and net PnL, sorted by volume', () => {
    const result = {
      trades: [
        trade({ id: 'a', pnl: 100, entrySignals: ['BULLISH_BREAK'] }),
        trade({ id: 'b', pnl: -40, entrySignals: ['BULLISH_BREAK'] }),
        trade({ id: 'c', pnl: 25, entrySignals: ['RSI_OVERSOLD'] }),
      ],
    } as unknown as BacktestResult;

    const attr = buildAttribution(result, null);
    expect(attr).not.toBeNull();
    const usage = attr!.entry_signal_usage;
    expect(usage[0].signal).toBe('BULLISH_BREAK');
    expect(usage[0].entries).toBe(2);
    expect(usage[0].wins).toBe(1);
    expect(usage[0].win_rate_pct).toBe(50);
    expect(usage[0].net_pnl).toBe(60);
    expect(usage[1].signal).toBe('RSI_OVERSOLD');
    expect(usage[1].net_pnl).toBe(25);
  });

  it('maps an entry signal to its owning strategy block when the block declares it', () => {
    const strategy = {
      blocks: [
        {
          id: 'blk-1',
          type: 'ENTRY_CONDITION',
          index: 0,
          data: { name: 'Breakout Gate', signals: [{ name: 'BULLISH_BREAK' }] },
        },
      ],
    } as unknown as Strategy;
    const result = {
      trades: [trade({ id: 'a', pnl: 10, entrySignals: ['BULLISH_BREAK'] })],
    } as unknown as BacktestResult;

    const attr = buildAttribution(result, strategy);
    expect(attr!.entry_signal_usage[0].block).toBe('Breakout Gate');
  });

  it('aggregates exit-type usage, falling back to notes then unknown', () => {
    const result = {
      trades: [
        trade({ id: 'a', pnl: -30, exitType: 'Stop Loss Hit' }),
        trade({ id: 'b', pnl: -20, exitType: 'Stop Loss Hit' }),
        trade({ id: 'c', pnl: 50, notes: 'TP1 Hit' }),
        trade({ id: 'd', pnl: 5 }),
      ],
    } as unknown as BacktestResult;

    const attr = buildAttribution(result, null);
    const exits = attr!.exit_type_usage;
    expect(exits[0].exit_type).toBe('Stop Loss Hit');
    expect(exits[0].count).toBe(2);
    expect(exits[0].net_pnl).toBe(-50);
    expect(exits.map((e) => e.exit_type)).toContain('TP1 Hit');
    expect(exits.map((e) => e.exit_type)).toContain('unknown');
  });

  it('surfaces metric divergence rows from the diagnose table', () => {
    const result = {
      totalTrades: 2,
      winRate: 0.5,
      trades: [trade({ id: 'a', pnl: 10 }), trade({ id: 'b', pnl: -10 })],
    } as unknown as BacktestResult;

    const attr = buildAttribution(result, null);
    expect(attr!.metric_divergence.map((m) => m.metric)).toEqual(
      expect.arrayContaining(['Profit factor', 'Win rate', 'Entries']),
    );
  });
});
