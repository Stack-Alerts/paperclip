'use client';

// Sprint A7 / BTCAAAAA-37781 — Storybook entries for StrategyImpactKpiBar (A2).
//
// Custom ".stories.tsx" pattern (NOT the Storybook framework) — these exports
// are picked up by the visual-regression harness in `e2e/ai-recs-panel.spec.ts`
// and rendered at 1920 / 1440 / 1280 px to verify the bar matches mockup 2
// of BTCAAAAA-37748 across indicator states (idle / preview / snapshot).

import { StrategyImpactKpiBar, ImpactBarMode } from './StrategyImpactKpiBar';
import {
  AppliedRecImpact,
  KpiSet,
} from './strategyImpactKpi';

const BASELINE: KpiSet = {
  winRate: 0.62,
  netLiquidity: 3_450,
  maxDrawdown: 0.18,
  profitFactor: 1.42,
  entries: 84,
};

const SAMPLE_IMPACTS: AppliedRecImpact[] = [
  {
    recId: 'r1',
    delta: {
      winRate: 0.04,
      netLiquidity: 420,
      maxDrawdown: -0.03,
      profitFactor: 0.18,
      entries: -4,
    },
  },
  {
    recId: 'r2',
    delta: {
      winRate: 0.02,
      netLiquidity: 180,
      maxDrawdown: -0.01,
      profitFactor: 0.06,
    },
  },
];

function BarDemo({
  mode,
  impacts,
  snapshotAfter,
  appliedCount,
}: {
  mode: ImpactBarMode;
  impacts: AppliedRecImpact[];
  snapshotAfter?: KpiSet;
  appliedCount: number;
}) {
  // Force re-mount on prop change so each story starts in its idle indicator
  // state — otherwise navigating from one story to another would carry the
  // previous debounced state.
  return (
    <div style={{ padding: 16, width: 900 }}>
      <StrategyImpactKpiBar
        key={`${mode}-${appliedCount}`}
        baseline={BASELINE}
        appliedImpacts={impacts}
        mode={mode}
        snapshotAfter={snapshotAfter}
      />
    </div>
  );
}

const meta = {
  title: 'Backtest/AI Recommendations/StrategyImpactKpiBar',
  component: StrategyImpactKpiBar,
};

export default meta;

// A2 — Idle (Baseline): no applied recs, indicator shows "Baseline"
export const IdleBaseline = {
  render: () => <BarDemo mode="live" impacts={[]} appliedCount={0} />,
};

// A2 — Preview: 2 applied recs, indicator flips to "Preview"
export const Preview = {
  render: () => (
    <BarDemo mode="live" impacts={SAMPLE_IMPACTS} appliedCount={2} />
  ),
};

// A2 — Snapshot mode: bar renders the snapshotAfter value side-by-side with
// the live projected value. Used by A6 diagnose-tab snapshots.
export const Snapshot = {
  render: () => (
    <BarDemo
      mode="snapshot"
      impacts={SAMPLE_IMPACTS}
      snapshotAfter={{
        winRate: 0.66,
        netLiquidity: 4_050,
        maxDrawdown: 0.14,
        profitFactor: 1.66,
        entries: 80,
      }}
      appliedCount={2}
    />
  ),
};

// A2 — Wrap-at-1439 sanity: at this width the right-side "applied" chip must
// stay visible while the four tiles wrap to two rows.
export const WrapAt1439 = {
  parameters: { viewport: { defaultViewport: 'desktop1439' } },
  render: () => (
    <div style={{ width: 1439, padding: 16 }}>
      <BarDemo mode="live" impacts={SAMPLE_IMPACTS} appliedCount={2} />
    </div>
  ),
};

// A2 — Wrap at 1280: tighter still — verify the chip does not clip
export const WrapAt1280 = {
  parameters: { viewport: { defaultViewport: 'desktop1280' } },
  render: () => (
    <div style={{ width: 1280, padding: 16 }}>
      <BarDemo mode="live" impacts={SAMPLE_IMPACTS} appliedCount={2} />
    </div>
  ),
};
