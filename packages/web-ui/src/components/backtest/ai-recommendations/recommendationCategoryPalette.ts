/**
 * Verbatim category palette derived from BTCAAAAA-37748 mockups 1 and 2
 * (Current Analysis base + applied states). Q5 locks these to the mockup —
 * any change to the tones below requires explicit board approval per the
 * "ABSOLUTELY NO DEVIATION" rule on the parent issue.
 */

export type RecommendationCategoryId =
  | 'risk'
  | 'entry'
  | 'exit'
  | 'signal'
  | 'regime';

export interface RecommendationCategoryTone {
  bg: string;
  fg: string;
  glow: string;
  codeTint: string;
  label: string;
}

export const RECOMMENDATION_CATEGORY_PALETTE: Record<
  RecommendationCategoryId,
  RecommendationCategoryTone
> = {
  risk: {
    bg: '#1f3a4d',
    fg: '#6fd3ff',
    glow: '#6fd3ff',
    codeTint: 'rgba(111, 211, 255, 0.08)',
    label: 'risk',
  },
  entry: {
    bg: '#1f3d2c',
    fg: '#5bd98a',
    glow: '#5bd98a',
    codeTint: 'rgba(91, 217, 138, 0.08)',
    label: 'entry',
  },
  exit: {
    bg: '#3a2851',
    fg: '#c08bff',
    glow: '#c08bff',
    codeTint: 'rgba(192, 139, 255, 0.08)',
    label: 'exit',
  },
  signal: {
    bg: '#4a2f1a',
    fg: '#ff9a52',
    glow: '#ff9a52',
    codeTint: 'rgba(255, 154, 82, 0.08)',
    label: 'signal',
  },
  regime: {
    bg: '#4a1f2b',
    fg: '#ff6b8a',
    glow: '#ff6b8a',
    codeTint: 'rgba(255, 107, 138, 0.08)',
    label: 'regime',
  },
};

export function getCategoryTone(
  id: RecommendationCategoryId,
): RecommendationCategoryTone {
  return RECOMMENDATION_CATEGORY_PALETTE[id];
}
