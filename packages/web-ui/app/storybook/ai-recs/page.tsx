'use client';

// Sprint A7 / BTCAAAAA-37781 — Visual-regression test harness.
//
// This page mounts the Sprint A1–A6 components in three deterministic
// configurations that map 1:1 to mockups 1, 2, 3 of BTCAAAAA-37748:
//
//   - mockup-1: RecommendationCard row (A3) at full width.
//   - mockup-2: StrategyImpactKpiBar (A2) above the row, with two
//               applied-rec impacts so the indicator flips to "Preview".
//   - mockup-3: Full layout — banner (A4) + row + right rail (A5+A6).
//
// State is locked (toggleOn = {rec-2}) so screenshots are byte-stable.
// NO data files, NO API calls, NO fetch — all fixtures are inlined.
//
// The matching e2e/ai-recs-panel.spec.ts targets these data-testids
// and snapshots them at 1920 / 1440 / 1280 px viewport widths.

import { useState } from 'react';
import {
  StrategyImpactKpiBar,
  type ImpactBarMode,
} from '@/components/backtest/ai-recommendations/StrategyImpactKpiBar';
import {
  type RecommendationCardData,
} from '@/components/backtest/ai-recommendations/RecommendationCard';
import { RecommendationsRow } from '@/components/backtest/ai-recommendations/RecommendationsRow';
import { StrategyAfterChangesRail } from '@/components/backtest/ai-recommendations/StrategyAfterChangesRail';
import { ReverseViewBanner } from '@/components/backtest/ai-recommendations/ReverseViewBanner';
import type { RecommendationCategoryId } from '@/components/backtest/ai-recommendations/recommendationCategoryPalette';
import type {
  AppliedRecImpact,
  KpiSet,
} from '@/components/backtest/ai-recommendations/strategyImpactKpi';
import type {
  AfterChangesItem,
} from '@/components/backtest/ai-recommendations/strategyAfterChangesMerge';
import type {
  ReverseViewPattern,
} from '@/components/backtest/ai-recommendations/reverseViewPattern';

// -----------------------------------------------------------------------------
// Inline fixtures — locked for deterministic screenshot diffs.
// -----------------------------------------------------------------------------

const KPI_BASELINE: KpiSet = {
  winRate: 0.62,
  netLiquidity: 3_450,
  maxDrawdown: 0.18,
  profitFactor: 1.42,
  entries: 84,
};

const KPI_IMPACTS: AppliedRecImpact[] = [
  {
    recId: 'rec-2',
    delta: {
      winRate: 0.04,
      netLiquidity: 420,
      maxDrawdown: -0.03,
      profitFactor: 0.18,
      entries: -4,
    },
  },
  {
    recId: 'rec-3',
    delta: {
      winRate: 0.02,
      netLiquidity: 180,
      maxDrawdown: -0.01,
      profitFactor: 0.06,
    },
  },
];

const KPI_SNAPSHOT_AFTER: KpiSet = {
  winRate: 0.66,
  netLiquidity: 4_050,
  maxDrawdown: 0.14,
  profitFactor: 1.66,
  entries: 80,
};

const REVERSE_VIEW_PATTERN: ReverseViewPattern = {
  sampleSize: 3,
  totalSize: 12,
  avgUplift: 4.2,
  topCategories: ['risk', 'entry'],
  topParamKeys: ['stopLoss', 'rsiPeriod'],
  headline:
    'Top quartile (3 of 12) lifts the strategy by +4.2% on average.',
};

const NOOP = () => undefined;

const STORY_ANALYSIS_ID = 'story-analysis-1';

const SAMPLE_RECS: RecommendationCardData[] = [
  {
    id: 'rec-1',
    analysisId: STORY_ANALYSIS_ID,
    title: 'Tighten stop loss on entry signals (RSI < 30)',
    description:
      'Reduces tail losses when RSI dips below 30 within the first 4 candles of an entry.',
    categoryId: 'risk',
    deltaLabel: '+4.0% WR',
    applied: false,
    codeLines: ['stopLoss: 0.030', 'rsiPeriod: 14', 'cooldown: 4'],
    onToggleApplied: NOOP,
  },
  {
    id: 'rec-2',
    analysisId: STORY_ANALYSIS_ID,
    title: 'Increase take profit on breakout trades',
    description:
      'Extends the trailing target by 1.5× on confirmed breakouts above the 20-period high.',
    categoryId: 'exit',
    deltaLabel: '+2.0% WR',
    applied: true,
    codeLines: ['takeProfit: 0.063', 'trailAtr: 1.5'],
    onToggleApplied: NOOP,
  },
  {
    id: 'rec-3',
    analysisId: STORY_ANALYSIS_ID,
    title: 'Filter low-volume breakouts in the 4h window',
    description:
      'Skips entries where 4h volume is below 0.7× of its 30-period median.',
    categoryId: 'entry',
    deltaLabel: '+0.06 PF',
    applied: false,
    codeLines: ['volumeFilter: 0.7', 'volWindow: 4h', 'volMedian: 30'],
    onToggleApplied: NOOP,
  },
  {
    id: 'rec-4',
    analysisId: STORY_ANALYSIS_ID,
    title: 'Reduce position size during regime shifts',
    description:
      'Halves base size when ADX transitions from < 20 to ≥ 25 within 6 candles.',
    categoryId: 'regime',
    deltaLabel: '-0.03 DD',
    deltaNegative: true,
    applied: false,
    codeLines: ['positionSize: -0.5', 'adxFloor: 25', 'adxShiftWindow: 6'],
    onToggleApplied: NOOP,
  },
  {
    id: 'rec-5',
    analysisId: STORY_ANALYSIS_ID,
    title: 'Pause entries after 3 consecutive losses',
    description:
      'Halts new entries for the next 6 candles once 3 stops trigger in a row.',
    categoryId: 'signal',
    deltaLabel: '+/-0',
    applied: false,
    codeLines: ['lossCooldown: 6', 'lossStreak: 3'],
    onToggleApplied: NOOP,
  },
];

const CATEGORY_LABEL_OVERRIDES: Partial<Record<RecommendationCategoryId, string>> = {
  risk: 'risk',
  entry: 'entry',
  exit: 'exit',
  signal: 'signal',
  regime: 'regime',
};

const AFTER_CHANGES_ITEMS: AfterChangesItem[] = [
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

// Locked toggle state — only rec-2 is "ON" so screenshot diffs stay stable.
const LOCKED_TOGGLE: ReadonlySet<string> = new Set(['rec-2']);

const SAMPLE_RECS_LOCKED: RecommendationCardData[] = SAMPLE_RECS.map((rec) =>
  rec.id === 'rec-2' ? { ...rec, applied: true } : { ...rec, applied: false },
);

// -----------------------------------------------------------------------------
// Page entry.
// -----------------------------------------------------------------------------

export default function AiRecsStorybookPage() {
  return (
    <main
      style={{
        background: 'var(--bg-base)',
        color: 'var(--text-primary)',
        minHeight: '100vh',
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 32,
      }}
      data-testid="ai-recs-storybook-page"
    >
      <header>
        <h1
          style={{
            fontSize: 18,
            fontWeight: 600,
            margin: 0,
            color: 'var(--text-secondary)',
          }}
        >
          AI Recommendations — visual regression harness
        </h1>
        <p
          style={{
            fontSize: 12,
            margin: '4px 0 0',
            color: 'var(--text-faint)',
          }}
        >
          BTCAAAAA-37781 / Sprint A7. Each section maps to a board mockup.
        </p>
      </header>

      <Mockup1 />
      <Mockup2 />
      <Mockup3 />
    </main>
  );
}

// -----------------------------------------------------------------------------
// Mockup 1 — RecommendationCard row (A3).
// -----------------------------------------------------------------------------

function Mockup1() {
  return (
    <section
      data-testid="mockup-1"
      aria-label="Mockup 1 — recommendation row"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <SectionHeader label="Mockup 1" subtitle="Recommendation row (A3)" />
      <RecommendationsRow recommendations={SAMPLE_RECS_LOCKED} analysisId={STORY_ANALYSIS_ID} />
    </section>
  );
}

// -----------------------------------------------------------------------------
// Mockup 2 — KPI bar (A2) above the recommendation row.
// -----------------------------------------------------------------------------

function Mockup2() {
  const [mode] = useState<ImpactBarMode>('live');
  return (
    <section
      data-testid="mockup-2"
      aria-label="Mockup 2 — KPI bar + row"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <SectionHeader label="Mockup 2" subtitle="Impact KPI bar (A2) + row" />
      <StrategyImpactKpiBar
        baseline={KPI_BASELINE}
        appliedImpacts={KPI_IMPACTS}
        mode={mode}
        snapshotAfter={mode === 'snapshot' ? KPI_SNAPSHOT_AFTER : undefined}
      />
      <RecommendationsRow recommendations={SAMPLE_RECS_LOCKED} analysisId={STORY_ANALYSIS_ID} />
    </section>
  );
}

// -----------------------------------------------------------------------------
// Mockup 3 — Full layout: banner (A4) + row + right rail (A5+A6).
// -----------------------------------------------------------------------------

function Mockup3() {
  return (
    <section
      data-testid="mockup-3"
      aria-label="Mockup 3 — full layout"
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) 320px',
        gap: 16,
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          minWidth: 0,
        }}
      >
        <SectionHeader
          label="Mockup 3"
          subtitle="Reverse view banner (A4) + row + right rail (A5+A6)"
        />
        <ReverseViewBanner pattern={REVERSE_VIEW_PATTERN} />
        <RecommendationsRow recommendations={SAMPLE_RECS_LOCKED} analysisId={STORY_ANALYSIS_ID} />
      </div>
      <StrategyAfterChangesRail
        items={AFTER_CHANGES_ITEMS}
        toggleOn={LOCKED_TOGGLE}
        onToggleCurrent={NOOP}
        onJumpToOriginEntry={NOOP}
      />
    </section>
  );
}

// -----------------------------------------------------------------------------
// Shared section header.
// -----------------------------------------------------------------------------

function SectionHeader({
  label,
  subtitle,
}: {
  label: string;
  subtitle: string;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 8,
        borderBottom: '1px solid var(--border)',
        paddingBottom: 8,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: 1,
          color: 'var(--text-muted)',
        }}
      >
        {label}
      </span>
      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
        {subtitle}
      </span>
    </div>
  );
}