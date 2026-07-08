import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TradesPanel } from '@/components/backtest/trades/TradesPanel';
import type { Trade } from '@/lib/strategy-builder/types';

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: '1.1',
    entryTime: '2026-03-15T08:00:00Z',
    exitTime: '2026-03-15T10:30:00Z',
    entryPrice: 62816.9,
    exitPrice: 61540.32,
    quantity: 0.0001,
    pnl: 203.22,
    pnlPercentage: 2.03,
    bars: 10,
    exitType: 'SL',
    side: 'SHORT',
    symbol: 'BTC.P/USDT',
    status: 'CLOSED',
    ...overrides,
  };
}

// Build a partial-exit group where the backend sent duplicated `.1` ids for
// each leg (the original "1.1 1.1 1.1" bug shape) — exercises the new
// sequential renumbering (`5.1`, `5.2`, `5.3`).
function makePartialGroup(baseId: string, legs: number): Trade[] {
  return Array.from({ length: legs }, (_, i) =>
    makeTrade({
      id: `${baseId}.1`, // duplicate on purpose — same shape as the engine bug
      entryTime: `2026-03-15T0${i + 1}:00:00Z`,
      pnl: 50 * (i + 1),
      pnlPercentage: 1.5 * (i + 1),
    })
  );
}

describe('TradesPanel — BTCAAAAA-36001 date display', () => {
  it('renders a Date/Time column header instead of the legacy Time header', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    expect(screen.getByRole('columnheader', { name: /Date\/Time/i })).toBeInTheDocument();
  });

  it('shows both the calendar date and the time for a trade', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    // entryTime is "2026-03-15T08:00:00Z". Whatever the test-runner timezone, the
    // formatter uses local getMonth/getDate, so we assert the *displayed* date
    // by reading it back from the rendered <td>.
    const cell = screen.getByTitle('2026-03-15T08:00:00Z');
    expect(cell).toBeInTheDocument();
    // Cell text must contain a slash-separated date and an HH:MM:SS time.
    expect(cell.textContent).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}/);
  });

  it('exposes the full ISO entryTime as a title attribute on the cell', () => {
    render(<TradesPanel trades={[makeTrade()]} />);
    expect(screen.getByTitle('2026-03-15T08:00:00Z')).toBeInTheDocument();
  });

  it('renders the em-dash placeholder when entryTime is empty', () => {
    const trade = makeTrade({ entryTime: '' });
    const { container } = render(<TradesPanel trades={[trade]} />);
    const tds = container.querySelectorAll('tbody td');
    // 2nd cell is the time cell (index 1).
    expect(tds[1]?.textContent).toBe('—');
  });
});

describe('TradesPanel — BTCAAAAA-39020 trade-collapse + sub-id numbering', () => {
  it('renumbers partial-exit rows even when the backend sends duplicated base.1 ids', () => {
    // Three trades with id="5.1" (the original bug shape) must render as
    // 5.1, 5.2, 5.3 — never as "5.1 5.1 5.1".
    const trades = makePartialGroup('5', 3);
    render(<TradesPanel trades={trades} />);

    expect(screen.getByText('5.1')).toBeInTheDocument();
    expect(screen.getByText('5.2')).toBeInTheDocument();
    expect(screen.getByText('5.3')).toBeInTheDocument();
    // And the source id "5.1" must NOT appear three times — only once as
    // the per-row display label for the first leg.
    const matches = screen.getAllByText('5.1');
    expect(matches).toHaveLength(1);
  });

  it('hides partial-exit rows when a group is collapsed, keeping only the totals row', () => {
    const trades = makePartialGroup('7', 3);
    const { container } = render(<TradesPanel trades={trades} />);

    // All three sub-ids are visible before collapse.
    expect(screen.getByText('7.1')).toBeInTheDocument();
    expect(screen.getByText('7.2')).toBeInTheDocument();
    expect(screen.getByText('7.3')).toBeInTheDocument();

    // Click the first partial row's Trade # to collapse that group.
    fireEvent.click(screen.getByText('7.1'));

    // After collapse, only the totals row survives — sub-id cells go away.
    expect(screen.queryByText('7.1')).not.toBeInTheDocument();
    expect(screen.queryByText('7.2')).not.toBeInTheDocument();
    expect(screen.queryByText('7.3')).not.toBeInTheDocument();
    expect(container.textContent).toContain('collapsed');
    // Totals row still anchored to baseId 7.
    expect(container.textContent).toContain('#7 Total');
  });

  it('toggles a group back open when its Trade # is clicked a second time', () => {
    const trades = makePartialGroup('9', 2);
    render(<TradesPanel trades={trades} />);

    // Collapse via totals-row chevron (cell is the chevron + label).
    const totalsCell = screen.getByTitle(/Trade 9 — click to collapse/);
    fireEvent.click(totalsCell);
    expect(screen.queryByText('9.1')).not.toBeInTheDocument();

    // Expand again — totals cell flips its title.
    const expandedCell = screen.getByTitle(/Trade 9 — click to expand/);
    fireEvent.click(expandedCell);
    expect(screen.getByText('9.1')).toBeInTheDocument();
    expect(screen.getByText('9.2')).toBeInTheDocument();
  });

  it('renders expand-all / collapse-all / reset-view buttons in the section header', () => {
    const trades = makePartialGroup('11', 2);
    render(<TradesPanel trades={trades} />);

    expect(screen.getByRole('button', { name: /expand all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /collapse all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reset view/i })).toBeInTheDocument();
  });

  it('collapse-all hides every partial group and re-renders them via expand-all', () => {
    const trades = [...makePartialGroup('20', 2), ...makePartialGroup('30', 2)];
    render(<TradesPanel trades={trades} />);

    // Sanity: all four sub-ids visible at first.
    expect(screen.getByText('20.1')).toBeInTheDocument();
    expect(screen.getByText('30.2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /collapse all/i }));

    expect(screen.queryByText('20.1')).not.toBeInTheDocument();
    expect(screen.queryByText('30.1')).not.toBeInTheDocument();
    // Both totals rows are still rendered so the user can expand again.
    expect(screen.getAllByText(/Total/).length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole('button', { name: /expand all/i }));
    expect(screen.getByText('20.1')).toBeInTheDocument();
    expect(screen.getByText('30.2')).toBeInTheDocument();
  });

  it('does not render header action buttons on the empty state', () => {
    // The empty-state branch intentionally omits the action buttons (nothing
    // to expand/collapse); the rest of this suite covers the enabled path
    // with one or more groups present.
    render(<TradesPanel trades={[]} />);
    expect(screen.queryByRole('button', { name: /expand all/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /collapse all/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Reset view/i })).not.toBeInTheDocument();
  });

  it('keeps header action buttons enabled when at least one group exists', () => {
    const trades = makePartialGroup('77', 2);
    render(<TradesPanel trades={trades} />);
    expect(screen.getByRole('button', { name: /expand all/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /collapse all/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Reset view/i })).toBeEnabled();
  });

  it('locks the TRADE HISTORY title and thead inside the scroll container', () => {
    const trades = [makeTrade({ id: '1' })];
    const { container } = render(<TradesPanel trades={trades} />);
    const h3 = container.querySelector('h3');
    const thead = container.querySelector('thead');
    expect(h3).not.toBeNull();
    expect(thead).not.toBeNull();
    // Sticky positioning is what survives scroll — assert the inline style.
    expect(h3!.getAttribute('style') ?? '').toMatch(/position:\s*sticky/);
    expect(thead!.getAttribute('style') ?? '').toMatch(/position:\s*sticky/);
  });
});

