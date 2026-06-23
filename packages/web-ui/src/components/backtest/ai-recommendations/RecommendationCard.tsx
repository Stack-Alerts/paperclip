'use client';

import { ArrowRight } from 'lucide-react';
import {
  RECOMMENDATION_CATEGORY_PALETTE,
  RecommendationCategoryId,
} from './recommendationCategoryPalette';

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
}: RecommendationCardData) {
  const tone = RECOMMENDATION_CATEGORY_PALETTE[categoryId];
  const deltaFg = deltaNegative ? 'var(--accent-red-on)' : 'var(--accent-green-on)';
  const deltaBg = deltaNegative ? 'var(--accent-red-soft)' : 'var(--accent-green-soft)';

  return (
    <article
      data-testid={`rec-card-${id}`}
      data-applied={applied ? 'true' : 'false'}
      className="flex flex-col rounded h-full"
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${applied ? tone.glow : 'var(--border)'}`,
        boxShadow: applied ? `0 0 0 1px ${tone.glow}` : 'none',
        transition: 'box-shadow 120ms ease, border-color 120ms ease',
      }}
    >
      <header className="flex items-center justify-between gap-2 px-3 pt-3">
        <span
          data-testid={`rec-card-${id}-category`}
          className="text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
          style={{ background: tone.bg, color: tone.fg, border: `1px solid ${tone.fg}` }}
        >
          {categoryLabel ?? tone.label}
        </span>
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
        className="flex items-center justify-between gap-2 px-3 py-2"
        style={{ borderTop: '1px solid var(--border)' }}
      >
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
      </footer>
    </article>
  );
}
