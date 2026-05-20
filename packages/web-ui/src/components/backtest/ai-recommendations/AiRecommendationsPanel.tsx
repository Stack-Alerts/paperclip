'use client';

export interface AiRecommendationsPanelProps {
  disabled?: boolean;
}

export function AiRecommendationsPanel(_props: AiRecommendationsPanelProps = {}) {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      AI Recommendations panel — scaffold. Owned by WebUI: Test/Optimize — AI Recommendations.
    </div>
  );
}
