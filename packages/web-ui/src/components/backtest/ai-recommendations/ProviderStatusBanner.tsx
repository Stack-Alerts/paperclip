/**
 * ProviderStatusBanner — thin re-export of AiProviderStatusBanner.
 *
 * This file exists so the split-panel orchestrator can import a
 * semantically-named module without changing the canonical implementation
 * in AiProviderStatusBanner.tsx.
 */
export {
  AiProviderStatusBanner as ProviderStatusBanner,
  type AiProviderStatusBannerProps as ProviderStatusBannerProps,
} from './AiProviderStatusBanner';
