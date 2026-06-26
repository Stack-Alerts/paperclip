'use client';

import { RecommendationCard, RecommendationCardData } from './RecommendationCard';

export interface RecommendationsRowProps {
  recommendations: RecommendationCardData[];
  /**
   * Stable identifier for the analysis that produced this batch of
   * recommendations. Passed through to every card so per-card feedback
   * keys are scoped to the same analysis. See BTCAAAAA-38468.
   */
  analysisId: string;
}

const MIN_CARD_PX = 248;
const COLUMN_GAP_PX = 12;

export function RecommendationsRow({ recommendations, analysisId }: RecommendationsRowProps) {
  return (
    <div
      data-testid="recommendations-row"
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fit, minmax(${MIN_CARD_PX}px, 1fr))`,
        gap: COLUMN_GAP_PX,
        width: '100%',
      }}
    >
      {recommendations.map((rec) => (
        <RecommendationCard key={rec.id} {...rec} analysisId={analysisId} />
      ))}
    </div>
  );
}
