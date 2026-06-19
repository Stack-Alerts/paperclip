/**
 * Webui-side apply orchestrator for AI recommendations (BTCAAAAA-36465).
 *
 * Replaces the FastAPI proxy (which 404ed because the backend endpoint never
 * existed) with in-process logic: we receive the current strategy from the
 * panel, parse the structured fields from the rec's raw text, mutate a deep
 * copy, and return it so the panel can update its local state via
 * onStrategyUpdated().
 *
 * Supported types (automatable without backend):
 *   ADJUST_PARAM  — update a named parameter on a block or signal
 *   ADJUST_RISK   — update a risk parameter in a risk_management block or settings
 *
 * Structural types (ADD_SIGNAL, REMOVE_SIGNAL, ADD_BLOCK, REMOVE_BLOCK) return
 * ok:true with a manualInstruction so the panel can show the user what to do
 * in the Strategy Builder rather than silently failing.
 */

export interface AutoApplyRec {
  rec_id: string;
  type: string;
  raw?: string;
  block?: string;
  signal?: string;
  parameter?: string;
  suggestedValue?: string;
  [key: string]: unknown;
}

export interface AutoApplyRequest {
  strategyId: string;
  recs: AutoApplyRec[];
  optInDestructiveIds: string[] | null;
  /** Current strategy state sent from the panel so we can apply locally. */
  strategy?: StrategyLike | null;
}

// Minimal strategy shape — mirrors the panel's Strategy type.
export interface StrategyLike {
  id: string;
  name: string;
  strategyType?: string;
  blocks?: BlockLike[];
  settings?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BlockLike {
  id: string;
  type: string;
  index: number;
  data: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AutoApplyDryRunEntry {
  rec_id: string;
  classification: string;
  [key: string]: unknown;
}

export interface AutoApplyResult {
  ok: boolean;
  strategy?: StrategyLike;
  dryRun?: { entries: AutoApplyDryRunEntry[]; applicable_count: number };
  apply?: { applied: Array<{ rec_id: string }>; applied_count: number };
  /** Human-readable instruction for structural recs that need manual steps. */
  manualInstruction?: string;
  error?: string;
  detail?: string;
}

// Kept for compatibility with route.ts — no longer used for remote calls.
export interface AutoApplyDeps {
  fetch?: typeof fetch;
  baseUrl?: string;
  authHeader?: string | null;
}

// ── Field extraction ──────────────────────────────────────────────────────────

function extractField(raw: string, label: string): string | undefined {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`(?:^|\\n)\\s*${escaped}\\s*[:\\-]\\s*([^\\n]+)`, 'i');
  const m = raw.match(re);
  if (!m) return undefined;
  const val = m[1].trim();
  return val === '' || /^n\/a$/i.test(val) ? undefined : val;
}

function parseNumeric(v: string): number | undefined {
  const n = parseFloat(v.replace(/[%,]/g, ''));
  return isNaN(n) ? undefined : n;
}

// ── Deep clone ────────────────────────────────────────────────────────────────

function deepClone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

// ── Block lookup ──────────────────────────────────────────────────────────────

function findBlock(blocks: BlockLike[], blockName: string): BlockLike | undefined {
  return blocks.find((b) => {
    const name = (b.data?.name as string | undefined) ?? '';
    return name.toLowerCase() === blockName.toLowerCase();
  });
}

function findSignal(
  block: BlockLike,
  signalName: string,
): Record<string, unknown> | undefined {
  const signals = block.data?.signals as Array<Record<string, unknown>> | undefined;
  if (!signals) return undefined;
  return signals.find(
    (s) =>
      typeof s.name === 'string' &&
      s.name.toLowerCase() === signalName.toLowerCase(),
  );
}

// ── Apply one rec ─────────────────────────────────────────────────────────────

function applyRec(strategy: StrategyLike, rec: AutoApplyRec): AutoApplyResult {
  const raw = rec.raw ?? '';

  // Prefer pre-parsed fields forwarded from ParsedRec; fall back to inline extraction.
  const recType = (rec.type ?? extractField(raw, 'Type') ?? '').trim().toUpperCase();
  const blockName = rec.block ?? extractField(raw, 'Block') ?? '';
  const signalName = rec.signal ?? extractField(raw, 'Signal');
  const parameter = rec.parameter ?? extractField(raw, 'Parameter');
  const suggestedRaw = rec.suggestedValue ?? extractField(raw, 'Suggested Value');

  const clone = deepClone(strategy);
  const blocks = clone.blocks ?? [];

  // ── Structural changes: guide the user to the Strategy Builder ────────────
  if (['ADD_SIGNAL', 'REMOVE_SIGNAL', 'ADD_BLOCK', 'REMOVE_BLOCK'].includes(recType)) {
    const action =
      recType === 'ADD_SIGNAL'
        ? `Add a signal named "${signalName ?? '?'}" to the "${blockName}" block`
        : recType === 'REMOVE_SIGNAL'
          ? `Remove the signal "${signalName ?? '?'}" from the "${blockName}" block`
          : recType === 'ADD_BLOCK'
            ? `Add a new "${blockName}" block via the Strategy Builder`
            : `Remove the "${blockName}" block in the Strategy Builder`;

    return {
      ok: true,
      strategy: clone,
      manualInstruction: `${action}. Open the Strategy Builder to apply this change manually.`,
      apply: { applied: [{ rec_id: rec.rec_id }], applied_count: 1 },
    };
  }

  // ── ADJUST_PARAM / ADJUST_RISK ─────────────────────────────────────────────
  if (!parameter) {
    return {
      ok: false,
      error: `Cannot apply rec "${rec.rec_id}": no Parameter field in the recommendation text.`,
    };
  }
  if (!suggestedRaw) {
    return {
      ok: false,
      error: `Cannot apply rec "${rec.rec_id}": no Suggested Value in the recommendation text.`,
    };
  }

  const numericVal = parseNumeric(suggestedRaw);
  const newValue: unknown = numericVal !== undefined ? numericVal : suggestedRaw;

  // Settings-level change (Block: "settings").
  if (/^settings$/i.test(blockName)) {
    if (clone.settings) {
      (clone.settings as Record<string, unknown>)[parameter] = newValue;
    }
    return {
      ok: true,
      strategy: clone,
      apply: { applied: [{ rec_id: rec.rec_id }], applied_count: 1 },
    };
  }

  const block = findBlock(blocks, blockName);
  if (!block) {
    return {
      ok: false,
      error: `Block "${blockName}" not found in strategy. Verify the block name matches exactly.`,
    };
  }

  // Dot-notation helper for nested paths e.g. "recheck_config.bar_delay".
  function setNested(obj: Record<string, unknown>, path: string, value: unknown): void {
    const parts = path.split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof cur[parts[i]] !== 'object' || cur[parts[i]] === null) {
        cur[parts[i]] = {};
      }
      cur = cur[parts[i]] as Record<string, unknown>;
    }
    cur[parts[parts.length - 1]] = value;
  }

  if (signalName) {
    const signal = findSignal(block, signalName);
    if (!signal) {
      return {
        ok: false,
        error: `Signal "${signalName}" not found in block "${blockName}".`,
      };
    }
    setNested(signal, parameter, newValue);
  } else {
    setNested(block.data, parameter, newValue);
  }

  return {
    ok: true,
    strategy: clone,
    apply: { applied: [{ rec_id: rec.rec_id }], applied_count: 1 },
  };
}

// ── Public entry point ────────────────────────────────────────────────────────

export async function runAutoApply(
  req: AutoApplyRequest,
  _deps?: AutoApplyDeps,
): Promise<AutoApplyResult> {
  if (!req.strategy) {
    return {
      ok: false,
      error:
        'No strategy provided. The panel must include the current strategy when calling auto-apply.',
    };
  }

  if (!req.recs || req.recs.length === 0) {
    return { ok: true, strategy: req.strategy, apply: { applied: [], applied_count: 0 } };
  }

  let current = deepClone(req.strategy);
  const applied: Array<{ rec_id: string }> = [];
  const manualInstructions: string[] = [];

  for (const rec of req.recs) {
    const result = applyRec(current, rec);
    if (!result.ok) {
      return result;
    }
    if (result.strategy) {
      current = result.strategy;
    }
    if (result.manualInstruction) {
      manualInstructions.push(result.manualInstruction);
    }
    applied.push({ rec_id: rec.rec_id });
  }

  return {
    ok: true,
    strategy: current,
    apply: { applied, applied_count: applied.length },
    ...(manualInstructions.length > 0
      ? { manualInstruction: manualInstructions.join('\n\n') }
      : {}),
  };
}
