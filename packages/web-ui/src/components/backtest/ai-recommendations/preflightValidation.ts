/**
 * BTCAAAAA-38466 (Stream 5, B2): preflight validation state machine for
 * AiRecommendationsPanel.
 *
 * Before sending a request to the AI provider, the panel checks four
 * preconditions and surfaces a distinct banner for each failure. Each
 * banner has a clear, one-click path to the fix:
 *
 *   - no-trades     → button that scrolls to the Run Backtest button
 *   - no-provider   → button that navigates to Settings -> AI
 *   - timeout       → Retry button (re-runs the analyze)
 *   - unparseable   → Copy Response button (manual paste into another tool)
 *
 * This module is pure: classifyPreflight() takes a context object and
 * returns a discriminated-union PreflightState. The panel uses that to
 * decide which banner to render. Helpers scrollToBacktestButton() and
 * isUnparseableResponse() are exported so the component can wire the
 * one-click affordances without coupling to the DOM or parser internals.
 *
 * Keeping the classification pure makes it unit-testable without jsdom or
 * network mocks; the panel owns the side effects.
 */

export type PreflightState =
  | { kind: 'none' }
  | { kind: 'no-trades' }
  | { kind: 'no-provider'; providerLabel: string }
  | { kind: 'timeout'; durationMs: number }
  | { kind: 'unparseable'; raw: string };

export type PreflightErrorKind = 'timeout' | 'http' | 'network' | 'unknown';

export interface PreflightError {
  message: string;
  kind: PreflightErrorKind;
}

export interface PreflightContext {
  /** False during SSR / first paint — caller should render nothing until true. */
  hydrated: boolean;
  /** True when the most recent backtest produced at least one trade. */
  hasTrades: boolean;
  /** True when an AI provider is selected and (if required) has an API key. */
  hasProvider: boolean;
  /** Display label for the configured provider (used in the no-provider banner). */
  providerLabel: string;
  /** Most recent analyze request error, or null if the last attempt succeeded. */
  lastError: PreflightError | null;
  /** Wall-clock duration of the most recent analyze request, in ms. */
  lastDurationMs: number | null;
  /** Raw text from the most recent successful HTTP response (post-parse). */
  lastRawResponse: string | null;
  /** Result of parsing the most recent response with parseAnalysisResponse. */
  lastParseResult: { diagnosis: string; recommendations: string } | null;
}

const UNPARSEABLE_MIN_LENGTH = 30;

/**
 * Classify the current preflight state from the supplied context.
 *
 * Order of checks is intentional:
 *   1. Not yet hydrated → no banner (avoid SSR / first-paint flash).
 *   2. No trades        → blocks the whole flow; the user must backtest first.
 *   3. No provider      → blocks the whole flow; the user must set one up.
 *   4. Timeout          → recoverable, the user can retry.
 *   5. Unparseable      → the user can copy the raw text and try elsewhere.
 *
 * Generic errors (HTTP, network, unknown) fall through to the existing
 * analysisError banner — they're already shown verbatim by the panel.
 */
export function classifyPreflight(ctx: PreflightContext): PreflightState {
  if (!ctx.hydrated) return { kind: 'none' };
  if (!ctx.hasTrades) return { kind: 'no-trades' };
  if (!ctx.hasProvider) {
    return { kind: 'no-provider', providerLabel: ctx.providerLabel };
  }
  if (ctx.lastError?.kind === 'timeout') {
    return { kind: 'timeout', durationMs: ctx.lastDurationMs ?? 0 };
  }
  if (
    ctx.lastRawResponse !== null &&
    ctx.lastParseResult !== null &&
    isUnparseableResponse(ctx.lastRawResponse, ctx.lastParseResult)
  ) {
    return { kind: 'unparseable', raw: ctx.lastRawResponse };
  }
  return { kind: 'none' };
}

/**
 * A response is "unparseable" when the raw text is non-empty but the
 * parser could not extract either a diagnosis or a recommendations section.
 *
 * This catches truncated replies, refusals ("I can't help with that"),
 * and any model output that doesn't include the expected DIAGNOSIS:
 * and RECOMMENDATIONS: headers AND has no numbered list to fall back on.
 */
export function isUnparseableResponse(
  raw: string,
  parsed: { diagnosis: string; recommendations: string },
): boolean {
  const trimmed = raw.trim();
  if (trimmed.length === 0) return false;
  if (trimmed.length < UNPARSEABLE_MIN_LENGTH) return true;
  return parsed.diagnosis.trim() === '' && parsed.recommendations.trim() === '';
}

/**
 * Scroll the Run Backtest button into view.
 *
 * ValidationPanel.tsx wraps the Run Backtest button in an InfoTooltip with
 * id="run-backtest-btn", so the existing DOM id is the stable target. We
 * intentionally do not add a data-testid to ValidationPanel because that
 * would cross the strategy-builder window boundary; the InfoTooltip id is
 * already public.
 */
export function scrollToBacktestButton(): boolean {
  if (typeof document === 'undefined') return false;
  const el = document.getElementById('run-backtest-btn');
  if (!el) return false;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  return true;
}

/**
 * Default path for the Settings -> AI entry point. Mirrors the
 * AiProviderStatusBanner default (BTCAAAAA-38464, Stream 3 H1).
 */
export const DEFAULT_SETTINGS_HREF = '/settings';
