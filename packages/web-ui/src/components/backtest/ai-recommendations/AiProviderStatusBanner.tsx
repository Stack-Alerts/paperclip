'use client';

import { useRouter } from 'next/navigation';
import { useAiProviderAvailability } from '@/hooks/useAiProviderAvailability';

export interface AiProviderStatusBannerProps {
  /**
   * Optional override for the navigation target. Defaults to '/settings', which
   * renders the AI Recommendations card as the first card on the Settings page.
   * Anchor links (e.g. '#ai-recommendations') are tolerated by Next.js' router
   * but are not required for the one-click contract.
   */
  settingsHref?: string;
}

/**
 * BTCAAAAA-38464 (Stream 3, H1): "Why is AI off?" banner.
 *
 * Closes the H1 gap from the BTC-36465 board-facing analysis: the AI
 * recommendations panel used to render a plain-text warning when no provider
 * was configured, with no path forward. Users had to discover Settings -> AI
 * on their own. This banner surfaces the reason ("provider not configured" or
 * "provider needs an API key") and routes the user to the fix in a single
 * click.
 *
 * Renders nothing until the underlying `useAiSettings` hook has hydrated
 * from localStorage (avoids a flash of "no provider" during SSR / first
 * paint). Once hydrated, renders synchronously — guaranteed to appear within
 * 500ms of the panel mounting in a browser environment.
 */
export function AiProviderStatusBanner({
  settingsHref,
}: AiProviderStatusBannerProps = {}) {
  const router = useRouter();
  const {
    hydrated,
    hasProvider,
    providerLabel,
    missingApiKey,
    settingsHref: derivedHref,
  } = useAiProviderAvailability();

  if (!hydrated || hasProvider) {
    return null;
  }

  const href = settingsHref ?? derivedHref;
  const message = missingApiKey
    ? `${providerLabel} requires an API key to send recommendations.`
    : 'No AI provider is configured.';

  const handleClick = () => {
    router.push(href);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      router.push(href);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      data-testid="ai-recs-provider-banner"
      aria-label="Open Settings to configure the AI provider"
      className="block w-full rounded p-2 text-xs text-left transition-colors"
      style={{
        background: 'var(--bg-elevated)',
        color: 'var(--accent-orange)',
        border: '1px solid var(--accent-orange)',
        cursor: 'pointer',
      }}
      title="Open Settings -> AI"
    >
      <div className="font-semibold">Why is AI off?</div>
      <div className="mt-0.5">{message}</div>
      <div className="mt-1 underline">Open Settings -&gt; AI</div>
    </button>
  );
}
