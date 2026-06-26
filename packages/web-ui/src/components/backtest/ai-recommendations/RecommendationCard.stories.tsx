import { useState } from 'react';
import { RecommendationCard, RecommendationCardData } from './RecommendationCard';
import { RecommendationsRow } from './RecommendationsRow';
import { RecommendationCategoryId } from './recommendationCategoryPalette';

const SAMPLE_CODE = ['side = long', 'tp_ratio = 1.5x', 'risk_pct = 0.25'];
const SAMPLE_ANALYSIS_ID = 'storybook-analysis-fixture';

function makeRec(
  id: string,
  categoryId: RecommendationCategoryId,
  title: string,
  delta: string,
): RecommendationCardData {
  return {
    id,
    categoryId,
    deltaLabel: delta,
    title,
    description:
      'Widen the stop past the −0.7% cluster so winning runners survive the last micro-drawdown before the breakout.',
    codeLines: SAMPLE_CODE,
    applied: false,
    onToggleApplied: () => undefined,
    onApplyOnChart: () => undefined,
    analysisId: SAMPLE_ANALYSIS_ID,
  };
}

const SAMPLE_RECS: RecommendationCardData[] = [
  makeRec('r1', 'risk', 'Widen the stop past the −0.7% cluster', '+2.3%'),
  makeRec('r2', 'entry', 'Gate entries against the EMA-15 vector', '+1.4%'),
  makeRec('r3', 'exit', 'Tighten the Below Axis 10 window to 6 candles', '+0.9%'),
  makeRec('r4', 'signal', 'Deepen reclock on the 100% TP-aware exit', '+3.1%'),
  makeRec('r5', 'regime', 'Shorten Bearish Climax reclock to 3 bars', '+0.6%'),
];

function StatefulRow({ initialApplied = [] as string[] }: { initialApplied?: string[] }) {
  const [applied, setApplied] = useState<Set<string>>(new Set(initialApplied));
  const recs = SAMPLE_RECS.map((r) => ({
    ...r,
    applied: applied.has(r.id),
    onToggleApplied: (next: boolean) =>
      setApplied((prev) => {
        const copy = new Set(prev);
        if (next) copy.add(r.id);
        else copy.delete(r.id);
        return copy;
      }),
  }));
  return <RecommendationsRow recommendations={recs} analysisId={SAMPLE_ANALYSIS_ID} />;
}

const meta = {
  title: 'Backtest/AI Recommendations/RecommendationCard',
  component: RecommendationCard,
};
export default meta;

export const Default = { render: () => <StatefulRow /> };

export const Applied = { render: () => <StatefulRow initialApplied={['r1']} /> };

function SingleCardDemo() {
  const [applied, setApplied] = useState(false);
  return (
    <div style={{ width: 320 }}>
      <RecommendationCard
        {...SAMPLE_RECS[0]}
        applied={applied}
        onToggleApplied={setApplied}
      />
    </div>
  );
}

export const SingleCard = {
  render: () => <SingleCardDemo />,
};

export const WrapAt1439 = {
  parameters: { viewport: { defaultViewport: 'desktop1439' } },
  render: () => (
    <div style={{ width: 1439 }}>
      <StatefulRow />
    </div>
  ),
};
