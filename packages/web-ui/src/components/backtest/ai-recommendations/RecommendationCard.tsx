'use client';

import {
  RECOMMENDATION_CATEGORY_PALETTE,
  RecommendationCategoryId,
} from './recommendationCategoryPalette';
import {
  RecommendationDiff,
  RecommendationDiffParam,
} from './RecommendationDiff';

/** The always-visible "THE CHANGE" block from the approved mockup: a context
 * line (e.g. "At 1hod exit · ABSOLUTE") plus a red `- old` / green `+ new`
 * diff pair. */
export interface RecommendationChange {
  contextLine: string;
  oldLine: string;
  newLine: string;
}

/** The three-metric footer from the mockup, formatted by the caller, e.g.
 * `{ wr: '+8 WR', dd: '+34 DD', pl: '+$1,640 P/L' }`. */
export interface RecommendationFooterMetrics {
  wr: string;
  dd: string;
  pl: string;
}

export interface RecommendationCardData {
  id: string;
  categoryId: RecommendationCategoryId;
  categoryLabel?: string;
  /** Caller-formatted delta string shown as the top-right pill, e.g. "+8%". */
  deltaLabel: string;
  deltaNegative?: boolean;
  title: string;
  description: string;
  /** Legacy raw code lines. Retained for the deterministic storybook harness;
   * superseded by `change` on the live panel. */
  codeLines?: string[];
  /** Mockup "THE CHANGE" section: context line + before/after diff. */
  change?: RecommendationChange;
  /** Mockup "Affects" lineage line, e.g. "Asia 50% → At 1hod". */
  affectsLine?: string;
  /** Mockup footer metric triplet (+WR ±DD ±$P/L). */
  footerMetrics?: RecommendationFooterMetrics;
  /**
   * Reverse-view / insight card: renders with no toggle, an "Insight only"
   * pill, and a highlighted note box instead of a diff.
   */
  insight?: boolean;
  /** Highlighted note box text used when `insight` is true. */
  insightBox?: string;
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
   * Kept for parity with the parent panel's per-analysis keying even though
   * the card face no longer renders inline feedback controls.
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
  change,
  affectsLine,
  footerMetrics,
  insight = false,
  insightBox,
  applied,
  onToggleApplied,
  disabled = false,
  dataAttributes,
  appliedDiff,
  conflictBadge,
}: RecommendationCardData) {
  const tone = RECOMMENDATION_CATEGORY_PALETTE[categoryId];
  const deltaFg = deltaNegative ? 'var(--accent-red-on)' : 'var(--accent-green-on)';
  const deltaBg = deltaNegative ? 'var(--accent-red-soft)' : 'var(--accent-green-soft)';

  return (
    <article
      data-testid={`rec-card-${id}`}
      data-applied={applied ? 'true' : 'false'}
      data-insight={insight ? 'true' : 'false'}
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
              data-testid="ai-recs-conflict-badge"
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
          style={
            insight
              ? { background: tone.bg, color: tone.fg, border: `1px solid ${tone.fg}` }
              : { background: deltaBg, color: deltaFg, border: `1px solid ${deltaFg}` }
          }
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
            WebkitLineClamp: 4,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {description}
        </p>
      </div>

      {insight ? (
        <div
          data-testid={`rec-card-${id}-insight-box`}
          className="text-[11px] mx-3 mb-2 rounded p-2 leading-snug"
          style={{
            background: tone.codeTint,
            color: 'var(--text-secondary)',
            border: `1px solid ${tone.fg}`,
            flex: '1 1 auto',
          }}
        >
          {insightBox ?? (codeLines ? codeLines.join('\n') : '')}
        </div>
      ) : change ? (
        <div
          data-testid={`rec-card-${id}-change`}
          className="mx-3 mb-2 flex flex-col gap-1"
          style={{ flex: '1 1 auto' }}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[9px] font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-faint)' }}
            >
              The change
            </span>
            <span className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>
              {change.contextLine}
            </span>
          </div>
          <div
            className="rounded overflow-hidden"
            style={{
              border: '1px solid var(--border)',
              fontFamily: 'var(--font-mono, monospace)',
              background: applied ? tone.codeTint : 'var(--bg-elevated)',
            }}
          >
            <div
              className="text-[11px] px-2 py-1 whitespace-pre-wrap break-words"
              style={{ color: 'var(--accent-red-on)', background: 'var(--accent-red-soft)' }}
            >
              {`- ${change.oldLine}`}
            </div>
            <div
              className="text-[11px] px-2 py-1 whitespace-pre-wrap break-words"
              style={{ color: 'var(--accent-green-on)', background: 'var(--accent-green-soft)' }}
            >
              {`+ ${change.newLine}`}
            </div>
          </div>
        </div>
      ) : (
        <pre
          data-testid={`rec-card-${id}-code`}
          className="text-[11px] mx-3 mb-2 rounded p-2 overflow-auto whitespace-pre-wrap break-words"
          style={{
            background: applied ? tone.codeTint : 'var(--bg-elevated)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
            flex: '1 1 auto',
          }}
        >
          {(codeLines ?? []).join('\n')}
        </pre>
      )}

      {affectsLine !== undefined && (
        <div
          data-testid={`rec-card-${id}-affects`}
          className="flex items-center gap-2 px-3 pb-2"
        >
          <span
            className="text-[9px] font-semibold uppercase tracking-wider"
            style={{ color: 'var(--text-faint)' }}
          >
            Affects
          </span>
          <span
            className="text-[10px] rounded px-1.5 py-0.5"
            style={{
              color: 'var(--text-muted)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
            }}
          >
            {affectsLine}
          </span>
        </div>
      )}

      <footer
        className="flex items-center justify-between gap-2 px-3 py-2"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <div
          data-testid={`rec-card-${id}-metrics`}
          className="flex items-center gap-2 text-[11px] font-medium"
          style={{ color: 'var(--text-secondary)' }}
        >
          {footerMetrics ? (
            <>
              <span>{footerMetrics.wr}</span>
              <span style={{ color: 'var(--text-faint)' }}>·</span>
              <span>{footerMetrics.dd}</span>
              <span style={{ color: 'var(--text-faint)' }}>·</span>
              <span>{footerMetrics.pl}</span>
            </>
          ) : (
            <span style={{ color: 'var(--text-faint)' }}>—</span>
          )}
        </div>

        {insight ? (
          <span
            data-testid={`rec-card-${id}-insight-pill`}
            className="text-[10px] uppercase tracking-wide rounded px-1.5 py-0.5"
            style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
          >
            Insight only
          </span>
        ) : (
          <label
            className="inline-flex items-center gap-2 text-[11px]"
            style={{ color: 'var(--text-muted)', cursor: disabled ? 'not-allowed' : 'pointer' }}
          >
            {/* testability marker — hidden visually, read by tests via data-testid */}
            <span data-testid="ai-recs-toggle-badge" style={{ display: 'none' }}>
              {applied ? 'ON' : 'OFF'}
            </span>
            <span
              className="text-[10px] uppercase tracking-wide"
              style={{ color: applied ? tone.fg : 'var(--text-faint)' }}
            >
              {applied ? 'On' : 'Off'}
            </span>
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
        )}
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
