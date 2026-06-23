'use client';

import { ReverseViewPattern } from './reverseViewPattern';

export interface ReverseViewBannerProps {
  pattern: ReverseViewPattern;
}

export function ReverseViewBanner({ pattern }: ReverseViewBannerProps) {
  const hasSample = pattern.sampleSize > 0;
  const upliftPositive = pattern.avgUplift >= 0;

  return (
    <section
      data-testid="reverse-view-banner"
      className="rounded p-3 flex flex-col gap-2 w-full"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <h3
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-secondary)' }}
        >
          Reverse view — what the winners share
        </h3>
        {hasSample && (
          <span
            data-testid="reverse-view-banner-uplift"
            className="text-[10px] font-semibold rounded px-1.5 py-0.5"
            style={{
              background: upliftPositive
                ? 'var(--accent-green-soft)'
                : 'var(--accent-red-soft)',
              color: upliftPositive
                ? 'var(--accent-green-on)'
                : 'var(--accent-red-on)',
              border: `1px solid ${
                upliftPositive
                  ? 'var(--accent-green-on)'
                  : 'var(--accent-red-on)'
              }`,
            }}
          >
            {formatUplift(pattern.avgUplift)}
          </span>
        )}
      </header>

      <p
        data-testid="reverse-view-banner-headline"
        className="text-xs"
        style={{ color: 'var(--text-muted)' }}
      >
        {pattern.headline}
      </p>

      {hasSample && (
        <dl
          className="grid gap-x-2 gap-y-1 text-[11px]"
          style={{ gridTemplateColumns: 'auto 1fr' }}
        >
          <dt
            className="font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-faint)' }}
          >
            Categories
          </dt>
          <dd
            data-testid="reverse-view-banner-categories"
            style={{ color: 'var(--text-secondary)' }}
          >
            {pattern.topCategories.length > 0
              ? pattern.topCategories.join(' · ')
              : '—'}
          </dd>
          <dt
            className="font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-faint)' }}
          >
            Params
          </dt>
          <dd
            data-testid="reverse-view-banner-params"
            className="font-mono"
            style={{ color: 'var(--text-secondary)' }}
          >
            {pattern.topParamKeys.length > 0
              ? pattern.topParamKeys.join(' · ')
              : '—'}
          </dd>
        </dl>
      )}
    </section>
  );
}

function formatUplift(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}
