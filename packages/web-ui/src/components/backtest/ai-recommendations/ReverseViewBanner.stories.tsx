'use client';

// Sprint A7 / BTCAAAAA-37781 — Storybook entries for ReverseViewBanner (A4).
//
// Custom ".stories.tsx" pattern (NOT the Storybook framework) — these exports
// are picked up by the visual-regression harness in `e2e/ai-recs-panel.spec.ts`
// and rendered at 1920 / 1440 / 1280 px to verify the banner matches mockup 3
// of BTCAAAAA-37748 across sample sizes (empty / small / large).

import { ReverseViewBanner } from './ReverseViewBanner';
import type { ReverseViewPattern } from './reverseViewPattern';

const EMPTY_PATTERN: ReverseViewPattern = {
  sampleSize: 0,
  totalSize: 0,
  avgUplift: 0,
  topCategories: [],
  topParamKeys: [],
  headline: 'Not enough recommendations yet to surface a shared pattern.',
};

const FULL_PATTERN: ReverseViewPattern = {
  sampleSize: 3,
  totalSize: 12,
  avgUplift: 4.2,
  topCategories: ['risk', 'entry'],
  topParamKeys: ['stopLoss', 'rsiPeriod'],
  headline:
    'Top quartile (3 of 12) lifts the strategy by +4.2% on average.',
};

const NEGATIVE_PATTERN: ReverseViewPattern = {
  sampleSize: 2,
  totalSize: 8,
  avgUplift: -1.5,
  topCategories: ['exit'],
  topParamKeys: ['takeProfit'],
  headline:
    'Top quartile (2 of 8) lifts the strategy by -1.5% on average.',
};

const SINGLE_CATEGORY: ReverseViewPattern = {
  sampleSize: 1,
  totalSize: 4,
  avgUplift: 0.8,
  topCategories: ['risk'],
  topParamKeys: ['stopLoss'],
  headline:
    'Top quartile (1 of 4) lifts the strategy by +0.8% on average.',
};

function BannerDemo({ pattern }: { pattern: ReverseViewPattern }) {
  return (
    <div style={{ padding: 16, width: 900 }}>
      <ReverseViewBanner pattern={pattern} />
    </div>
  );
}

const meta = {
  title: 'Backtest/AI Recommendations/ReverseViewBanner',
  component: ReverseViewBanner,
};

export default meta;

// A4 — Empty: insufficient sample, headline + nothing else (auto-hide).
export const Empty = {
  render: () => <BannerDemo pattern={EMPTY_PATTERN} />,
};

// A4 — Full: top-quartile sample with 2 categories + 2 param keys.
export const FullSample = {
  render: () => <BannerDemo pattern={FULL_PATTERN} />,
};

// A4 — Negative uplift: chip flips to the red palette.
export const NegativeUplift = {
  render: () => <BannerDemo pattern={NEGATIVE_PATTERN} />,
};

// A4 — Single category / single param: the "1 of 4" edge case.
export const SingleCategory = {
  render: () => <BannerDemo pattern={SINGLE_CATEGORY} />,
};

// A4 — Wrap-at-1439 sanity: the headline + chip stay on one row while the
// categories / params grid wraps below.
export const WrapAt1439 = {
  parameters: { viewport: { defaultViewport: 'desktop1439' } },
  render: () => (
    <div style={{ width: 1439, padding: 16 }}>
      <BannerDemo pattern={FULL_PATTERN} />
    </div>
  ),
};

// A4 — Wrap at 1280: tighter still — verify the chip + headline do not clip.
export const WrapAt1280 = {
  parameters: { viewport: { defaultViewport: 'desktop1280' } },
  render: () => (
    <div style={{ width: 1280, padding: 16 }}>
      <BannerDemo pattern={FULL_PATTERN} />
    </div>
  ),
};