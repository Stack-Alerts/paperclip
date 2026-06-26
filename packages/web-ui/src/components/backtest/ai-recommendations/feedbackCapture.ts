/**
 * Per-card thumbs up/down feedback capture for AI Recommendations (Stream 7).
 *
 * Persists feedback in `sessionStorage` keyed by `ai-recs-feedback:<analysisId>:<recId>`
 * and publishes the full map on `window.__AI_RECS_FEEDBACK__` for future backend scraping.
 * Frontend-only by design — no network call.
 */

export type FeedbackValue = 'up' | 'down';

export type FeedbackMap = Record<string, FeedbackValue>;

const FEEDBACK_PREFIX = 'ai-recs-feedback:';
const WINDOW_GETTER_KEY = '__AI_RECS_FEEDBACK__';
const VALID_VALUES: readonly FeedbackValue[] = ['up', 'down'];

function getSessionStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function storageKey(analysisId: string, recId: string): string {
  return `${FEEDBACK_PREFIX}${analysisId}:${recId}`;
}

/**
 * Splits a composite key `<analysisId>:<recId>` back into its parts. Splits on the
 * FIRST colon so composite analysis IDs or rec IDs that contain colons survive.
 */
export function parseCompositeKey(compositeKey: string): { analysisId: string; recId: string } | null {
  if (typeof compositeKey !== 'string') return null;
  const idx = compositeKey.indexOf(':');
  if (idx <= 0 || idx === compositeKey.length - 1) return null;
  return {
    analysisId: compositeKey.slice(0, idx),
    recId: compositeKey.slice(idx + 1),
  };
}

function isFeedbackValue(value: unknown): value is FeedbackValue {
  return typeof value === 'string' && (VALID_VALUES as readonly string[]).includes(value);
}

export function isValidFeedbackValue(value: unknown): value is FeedbackValue {
  return isFeedbackValue(value);
}

function readStorage(): FeedbackMap {
  const storage = getSessionStorage();
  if (!storage) return {};
  const out: FeedbackMap = {};
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (!key || !key.startsWith(FEEDBACK_PREFIX)) continue;
    const compositeKey = key.slice(FEEDBACK_PREFIX.length);
    const raw = storage.getItem(key);
    if (isFeedbackValue(raw)) {
      out[compositeKey] = raw;
    }
  }
  return out;
}

export function getFeedback(analysisId: string, recId: string): FeedbackValue | null {
  const storage = getSessionStorage();
  if (!storage) return null;
  const raw = storage.getItem(storageKey(analysisId, recId));
  return isFeedbackValue(raw) ? raw : null;
}

export function setFeedback(analysisId: string, recId: string, value: FeedbackValue): FeedbackMap {
  const storage = getSessionStorage();
  if (!storage) return readStorage();
  if (!isFeedbackValue(value)) return readStorage();
  storage.setItem(storageKey(analysisId, recId), value);
  const map = readStorage();
  refreshWindowGetter(map);
  return map;
}

export function clearFeedback(analysisId: string, recId: string): FeedbackMap {
  const storage = getSessionStorage();
  if (!storage) return readStorage();
  storage.removeItem(storageKey(analysisId, recId));
  const map = readStorage();
  refreshWindowGetter(map);
  return map;
}

export function getAllFeedback(): FeedbackMap {
  return readStorage();
}

export function refreshWindowGetter(map: FeedbackMap = readStorage()): void {
  if (typeof window === 'undefined') return;
  try {
    (window as unknown as Record<string, unknown>)[WINDOW_GETTER_KEY] = map;
  } catch {
    // Best effort — the getter is opportunistic, not load-bearing.
  }
}

let installed = false;
export function installWindowGetter(): void {
  if (installed) return;
  if (typeof window === 'undefined') return;
  installed = true;
  try {
    Object.defineProperty(window, WINDOW_GETTER_KEY, {
      configurable: true,
      enumerable: false,
      get: () => readStorage(),
    });
  } catch {
    // If defineProperty fails (already defined as a data prop, e.g. in tests),
    // fall back to a direct assignment that always reflects the current map.
    refreshWindowGetter();
  }
}

if (typeof window !== 'undefined') {
  installWindowGetter();
}

export const __internal = {
  FEEDBACK_PREFIX,
  WINDOW_GETTER_KEY,
  isFeedbackValue,
};
