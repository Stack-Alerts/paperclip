'use client';

// Sprint A7 / BTCAAAAA-37781 — Visual-regression test harness.
// Extended in Sprint B7 / BTCAAAAA-38568 with mockups 4 (AI Request tab),
// 5 (AI Response tab), and 6 (History tab).
//
//   - mockup-1: RecommendationCard row (A3) at full width.
//   - mockup-2: StrategyImpactKpiBar (A2) above the row.
//   - mockup-3: Full layout — banner (A4) + row + right rail (A5+A6).
//   - mockup-4: AI Request tab — 5 CollapsibleSections with copy buttons (B1).
//   - mockup-5: AI Response tab — chip strip + MarkdownRenderer (B2).
//   - mockup-6: History tab — HistoryView with snapshot KPIs (B3).
//
// State is locked so screenshots are byte-stable.
// NO data files, NO API calls, NO fetch — all fixtures are inlined.

import { useState } from 'react';
import { CollapsibleSection, PreviewText } from '@/components/backtest/ai-recommendations/CollapsibleSection';
import { MarkdownRenderer } from '@/components/backtest/ai-recommendations/MarkdownRenderer';
import { HistoryView } from '@/components/backtest/ai-recommendations/HistoryView';
import type { AiRecsHistoryEntry } from '@/hooks/useAiRecsHistory';
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
      <Mockup4 />
      <Mockup5 />
      <Mockup6 />
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
// Mockup 4 — AI Request tab: 5 CollapsibleSections with copy buttons (B1).
// -----------------------------------------------------------------------------

const REQUEST_SECTIONS = [
  {
    title: '1. Strategy Parameters',
    description: '5 params',
    text: 'stopLoss: 0.030\nrsiPeriod: 14\ncooldown: 4\ntakeProfit: 0.063\ntrailAtr: 1.5',
  },
  {
    title: '2. Backtest Results',
    description: 'summary',
    text: 'winRate: 0.62\nnetLiquidity: 3450\nmaxDrawdown: 0.18\nprofitFactor: 1.42\nentries: 84',
  },
  {
    title: '3. Recent Trades',
    description: '5 trades',
    text: 'BTC/USDT LONG  +2.1%  2026-06-25 09:14\nBTC/USDT SHORT -0.8%  2026-06-25 11:02\nBTC/USDT LONG  +3.4%  2026-06-25 14:37\nBTC/USDT LONG  +1.2%  2026-06-26 08:11\nBTC/USDT SHORT -1.1%  2026-06-26 10:55',
  },
  {
    title: '4. Performance Metrics',
    description: '4 metrics',
    text: 'sharpe: 1.80\ncalmar: 2.10\nsortinoRatio: 2.34\nrecoveryFactor: 3.12',
  },
  {
    title: '5. Available Building Blocks',
    description: '8 blocks',
    text: '[\n  "RSI",\n  "MACD",\n  "BollingerBands",\n  "ATR",\n  "EMA",\n  "SMA",\n  "VWAP",\n  "OBV"\n]',
  },
] as const;

function Mockup4() {
  return (
    <section
      data-testid="mockup-4"
      aria-label="Mockup 4 — AI Request tab"
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
      <SectionHeader label="Mockup 4" subtitle="AI Request tab — 5 collapsible sections with copy buttons (B1)" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {REQUEST_SECTIONS.map((s) => (
          <CollapsibleSection
            key={s.title}
            title={s.title}
            description={s.description}
            defaultOpen
            copyText={s.text}
          >
            <PreviewText text={s.text} />
          </CollapsibleSection>
        ))}
      </div>
    </section>
  );
}

// -----------------------------------------------------------------------------
// Mockup 5 — AI Response tab: chip strip + MarkdownRenderer (B2).
// -----------------------------------------------------------------------------

const SAMPLE_RESPONSE_META = {
  provider: 'claude',
  tokens: 184,
  durationMs: 4100,
} as const;

const SAMPLE_RAW_REPLY = `## Analysis Summary

The backtest reveals **3 high-confidence improvement opportunities** based on 84 entries over the past 30 days.

### Key Findings

1. **Stop loss tightening** on RSI < 30 entries reduces tail losses by ~0.8% per trade
2. **Take profit extension** (1.5× trailing ATR on confirmed breakouts) captures an additional +2.0% average gain
3. **Volume filter** on 4h window eliminates 12 low-quality entries with negative EV

### Recommended Parameter Changes

\`\`\`
stopLoss: 0.030   # was 0.045
takeProfit: 0.063  # was 0.042
volumeFilter: 0.7  # new param
volWindow: 4h      # new param
\`\`\`

These changes are projected to improve *win rate* from **62% → 66%** and reduce max drawdown from 18% → 14%.`;

function Mockup5() {
  return (
    <section
      data-testid="mockup-5"
      aria-label="Mockup 5 — AI Response tab"
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
      <SectionHeader label="Mockup 5" subtitle="AI Response tab — chip strip + markdown render (B2)" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Header row: chip strip + copy button */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              data-testid="ai-recs-chip-provider"
              className="text-[10px] font-medium px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--accent-blue-soft)',
                color: 'var(--accent-blue)',
                border: '1px solid var(--accent-blue)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {SAMPLE_RESPONSE_META.provider}
            </span>
            <span
              data-testid="ai-recs-chip-tokens"
              className="text-[10px] font-medium px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {SAMPLE_RESPONSE_META.tokens} tokens
            </span>
            <span
              data-testid="ai-recs-chip-latency"
              className="text-[10px] font-medium px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {(SAMPLE_RESPONSE_META.durationMs / 1000).toFixed(1)}s
            </span>
          </div>
          <button
            type="button"
            data-testid="ai-recs-copy-response"
            className="px-2 py-1 rounded text-[10px] font-medium"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Copy
          </button>
        </div>
        {/* Response body */}
        <div
          data-testid="ai-recs-raw-reply"
          className="rounded p-3"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            minHeight: 200,
          }}
        >
          <MarkdownRenderer text={SAMPLE_RAW_REPLY} />
        </div>
      </div>
    </section>
  );
}

// -----------------------------------------------------------------------------
// Mockup 6 — History tab: HistoryView with snapshot KPIs (B3).
// -----------------------------------------------------------------------------

const NOOP_FN = () => undefined;
const NOOP_STR = (_id: string, _v: string) => undefined;

const SAMPLE_HISTORY: AiRecsHistoryEntry[] = [
  {
    id: 'hist-001',
    createdAt: '2026-06-27T08:00:00.000Z',
    prompt: 'Optimize for higher win rate while keeping drawdown below 20%.',
    summary: '3 recommendations — stop loss tighten, take profit extend, volume filter.',
    diagnosis: 'Win rate 62%, max drawdown 18%, 84 entries over 30 days.',
    recommendations: 'rec-1|rec-2|rec-3',
    raw: SAMPLE_RAW_REPLY,
    strategyName: 'BTC-RSI-v4',
    status: 'applied',
    notes: 'Applied rec-2 and rec-3. Monitoring for next cycle.',
    snapshotKpis: {
      winRate: 0.62,
      netLiquidity: 3450,
      maxDrawdown: 0.18,
      profitFactor: 1.42,
      entries: 84,
    },
  },
  {
    id: 'hist-002',
    createdAt: '2026-06-26T14:30:00.000Z',
    prompt: 'Check if volume filters improve entry quality.',
    summary: '2 recommendations — volume filter, 4h window adjustment.',
    diagnosis: 'High entry count with mixed volume quality.',
    recommendations: 'rec-A|rec-B',
    raw: '## Volume Analysis\n\nFiltering low-volume signals improves EV per trade by ~1.4%.',
    strategyName: 'BTC-RSI-v4',
    status: 'new',
    notes: '',
    snapshotKpis: {
      winRate: 0.59,
      netLiquidity: 3100,
      maxDrawdown: 0.21,
      profitFactor: 1.28,
      entries: 91,
    },
  },
  {
    id: 'hist-003',
    createdAt: '2026-06-25T10:00:00.000Z',
    prompt: 'Initial analysis run.',
    summary: '5 recommendations generated.',
    diagnosis: 'Baseline run — no changes applied.',
    recommendations: 'rec-X|rec-Y|rec-Z',
    raw: '## Baseline\n\nStrategy is performing within expected parameters.',
    strategyName: 'BTC-RSI-v4',
    status: 'dismissed',
    notes: 'Dismissed — baseline only.',
  },
];

function Mockup6() {
  return (
    <section
      data-testid="mockup-6"
      aria-label="Mockup 6 — History tab"
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
      <SectionHeader label="Mockup 6" subtitle="History tab — HistoryView with snapshot KPIs (B3)" />
      <HistoryView
        entries={SAMPLE_HISTORY}
        hydrated
        onUpdateStatus={NOOP_FN}
        onUpdateNotes={NOOP_STR}
        onRequestDelete={NOOP_FN}
        onRequestClearAll={NOOP_FN}
        onLoadIntoCurrent={NOOP_FN}
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