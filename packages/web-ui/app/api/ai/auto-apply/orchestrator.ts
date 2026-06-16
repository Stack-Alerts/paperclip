/**
 * Proxy the webui's "Apply all recommendations" action into the Python
 * AutoApplyOrchestrator (BTCAAAAA-36744) via the FastAPI service
 * (BTCAAAAA-36779). The route is intentionally thin: the orchestrator
 * already owns backup → classify → apply → verify (rolls back on failure)
 * → mark_applied, so the webui only forwards the recs and a strategyId.
 *
 * Pure function: no `process.env` reads, no localStorage, no module-scope
 * fetch — all dependencies are injected so the unit test can mock the
 * transport without monkey-patching globals.
 */

export interface AutoApplyRec {
  rec_id: string;
  type: string;
  // The orchestrator is permissive about additional fields (priority,
  // rationale, suggested_value, opt_in_destructive, ...). We keep this
  // type loose so forward-compatible shapes pass through unchanged.
  [key: string]: unknown;
}

export interface AutoApplyRequest {
  strategyId: string;
  recs: AutoApplyRec[];
  optInDestructiveIds: string[] | null;
}

export interface AutoApplyStrategyPayload {
  // Mirrors the webui Strategy shape returned by FastAPI
  // (_build_sb_strategy). Only the fields the panel reads are typed.
  id: string;
  name: string;
  strategyType: string;
  [key: string]: unknown;
}

export interface AutoApplyDryRunEntry {
  rec_id: string;
  classification: string;
  [key: string]: unknown;
}

export interface AutoApplyResult {
  ok: boolean;
  strategy?: AutoApplyStrategyPayload;
  dryRun?: { entries: AutoApplyDryRunEntry[]; applicable_count: number };
  apply?: { applied: Array<{ rec_id: string }>; applied_count: number };
  error?: string;
  detail?: string;
}

export interface AutoApplyDeps {
  fetch: typeof fetch;
  baseUrl: string;
  /**
   * Optional upstream JWT forwarded to FastAPI's `Depends(require_jwt)`.
   * Must be the raw header value (e.g. `"Bearer eyJ..."`) — the route
   * extracts it from the incoming Next.js request and passes it through
   * unchanged. Omit only in tests / local CLI usage.
   */
  authHeader?: string | null;
}

export async function runAutoApply(
  req: AutoApplyRequest,
  deps: AutoApplyDeps,
): Promise<AutoApplyResult> {
  const { fetch, baseUrl, authHeader } = deps;
  const url = `${baseUrl.replace(/\/+$/, '')}/strategy-builder/strategies/${encodeURIComponent(req.strategyId)}/auto-apply`;

  const headers: Record<string, string> = {
    'content-type': 'application/json',
  };
  if (authHeader) {
    headers['authorization'] = authHeader;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        recs: req.recs ?? [],
        opt_in_destructive_ids: req.optInDestructiveIds ?? null,
      }),
    });
  } catch (err) {
    return {
      ok: false,
      error: 'Could not reach the FastAPI service.',
      detail: err instanceof Error ? err.message : String(err),
    };
  }

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // Non-JSON error body (e.g. reverse-proxy 502). Fall through with
    // the status text as the error.
  }

  if (!res.ok) {
    const detail = (body as { detail?: string } | null)?.detail;
    return {
      ok: false,
      error: `Auto-apply returned HTTP ${res.status}.`,
      detail: typeof detail === 'string' ? detail : res.statusText,
    };
  }

  const payload = body as {
    strategy?: AutoApplyStrategyPayload;
    dry_run?: { entries: AutoApplyDryRunEntry[]; applicable_count: number };
    apply?: { applied: Array<{ rec_id: string }>; applied_count: number };
  } | null;
  if (!payload || typeof payload !== 'object') {
    return {
      ok: false,
      error: 'Auto-apply response was empty or malformed.',
    };
  }

  return {
    ok: true,
    ...(payload.strategy ? { strategy: payload.strategy } : {}),
    ...(payload.dry_run ? { dryRun: payload.dry_run } : {}),
    ...(payload.apply ? { apply: payload.apply } : {}),
  };
}
