'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export interface RecommendationDiffParam {
  key: string;
  before: string;
  after: string;
}

export interface RecommendationDiffProps {
  params: ReadonlyArray<RecommendationDiffParam>;
  /**
   * Test-ID prefix. Component emits
   * `${prefix}`, `${prefix}-toggle`, `${prefix}-list`,
   * `${prefix}-row`, `${prefix}-before`, `${prefix}-after`, `${prefix}-none`.
   */
  testIdPrefix?: string;
}

export function RecommendationDiff({
  params,
  testIdPrefix = 'rec-diff',
}: RecommendationDiffProps) {
  const [open, setOpen] = useState(false);
  const count = params.length;

  return (
    <div
      data-testid={testIdPrefix}
      data-open={open ? 'true' : 'false'}
      style={{ borderTop: '1px solid var(--accent-green)' }}
      className="mt-1 pt-1.5"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid={`${testIdPrefix}-toggle`}
        className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide mb-1 w-full"
        style={{ color: 'var(--accent-green-on)', background: 'transparent', border: 'none', padding: 0, cursor: 'pointer' }}
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        Applied changes ({count})
      </button>

      {open && (count > 0 ? (
        <ul className="flex flex-col gap-0.5" data-testid={`${testIdPrefix}-list`}>
          {params.map((p) => (
            <li
              key={p.key}
              className="text-[10px] font-mono flex gap-1 flex-wrap"
              data-testid={`${testIdPrefix}-row`}
            >
              <span style={{ color: 'var(--text-faint)' }}>{p.key}:</span>
              <span style={{ display: 'inline-flex', gap: 4, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span
                  data-testid={`${testIdPrefix}-before`}
                  style={{ color: 'var(--accent-red-on)', textDecoration: 'line-through' }}
                >
                  {p.before}
                </span>
                <span style={{ color: 'var(--text-faint)' }}>→</span>
                <span
                  data-testid={`${testIdPrefix}-after`}
                  style={{ color: 'var(--accent-green-on)' }}
                >
                  {p.after}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p
          className="text-[10px]"
          style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}
          data-testid={`${testIdPrefix}-none`}
        >
          No numeric parameters changed — check the strategy blocks manually.
        </p>
      ))}
    </div>
  );
}