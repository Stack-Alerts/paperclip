'use client';

import { useCallback, useState } from 'react';
import { ArrowRight, ThumbsDown, ThumbsUp } from 'lucide-react';
import {
  RECOMMENDATION_CATEGORY_PALETTE,
  RecommendationCategoryId,
} from './recommendationCategoryPalette';
import {
  RecommendationDiff,
  RecommendationDiffParam,
} from './RecommendationDiff';
import { FeedbackValue, getFeedback, setFeedback } from './feedbackCapture';

export interface RecommendationCardData {
  id: string;
  categoryId: RecommendationCategoryId;
  categoryLabel?: string;
  /** Caller-formatted delta string, e.g. "+2.3%". */
  deltaLabel: string;
  deltaNegative?: boolean;
  title: string;
  description: string;
  codeLines: string[];
  onApplyOnChart?: () => void;
  applied: boolean;
  onToggleApplied: (next: boolean) => void;
  disabled?: boolean;
  /** Optional extra data-* attributes applied to the card root. Used by the
   * parent panel to preserve the `ai-recs-toggle-card` testid and the
   * `data-rec-id` attribute that StrategyAfterChangesRail's CSS-selector
   * scroll-into-view contract depends on. */
  dataAttributes?: Record<string, string>;
  /** Per-parameter before/after deltas — rendered as a collapsed diff when applied. */
  appliedDiff?: ReadonlyArray<RecommendationDiffParam>;
  /**
   * Stable identifier for the analysis that produced this recommendation.
   * Combined with `id` to key per-card feedback in sessionStorage. Frontend
   * contract from BTCAAAAA-38468 — backend scraping reads via
   * `window.__AI_RECS_FEEDBACK__`.
   */
  analysisId: string;
  /** Optional badge rendered in the card header to flag a rec that lost a same-param conflict. */
  conflictBadge?: { label: string; tooltip?: string };
}

export function RecommendationCard({
  id,
  categoryId,
  categoryLabel,
  deltaLabel,
  deltaNegative = false,
  title,
  description,
  codeLines,
  onApplyOnChart,
  applied,
  onToggleApplied,
  disabled = false,
  dataAttributes,
  appliedDiff,
  analysisId,
  conflictBadge,
}: RecommendationCardData) {
  const tone = RECOMMENDATION_CATEGORY_PALETTE[categoryId];
  const deltaFg = deltaNegative ? 'var(--accent-red-on)' : 'var(--accent-green-on)';
  const deltaBg = deltaNegative ? 'var(--accent-red-soft)' : 'var(--accent-green-soft)';

  const [feedback, setFeedbackState] = useState<FeedbackValue | null>(() =>
    getFeedback(analysisId, id),
  );

  const handleThumb = useCallback(
    (value: FeedbackValue) => {
      setFeedback(analysisId, id, value);
      setFeedbackState(value);
    },
    [analysisId, id],
  );

  return (
    <article
      data-testid={`rec-card-${id}`}
      data-applied={applied ? 'true' : 'false'}
      {...(dataAttributes ?? {})}
      className="flex flex-col rounded h-full"
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${applied ? tone.glow : 'var(--border)'}`,
        boxShadow: applied ? `0 0 0 1px ${tone.glow}` : 'none',
        transition: 'box-shadow 120ms ease, border-color 120ms ease',
      }}
    >
      <header className="flex items-center justify-between gap-2 px-3 pt-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            data-testid={`rec-card-${id}-category`}
            className="text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
            style={{ background: tone.bg, color: tone.fg, border: `1px solid ${tone.fg}` }}
          >
            {categoryLabel ?? tone.label}
          </span>
          {conflictBadge && (
            <span
              data-testid={`rec-card-${id}-conflict`}
              data-conflict-loser="true"
              className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--accent-amber-soft, #fef3c7)',
                color: 'var(--accent-amber-on, #92400e)',
                border: '1px solid var(--accent-amber-on, #d97706)',
              }}
              title={conflictBadge.tooltip}
            >
              {conflictBadge.label}
            </span>
          )}
        </div>
        <span
          data-testid={`rec-card-${id}-delta`}
          className="text-[10px] font-semibold rounded px-1.5 py-0.5"
          style={{ background: deltaBg, color: deltaFg, border: `1px solid ${deltaFg}` }}
        >
          {deltaLabel}
        </span>
      </header>

      <div className="px-3 pt-2 pb-2 flex flex-col gap-1">
        <h3
          className="text-sm font-semibold"
          style={{ color: 'var(--text-primary, var(--text-secondary))' }}
        >
          {title}
        </h3>
        <p
          className="text-xs leading-snug"
          style={{
            color: 'var(--text-muted)',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {description}
        </p>
      </div>

      <pre
        data-testid={`rec-card-${id}-code`}
        className="text-[11px] mx-3 mb-3 rounded p-2 overflow-auto whitespace-pre-wrap break-words"
        style={{
          background: applied ? tone.codeTint : 'var(--bg-elevated)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
          fontFamily: 'var(--font-mono, monospace)',
          flex: '1 1 auto',
        }}
      >
        {codeLines.join('\n')}
      </pre>

      <footer
        className="flex flex-col gap-1.5 px-3 py-2"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={onApplyOnChart}
            disabled={!onApplyOnChart}
            data-testid={`rec-card-${id}-apply-on-chart`}
            className="flex items-center gap-1 text-[11px] font-medium"
            style={{
              color: 'var(--accent-blue)',
              background: 'transparent',
              border: 'none',
              padding: 0,
              cursor: onApplyOnChart ? 'pointer' : 'default',
              opacity: onApplyOnChart ? 1 : 0.5,
            }}
          >
            apply on chart
            <ArrowRight size={12} />
          </button>

          <label
            className="inline-flex items-center gap-2 text-[11px]"
            style={{ color: 'var(--text-muted)', cursor: disabled ? 'not-allowed' : 'pointer' }}
          >
            <span>Apply</span>
            <span style={{ position: 'relative', display: 'inline-block', width: 28, height: 16 }}>
              <input
                type="checkbox"
                checked={applied}
                disabled={disabled}
                onChange={(e) => onToggleApplied(e.target.checked)}
                data-testid={`rec-card-${id}-toggle`}
                aria-label={`Apply ${title}`}
                style={{
                  appearance: 'none',
                  width: 28,
                  height: 16,
                  borderRadius: 999,
                  background: applied ? tone.glow : 'var(--bg-elevated)',
                  border: `1px solid ${applied ? tone.glow : 'var(--border)'}`,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  opacity: disabled ? 0.5 : 1,
                  transition: 'background 120ms ease, border-color 120ms ease',
                  margin: 0,
                }}
              />
              <span
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  top: 2,
                  left: applied ? 14 : 2,
                  width: 12,
                  height: 12,
                  borderRadius: 999,
                  background: '#fff',
                  transition: 'left 120ms ease',
                  pointerEvents: 'none',
                }}
              />
            </span>
          </label>
        </div>

        <div
          className="flex items-center justify-between gap-2"
          data-testid={`rec-card-${id}-feedback`}
          data-feedback={feedback ?? 'none'}
        >
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
            Was this helpful?
          </span>
          <div className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => handleThumb('up')}
              aria-label={`Mark ${title} as helpful`}
              aria-pressed={feedback === 'up'}
              data-testid={`rec-card-${id}-thumb-up`}
              className="inline-flex items-center justify-center rounded"
              style={{
                width: 24,
                height: 22,
                padding: 0,
                border: `1px solid ${feedback === 'up' ? tone.fg : 'var(--border)'}`,
                background: feedback === 'up' ? tone.bg : 'transparent',
                color: feedback === 'up' ? tone.fg : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'background 120ms ease, border-color 120ms ease, color 120ms ease',
              }}
            >
              <ThumbsUp size={12} />
            </button>
            <button
              type="button"
              onClick={() => handleThumb('down')}
              aria-label={`Mark ${title} as not helpful`}
              aria-pressed={feedback === 'down'}
              data-testid={`rec-card-${id}-thumb-down`}
              className="inline-flex items-center justify-center rounded"
              style={{
                width: 24,
                height: 22,
                padding: 0,
                border: `1px solid ${feedback === 'down' ? 'var(--accent-red-on)' : 'var(--border)'}`,
                background:
                  feedback === 'down' ? 'var(--accent-red-soft)' : 'transparent',
                color:
                  feedback === 'down' ? 'var(--accent-red-on)' : 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'background 120ms ease, border-color 120ms ease, color 120ms ease',
              }}
            >
              <ThumbsDown size={12} />
            </button>
          </div>
        </div>
      </footer>

      {applied && appliedDiff && (
        <div className="px-3 pb-2">
          <RecommendationDiff
            params={appliedDiff}
            testIdPrefix={`rec-card-${id}-diff`}
          />
        </div>
      )}
    </article>
  );
}
