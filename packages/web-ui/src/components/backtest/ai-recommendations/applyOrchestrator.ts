// Apply orchestrator — pure state transitions + async executeApply for the
// per-tile toggle in AiRecommendationsPanel.
//
// Extracted from AiRecommendationsPanel.handleToggleRec (BTCAAAAA-38462,
// "Stream 1: AI Recs apply orchestrator") so the apply/rollback/history
// logic can be unit-tested without rendering the panel and so the panel
// itself only owns React wiring.
//
// Public surface:
//   rollbackTransitions(rec, appliedRecIds, preApplySnapshots)
//   buildApplyRequest(rec, strategy, authToken)
//   parseApplyResponse(data, rec)
//   executeApply(input, deps)
//
// executeApply returns a list of state transitions the caller applies in
// order. Keeping the transitions as data (rather than reaching into
// setState directly) is what lets us assert AC15-AC22 from a Jest test
// without spinning up a React renderer.

import type { Strategy } from '@/lib/strategy-builder/types';

export interface ParsedRecLike {
  id: string;
  type: string;
  raw?: string;
  block?: string;
  signal?: string;
  parameter?: string;
  suggestedValue?: string;
}

export type PreApplySnapshot = [string, Strategy];

export interface ApplyOrchestratorInput {
  rec: ParsedRecLike;
  strategy: Strategy;
  appliedRecIds: readonly string[];
  preApplySnapshots: readonly PreApplySnapshot[];
}

export type ApplyOrchestratorTransition =
  | { kind: 'snapshot'; entry: PreApplySnapshot }
  | { kind: 'markApplying'; recId: string }
  | { kind: 'clearError'; recId: string }
  | { kind: 'markApplied'; recId: string }
  | { kind: 'markRollback'; recId: string; restoredStrategy: Strategy }
  | { kind: 'setError'; recId: string; message: string }
  | { kind: 'dropSnapshot'; recId: string };

export interface ApplyOrchestratorDeps {
  fetchFn: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  getAuthToken?: () => string | undefined;
  onHistoryStatusChange?: (
    recId: string,
    status: 'applied' | 'dismissed',
  ) => void;
  /**
   * Fired after a successful apply with the server-returned strategy.
   * The panel wires this to the parent's `onStrategyUpdated` so the
   * post-apply strategy reaches the strategy-builder without leaking
   * the raw fetch response through the transition stream.
   */
  onStrategyApplied?: (strategy: Strategy) => void;
}

export interface ExecuteApplyResult {
  transitions: ApplyOrchestratorTransition[];
  ok: boolean;
}

export function rollbackTransitions(
  rec: ParsedRecLike,
  appliedRecIds: readonly string[],
  preApplySnapshots: readonly PreApplySnapshot[],
): { kind: 'markRollback'; recId: string; restoredStrategy: Strategy } | null {
  if (!appliedRecIds.includes(rec.id)) return null;
  const snapshotEntry = preApplySnapshots.find(([id]) => id === rec.id);
  if (!snapshotEntry) return null;
  return {
    kind: 'markRollback',
    recId: rec.id,
    restoredStrategy: snapshotEntry[1],
  };
}

export function buildApplyRequest(
  rec: ParsedRecLike,
  strategy: Strategy,
  authToken: string | undefined,
): { url: string; init: RequestInit } {
  const headers: Record<string, string> = {
    'content-type': 'application/json',
  };
  if (authToken) headers['authorization'] = `Bearer ${authToken}`;

  const body = {
    strategyId: strategy.id,
    strategy,
    recs: [
      {
        rec_id: rec.id,
        type: rec.type,
        ...(rec.raw ? { raw: rec.raw } : {}),
        ...(rec.block ? { block: rec.block } : {}),
        ...(rec.signal ? { signal: rec.signal } : {}),
        ...(rec.parameter ? { parameter: rec.parameter } : {}),
        ...(rec.suggestedValue ? { suggestedValue: rec.suggestedValue } : {}),
      },
    ],
    optInDestructiveIds: null,
  };

  return {
    url: '/api/ai/auto-apply',
    init: {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    },
  };
}

export interface ParsedApplyResponse {
  ok: boolean;
  status: number;
  strategy?: Strategy;
  error?: string;
  detail?: string;
}

export function parseApplyResponse(
  res: Response,
  data: { ok?: boolean; strategy?: Strategy; error?: string; detail?: string } | null,
): ParsedApplyResponse {
  const okHttp = res.ok;
  const okBody = Boolean(data?.ok);
  if (!okHttp || !okBody) {
    return {
      ok: false,
      status: res.status,
      error: data?.error ?? `Auto-apply returned HTTP ${res.status}.`,
      detail: data?.detail,
    };
  }
  return {
    ok: true,
    status: res.status,
    strategy: data?.strategy,
  };
}

export async function executeApply(
  input: ApplyOrchestratorInput,
  deps: ApplyOrchestratorDeps,
): Promise<ExecuteApplyResult> {
  const { rec, strategy, appliedRecIds, preApplySnapshots } = input;
  const transitions: ApplyOrchestratorTransition[] = [];

  const rollback = rollbackTransitions(rec, appliedRecIds, preApplySnapshots);
  if (rollback) {
    transitions.push(rollback);
    deps.onHistoryStatusChange?.(rec.id, 'dismissed');
    return { transitions, ok: true };
  }

  // Apply path — snapshot first so a later rollback (local) is always
  // reversible even if the orchestrator fails or returns a malformed body.
  transitions.push({ kind: 'snapshot', entry: [rec.id, strategy] });
  transitions.push({ kind: 'markApplying', recId: rec.id });
  transitions.push({ kind: 'clearError', recId: rec.id });

  const token = deps.getAuthToken?.();
  const { url, init } = buildApplyRequest(rec, strategy, token);

  try {
    const res = await deps.fetchFn(url, init);
    let data: { ok?: boolean; strategy?: Strategy; error?: string; detail?: string } | null = null;
    try {
      data = (await res.json()) as typeof data;
    } catch {
      data = null;
    }
    const parsed = parseApplyResponse(res, data);
    if (!parsed.ok) {
      transitions.push({ kind: 'dropSnapshot', recId: rec.id });
      transitions.push({
        kind: 'setError',
        recId: rec.id,
        message: parsed.error ?? `Auto-apply returned HTTP ${parsed.status}.`,
      });
      return { transitions, ok: false };
    }
    transitions.push({ kind: 'markApplied', recId: rec.id });
    if (parsed.strategy) deps.onStrategyApplied?.(parsed.strategy);
    deps.onHistoryStatusChange?.(rec.id, 'applied');
    return { transitions, ok: true };
  } catch (err) {
    transitions.push({ kind: 'dropSnapshot', recId: rec.id });
    transitions.push({
      kind: 'setError',
      recId: rec.id,
      message:
        err instanceof Error
          ? err.message
          : 'The auto-apply request failed.',
    });
    return { transitions, ok: false };
  }
}