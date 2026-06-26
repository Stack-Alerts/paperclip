'use client';

// Sprint A7 / BTCAAAAA-37781 — Storybook entries for StrategyAfterChangesRail (A5+A6).
//
// Custom ".stories.tsx" pattern (NOT the Storybook framework) — these exports
// are picked up by the visual-regression harness in `e2e/ai-recs-panel.spec.ts`
// and rendered at 1920 / 1440 / 1280 px to verify the rail matches the right
// rail of mockup 3 (BTCAAAAA-37748) across status pills, carried-over links,
// and the empty-state fallback.

import { useState } from 'react';
import { StrategyAfterChangesRail } from './StrategyAfterChangesRail';
import type {
  AfterChangesItem,
  AfterChangesStatus,
} from './strategyAfterChangesMerge';

const CURRENT_RECS: AfterChangesItem[] = [
  {
    key: 'current:rec-1',
    recId: 'rec-1',
    title: 'Tighten stop loss on entry signals (RSI < 30)',
    status: 'recommended',
    carriedOver: false,
  },
  {
    key: 'current:rec-2',
    recId: 'rec-2',
    title: 'Increase take profit on breakout trades',
    status: 'applied',
    carriedOver: false,
  },
  {
    key: 'current:rec-3',
    recId: 'rec-3',
    title: 'Filter low-volume breakouts in the 4h window',
    status: 'recommended',
    carriedOver: false,
  },
];

const STAGED_PRIOR: AfterChangesItem[] = [
  {
    key: 'prior:hist-abc:rec-0',
    recId: 'hist-abc:rec-0',
    title: 'Widen the trailing stop on regime shift (carried)',
    status: 'staged-from-prior',
    carriedOver: true,
    originHistoryEntryId: 'hist-abc',
  },
  {
    key: 'prior:hist-def:rec-1',
    recId: 'hist-def:rec-1',
    title: 'Cap daily drawdown at 6% (carried)',
    status: 'staged-from-prior',
    carriedOver: true,
    originHistoryEntryId: 'hist-def',
  },
];

const MIXED_ITEMS: AfterChangesItem[] = [...CURRENT_RECS, ...STAGED_PRIOR];

function RailDemo({
  items,
  initialOn,
  showJumpHandler = false,
}: {
  items: AfterChangesItem[];
  initialOn: ReadonlyArray<string>;
  showJumpHandler?: boolean;
}) {
  const [toggleOn, setToggleOn] = useState<ReadonlySet<string>>(
    () => new Set(initialOn),
  );
  const handleToggle = (recId: string) => {
    setToggleOn((prev) => {
      const next = new Set(prev);
      if (next.has(recId)) next.delete(recId);
      else next.add(recId);
      return next;
    });
  };
  return (
    <div style={{ padding: 16 }}>
      <StrategyAfterChangesRail
        items={items}
        toggleOn={toggleOn}
        onToggleCurrent={handleToggle}
        {...(showJumpHandler
          ? { onJumpToOriginEntry: () => undefined }
          : {})}
      />
    </div>
  );
}

const meta = {
  title: 'Backtest/AI Recommendations/StrategyAfterChangesRail',
  component: StrategyAfterChangesRail,
};

export default meta;

// A5+A6 — Empty state: no current recs, no staged items.
export const Empty = {
  render: () => (
    <RailDemo items={[]} initialOn={[]} />
  ),
};

// A5+A6 — Current only: 3 recs, mix of "recommended" and "applied" pills.
export const CurrentOnly = {
  render: () => (
    <RailDemo items={CURRENT_RECS} initialOn={['rec-2']} />
  ),
};

// A5+A6 — Prior staged: 2 carried-over items with "view analysis" links.
export const PriorStaged = {
  render: () => (
    <RailDemo items={STAGED_PRIOR} initialOn={[]} showJumpHandler />
  ),
};

// A5+A6 — Mixed: current + staged-from-prior; verifies all 3 pill colors and
// the carried-over link sit side-by-side without clipping.
export const Mixed = {
  render: () => (
    <RailDemo items={MIXED_ITEMS} initialOn={['rec-2']} showJumpHandler />
  ),
};

// A5+A6 — Wrap-at-1439 sanity: rail sits beside the main column at 1439 px
// without clipping the rightmost toggle.
export const WrapAt1439 = {
  parameters: { viewport: { defaultViewport: 'desktop1439' } },
  render: () => (
    <div style={{ width: 1439, padding: 16 }}>
      <RailDemo items={MIXED_ITEMS} initialOn={['rec-2']} showJumpHandler />
    </div>
  ),
};

// A5+A6 — Wrap at 1280: tighter viewport; titles truncate rather than overflow.
export const WrapAt1280 = {
  parameters: { viewport: { defaultViewport: 'desktop1280' } },
  render: () => (
    <div style={{ width: 1280, padding: 16 }}>
      <RailDemo items={MIXED_ITEMS} initialOn={['rec-2']} showJumpHandler />
    </div>
  ),
};

// Compile-time sanity: STATUS_PILL rendering is exhaustive over AfterChangesStatus.
const _statusCoverage: Record<AfterChangesStatus, true> = {
  recommended: true,
  applied: true,
  'staged-from-prior': true,
};
void _statusCoverage;