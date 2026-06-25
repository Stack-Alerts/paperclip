'use client';

import { getProviderMeta, useAiSettings } from '@/hooks/useAiSettings';

export interface AiProviderAvailability {
  /**
   * False until `useAiSettings` has read localStorage on mount. Callers should
   * render a neutral placeholder (no banner, no "missing key" warning) while
   * `hydrated === false` to avoid a flash of incorrect state on first paint.
   */
  hydrated: boolean;
  /**
   * True when the selected provider is ready to receive a request:
   * - providers that do not require an API key (claude-code, ollama) are
   *   always ready once hydrated
   * - providers that DO require an API key (anthropic, openai, openrouter,
   *   deepseek) are ready only when a non-empty key is present
   */
  hasProvider: boolean;
  /** Display label for the currently selected provider, e.g. "Anthropic API". */
  providerLabel: string;
  /** Link target for the "open Settings" action in `AiProviderStatusBanner`. */
  settingsHref: string;
  /** Whether the currently selected provider requires an API key. */
  requiresApiKey: boolean;
  /**
   * Convenience flag: `requiresApiKey && !hasApiKey`. Lets the banner
   * distinguish "no provider selected" from "provider selected but no key".
   */
  missingApiKey: boolean;
}

/**
 * BTCAAAAA-38464 (Stream 3, H1): one-call view of "is the AI provider ready?".
 *
 * Lifts the inline `useAiSettings` + `getProviderMeta` + `hasProvider` derivation
 * out of `AiRecommendationsPanel.tsx` (formerly at lines 1788–1793) so the panel
 * and the new `AiProviderStatusBanner` agree on a single source of truth. Adding
 * the banner later does not require touching the panel's provider-readiness
 * branch.
 *
 * The hook is intentionally read-only — it never mutates `useAiSettings`. The
 * Settings page owns the editing surface; this hook just reports the state.
 */
export function useAiProviderAvailability(): AiProviderAvailability {
  const { settings, hydrated } = useAiSettings();

  if (!hydrated) {
    return {
      hydrated: false,
      hasProvider: false,
      providerLabel: '',
      settingsHref: '/settings',
      requiresApiKey: false,
      missingApiKey: false,
    };
  }

  const meta = getProviderMeta(settings.provider);
  const apiKey = settings.apiKeys[settings.provider]?.trim() ?? '';
  const hasApiKey = apiKey.length > 0;
  const ready = !meta.requiresApiKey || hasApiKey;

  return {
    hydrated: true,
    hasProvider: ready,
    providerLabel: meta.label,
    settingsHref: '/settings',
    requiresApiKey: meta.requiresApiKey,
    missingApiKey: meta.requiresApiKey && !hasApiKey,
  };
}
