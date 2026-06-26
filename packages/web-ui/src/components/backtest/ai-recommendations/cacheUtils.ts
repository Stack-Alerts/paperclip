import { Strategy } from '@/lib/strategy-builder/types';

// AC21: per-strategy AI recommendations cache. Lives in sessionStorage so the
// recs + applied-state survive tab navigation, parent re-renders, and the AI
// panel remounting. AC22: only cleared on explicit user rerun
// (handleApproveAndSendClick → runApproveAndSend, and loadHistoryIntoCurrent
// when the user explicitly loads a different history entry). Keyed by
// strategyId so switching strategies does not bleed stale recs.
export const AI_RECS_CACHE_KEY = 'ai_recs_v3_cache_v1';
export const AI_RECS_CACHE_VERSION = 1;

export interface CachedAnalysis {
  version: number;
  strategyId: string | null;
  diagnosis: string;
  recommendations: string;
  raw: string;
  appliedRecIds: string[];
  // JSON-stringified Strategy per applied rec, so we can locally roll back
  // (AC18) without a server round-trip. Server-persisted rollback is a
  // follow-up backend ticket; this snapshot keeps the UX honest in the
  // meantime.
  preApplySnapshots: Array<[string, Strategy]>;
  analysisTimestamp: string;
  // BTCAAAAA-37773 / Sprint A1: hash of strategy+backtestConfig captured at
  // the time the cached analysis was produced. Used to gate the persistent
  // Re-analyze button. Optional so caches written before this field shipped
  // still parse — missing hash is treated as "unknown" → button enabled.
  analysisHash?: string;
}

export function readRecsCache(): CachedAnalysis | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(AI_RECS_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CachedAnalysis>;
    if (parsed.version !== AI_RECS_CACHE_VERSION) return null;
    if (
      typeof parsed.diagnosis !== 'string' ||
      typeof parsed.recommendations !== 'string' ||
      typeof parsed.raw !== 'string'
    ) {
      return null;
    }
    return {
      version: parsed.version,
      strategyId: parsed.strategyId ?? null,
      diagnosis: parsed.diagnosis,
      recommendations: parsed.recommendations,
      raw: parsed.raw,
      appliedRecIds: Array.isArray(parsed.appliedRecIds)
        ? parsed.appliedRecIds.filter((s): s is string => typeof s === 'string')
        : [],
      preApplySnapshots: Array.isArray(parsed.preApplySnapshots)
        ? (parsed.preApplySnapshots as Array<[string, Strategy]>)
        : [],
      analysisTimestamp:
        typeof parsed.analysisTimestamp === 'string'
          ? parsed.analysisTimestamp
          : new Date().toISOString(),
      analysisHash:
        typeof parsed.analysisHash === 'string' ? parsed.analysisHash : undefined,
    };
  } catch {
    return null;
  }
}

export function writeRecsCache(cache: CachedAnalysis | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (!cache) {
      window.sessionStorage.removeItem(AI_RECS_CACHE_KEY);
      return;
    }
    window.sessionStorage.setItem(AI_RECS_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Quota / private-mode failures are silent — the panel still works,
    // the recs just won't survive a refresh.
  }
}

/**
 * AC9: best-effort admin-role detection. The webui does not yet have a
 * server-issued roles endpoint, so we parse the auth_token (a JWT) for an
 * `admin` / `role` claim. Anything we cannot prove admin = locked out.
 */
export function readIsAdminFromAuthToken(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const token = window.localStorage.getItem('auth_token');
    if (!token) return false;
    const parts = token.split('.');
    if (parts.length < 2) return false;
    const payload = parts[1];
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(padded + '==='.slice((padded.length + 3) % 4));
    const claims = JSON.parse(json) as Record<string, unknown>;
    if (claims.admin === true) return true;
    if (claims.is_admin === true) return true;
    const role = claims.role;
    if (typeof role === 'string' && role.toLowerCase() === 'admin') return true;
    const roles = claims.roles;
    if (Array.isArray(roles) && roles.some((r) => typeof r === 'string' && r.toLowerCase() === 'admin')) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}
