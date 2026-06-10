import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { LiveOutputPanel } from '@/components/backtest/live-output/LiveOutputPanel';
import type { BacktestResult, BacktestStatusMessage } from '@/lib/strategy-builder/types';

function makeResult(overrides: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: 'r1',
    strategyId: 's1',
    runId: 'r1',
    status: 'completed',
    startDate: '2026-01-01',
    endDate: '2026-02-01',
    initialCapital: 10000,
    finalCapital: 11000,
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalReturn: 0,
    returnPercentage: 0,
    maxDrawdown: 0,
    sharpeRatio: 0,
    sortino_ratio: 0,
    profitFactor: 0,
    averageWin: 0,
    averageLoss: 0,
    trades: [],
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

// Cycle-13 board revision 2026-06-03: the idle Status checklist lives on
// the Config tab; Live Output keeps its separate streaming role + run
// counters. These tests lock that contract.
describe('LiveOutputPanel — streaming output + run counters (cycle-13)', () => {
  it('shows the natural "no output yet" placeholder when idle (no idle checklist)', () => {
    render(<LiveOutputPanel logs={[]} isRunning={false} />);
    expect(screen.getByText(/No output yet/)).toBeInTheDocument();
    expect(screen.queryByText(/Status updates will appear here when backtest starts/)).toBeNull();
    expect(screen.queryByText(/Data loading progress from Unified Data Manager/)).toBeNull();
  });

  it('tallies TP/SL adjustments from completed trades in the header counter row', () => {
    const result = makeResult({
      totalTrades: 4,
      trades: [
        { id: 't1', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP1' },
        { id: 't2', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'TP2' },
        { id: 't3', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'SL' },
        { id: 't4', entryTime: '', exitTime: '', entryPrice: 0, exitPrice: 0, quantity: 0, pnl: 0, pnlPercentage: 0, bars: 0, exitType: 'SL' },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    expect(screen.getByText('(TP1: 1, TP2: 1, TP3: 0, SL: 2)')).toBeInTheDocument();
  });

  it('streams log lines when active', () => {
    const logs: BacktestStatusMessage[] = [
      { message: 'Loading bars from Binance…', level: 'SYSTEM', timestamp: '2026-06-03T10:15:23Z' },
    ];
    render(<LiveOutputPanel logs={logs} isRunning={true} />);
    expect(screen.getByText(/Loading bars from Binance/)).toBeInTheDocument();
    expect(screen.getByText(/RUNNING/)).toBeInTheDocument();
  });
});

// BTCAAAAA-33591 cycle-33: per-trade synthesis safety net (frontend side).
describe('LiveOutputPanel — per-trade synthesis (cycle-33, BTCAAAAA-33591)', () => {
  it('synthesizes ORDER / FILL / POSITION / PERFORMANCE lines from a result with trades', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't1',
          entryTime: '2026-01-01T10:00:00Z',
          exitTime: '2026-01-01T11:00:00Z',
          entryPrice: 100,
          exitPrice: 110,
          quantity: 1,
          pnl: 10,
          pnlPercentage: 10,
          bars: 4,
          exitType: 'TP1',
          side: 'LONG',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    expect(screen.getByText(/ORDER #1:.*LONG.*1.*BTC\.P\/USDT.*BUY @ 100\.00/)).toBeInTheDocument();
    expect(screen.getByText(/BUY FILL #1:.*1.*BTC\.P\/USDT @ 100\.00/)).toBeInTheDocument();
    expect(screen.getByText(/POSITION OPEN #1:.*LONG.*1.*BTC\.P\/USDT @ 100\.00 \| bars=4/)).toBeInTheDocument();
    expect(screen.getByText(/PERFORMANCE #1:.*WIN.*TP1.*110\.00.*Total PnL: \$10\.00.*10\.00%.*bars=4/)).toBeInTheDocument();
  });

  it('renders SELL FILL (not BUY FILL) for SHORT trades', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't2',
          entryTime: '2026-01-01T10:00:00Z',
          exitTime: '2026-01-01T11:00:00Z',
          entryPrice: 100,
          exitPrice: 90,
          quantity: 1,
          pnl: -10,
          pnlPercentage: -10,
          bars: 4,
          exitType: 'SL',
          side: 'SHORT',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    render(<LiveOutputPanel logs={[]} isRunning={false} result={result} />);
    expect(screen.getByText(/SELL FILL #1:.*1.*BTC\.P\/USDT @ 100\.00/)).toBeInTheDocument();
    expect(screen.queryByText(/BUY FILL #1:/)).toBeNull();
    expect(screen.getByText(/PERFORMANCE #1:.*LOSS/)).toBeInTheDocument();
  });

  it('skips synthesis when the backend log uses ORDER/PERFORMANCE format (no double-accounting)', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't_order',
          entryTime: '2026-01-01T10:00:00Z',
          exitTime: '2026-01-01T11:00:00Z',
          entryPrice: 100,
          exitPrice: 110,
          quantity: 1,
          pnl: 10,
          pnlPercentage: 10,
          bars: 4,
          exitType: 'TP1',
          side: 'LONG',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    const logs: BacktestStatusMessage[] = [
      { message: 'ORDER #1: LONG 1 BTC.P/USDT BUY @ 100.00', level: 'INFO', timestamp: '2026-01-01T10:00:00Z' },
      { message: 'BUY FILL #1: 1 BTC.P/USDT @ 100.00', level: 'INFO', timestamp: '2026-01-01T10:00:01Z' },
      { message: 'POSITION OPEN #1: LONG 1 BTC.P/USDT @ 100.00 | bars=4', level: 'INFO', timestamp: '2026-01-01T10:00:02Z' },
      { message: 'PERFORMANCE #1: WIN | TP1 @ 110.00 | Total PnL: $10.00 (10.00%) | bars=4', level: 'INFO', timestamp: '2026-01-01T11:00:00Z' },
    ];
    render(<LiveOutputPanel logs={logs} isRunning={false} result={result} />);
    expect(screen.getAllByText(/ORDER #1:/).length).toBe(1);
    expect(screen.getAllByText(/PERFORMANCE #1:/).length).toBe(1);
  });

  it('skips synthesis when the backend log already covers each trade (Entry/Exit present)', () => {
    const result = makeResult({
      totalTrades: 1,
      trades: [
        {
          id: 't3',
          entryTime: '',
          exitTime: '',
          entryPrice: 100,
          exitPrice: 110,
          quantity: 1,
          pnl: 10,
          pnlPercentage: 10,
          bars: 4,
          exitType: 'TP1',
          side: 'LONG',
          symbol: 'BTC.P/USDT',
        },
      ],
    });
    const logs: BacktestStatusMessage[] = [
      { message: 'Entry #1: LONG @ 100.00', level: 'INFO', timestamp: '2026-01-01T10:00:00Z' },
      { message: 'Exit #1: WIN | TP1 @ 110.00 | PnL: $10.00 (10.00%) | Bars: 4', level: 'INFO', timestamp: '2026-01-01T11:00:00Z' },
    ];
    render(<LiveOutputPanel logs={logs} isRunning={false} result={result} />);
    expect(screen.queryByText(/ORDER #1:/)).toBeNull();
    expect(screen.queryByText(/BUY FILL #1:/)).toBeNull();
    expect(screen.queryByText(/POSITION OPEN #1:/)).toBeNull();
    expect(screen.queryByText(/PERFORMANCE #1:/)).toBeNull();
  });
});

// BTCAAAAA-35662: thick-client filter bar — level + category toggle buttons,
// Unselect All, bottom stats bar, and [TAG] bracket display.
describe('LiveOutputPanel — thick-client filter bar (BTCAAAAA-35662)', () => {
  const ts = (n: number) => `2026-01-01T00:00:0${n}Z`;
  const log = (message: string, n = 0): BacktestStatusMessage => ({ message, level: 'INFO', timestamp: ts(n) });
  const NOMATCH = 'xyzzy_unique_no_match_999';

  beforeEach(() => { localStorage.clear(); });

  // ── Select / Unselect All ───────────────────────────────────────────────────

  it('Unselect All hides every line including hidden-filter matches (PERFORMANCE, CONFIG_READ)', () => {
    const logs = [
      log('TRADE OPENED: BTC long'),
      log('PERFORMANCE #1: WIN | TP1 | Total PnL: $10.00', 1),
      log('Loading bars from Binance...', 2),
    ];
    render(<LiveOutputPanel logs={logs} />);
    fireEvent.click(screen.getByTitle('Toggle all event filters')); // Unselect All
    expect(screen.getByText(/No lines match the active filters/)).toBeInTheDocument();
    expect(screen.queryByText(/TRADE OPENED/)).toBeNull();
    expect(screen.queryByText(/PERFORMANCE #1/)).toBeNull();
    expect(screen.queryByText(/Loading bars/)).toBeNull();
  });

  it('Select All after Unselect All restores all lines', () => {
    const logs = [log('TRADE OPENED: BTC long'), log('PERFORMANCE #1: WIN | Total PnL: $10.00', 1)];
    render(<LiveOutputPanel logs={logs} />);
    const btn = screen.getByTitle('Toggle all event filters');
    fireEvent.click(btn); // Unselect All
    fireEvent.click(btn); // Select All
    expect(screen.getByText(/TRADE OPENED/)).toBeInTheDocument();
    expect(screen.getByText(/PERFORMANCE #1/)).toBeInTheDocument();
  });

  // ── Level filter buttons ────────────────────────────────────────────────────
  // Each pair: [label, matchMsg (classifies to that level), otherMsg (different level)]
  // - Messages avoid `|` in first 15 chars to prevent regex-OR issues.
  // - LOSS message avoids 'SL @' pattern which would trigger STOP_LOSS instead.

  it.each([
    ['INFO',      'Loading bars from Binance',    'Exit #1: WIN from TP1'],
    ['WIN',       'Exit #1: WIN from TP1 110',    'Loading bars from Binance'],
    ['LOSS',      'Exit #2: LOSS cutoff hit',      'Loading bars from Binance'],
    ['DECISION',  'Decision: entry evaluated',     'Loading bars from Binance'],
    ['STOP/LOSS', 'Exit #1: Stop Loss Hit',        'Loading bars from Binance'],
  ])('level filter "%s": shows matching line when enabled, hides when disabled', (label, matchMsg, otherMsg) => {
    render(<LiveOutputPanel logs={[log(matchMsg), log(otherMsg, 1)]} />);
    const toggleBtn = screen.getByTitle('Toggle all event filters');

    // All filters off
    fireEvent.click(toggleBtn);
    expect(screen.queryByText(new RegExp(matchMsg.slice(0, 12)))).toBeNull();

    // Enable only this level — match shows, other level is hidden
    fireEvent.click(screen.getByRole('button', { name: label }));
    expect(screen.getByText(new RegExp(matchMsg.slice(0, 12)))).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(otherMsg.slice(0, 12)))).toBeNull();

    // Disable again → match disappears
    fireEvent.click(screen.getByRole('button', { name: label }));
    expect(screen.queryByText(new RegExp(matchMsg.slice(0, 12)))).toBeNull();
  });

  // ── Category filter buttons ─────────────────────────────────────────────────

  it('category filter TRADE shows trade lines; SYSTEM lines hidden when only TRADE category is active', () => {
    const tradeLine = 'ORDER #1: LONG 1 BTC @ 100.00';
    const systemLine = 'Starting backtest engine now';
    render(<LiveOutputPanel logs={[log(tradeLine), log(systemLine, 1)]} />);

    fireEvent.click(screen.getByTitle('Toggle all event filters')); // Unselect All
    fireEvent.click(screen.getByRole('button', { name: 'INFO' }));  // enable INFO level
    fireEvent.click(screen.getByRole('button', { name: 'TRADE' })); // enable TRADE category

    expect(screen.getByText(/ORDER #1: LONG/)).toBeInTheDocument();
    expect(screen.queryByText(/Starting backtest/)).toBeNull();
  });

  // ── Stacking level filters (OR logic) ──────────────────────────────────────

  it('stacks level filters (OR): lines matching either enabled level both appear', () => {
    const winLine = 'Exit #1: WIN from TP1 @ 110.00';
    const lossLine = 'Exit #2: LOSS cutoff hit @ 90.00';
    const infoLine = 'Starting backtest engine';
    render(<LiveOutputPanel logs={[log(winLine), log(lossLine, 1), log(infoLine, 2)]} />);

    fireEvent.click(screen.getByTitle('Toggle all event filters')); // Unselect All
    fireEvent.click(screen.getByRole('button', { name: 'WIN' }));
    fireEvent.click(screen.getByRole('button', { name: 'LOSS' }));

    expect(screen.getByText(/Exit #1: WIN/)).toBeInTheDocument();
    expect(screen.getByText(/Exit #2: LOSS/)).toBeInTheDocument();
    expect(screen.queryByText(/Starting backtest/)).toBeNull();
  });

  // ── Bottom stats bar ────────────────────────────────────────────────────────

  it('shows bottom stats bar with Messages / Displayed / Decisions / Winners / Losses / Stop Loss / Trades', () => {
    const result = makeResult({ totalTrades: 3 });
    const logs: BacktestStatusMessage[] = [
      log('Exit #1: WIN | TP1 @ 110.00'),
      log('Exit #2: LOSS | SL @ 90.00', 1),
      log('Decision: trade entry evaluated', 2),
    ];
    render(<LiveOutputPanel logs={logs} result={result} />);
    const stats = screen.getByTestId('live-output-stats');
    expect(stats).toHaveTextContent('Messages:');
    expect(stats).toHaveTextContent('Displayed:');
    expect(stats).toHaveTextContent('Decisions:');
    expect(stats).toHaveTextContent('Winners:');
    expect(stats).toHaveTextContent('Losses:');
    expect(stats).toHaveTextContent('Stop Loss:');
    expect(stats).toHaveTextContent('Trades:');
  });

  // ── [TAG] bracket display in log rows ──────────────────────────────────────

  it('renders [INFO] and [SYSTEM] bracket tags for a system log line', () => {
    render(<LiveOutputPanel logs={[log('Starting backtest engine')]} />);
    expect(screen.getByText('[INFO]')).toBeInTheDocument();
    expect(screen.getByText('[SYSTEM]')).toBeInTheDocument();
  });

  it('renders [WIN] bracket tag for WIN-level lines', () => {
    render(<LiveOutputPanel logs={[log('Exit #1: WIN | TP1 @ 110.00')]} />);
    expect(screen.getByText('[WIN]')).toBeInTheDocument();
  });

  it('renders [LOSS] bracket tag for LOSS-level lines', () => {
    render(<LiveOutputPanel logs={[log('Exit #1: LOSS cutoff hit')]} />);
    expect(screen.getByText('[LOSS]')).toBeInTheDocument();
  });
});
