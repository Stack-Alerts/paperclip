/**
 * Provider call logic for the "Approve & Send to AI" analyze endpoint.
 *
 * Kept free of Node-only APIs so it can be unit-tested under jsdom: HTTP
 * providers use an injected `fetch`, and the Claude Code CLI path is
 * delegated to an injected `runClaudeCli` (its real implementation lives in
 * route.ts, which runs on the Node.js runtime).
 */

export type AnalyzeProvider =
  | 'claude-code'
  | 'anthropic'
  | 'minimax'
  | 'openai'
  | 'openrouter'
  | 'deepseek'
  | 'ollama';

export interface AnalyzeRequest {
  provider: AnalyzeProvider;
  model: string;
  apiKey?: string;
  ollamaBaseUrl?: string;
  /** The user's instruction, e.g. "Analyze this backtest and recommend changes." */
  prompt: string;
  /** The backtest JSON payload (strategy config, trades, metrics). */
  payload: unknown;
}

export interface AnalyzeResult {
  ok: boolean;
  /** The model's response text on success. */
  text?: string;
  /** Short error description on failure. */
  error?: string;
  /** Optional extra context (provider error body, etc.). */
  detail?: string;
}

export interface AnalyzeDeps {
  fetch: typeof fetch;
  /**
   * Runs the Claude Code CLI with the given model, prompt, and JSON payload
   * (the implementation lives in route.ts so the Node-only child_process
   * import stays out of the pure helper).
   */
  runClaudeCli: (
    model: string,
    prompt: string,
    payload: unknown,
  ) => Promise<AnalyzeResult>;
  /** Per-request timeout for HTTP providers. */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 120_000;

const OPENAI_COMPATIBLE_ENDPOINTS: Partial<Record<AnalyzeProvider, string>> = {
  openai: 'https://api.openai.com/v1/chat/completions',
  openrouter: 'https://openrouter.ai/api/v1/chat/completions',
  deepseek: 'https://api.deepseek.com/chat/completions',
};

// Anthropic-compatible /v1/messages endpoints. Both anthropic and minimax share
// the same x-api-key + anthropic-version header shape.
const ANTHROPIC_COMPATIBLE_ENDPOINTS: Partial<Record<AnalyzeProvider, string>> = {
  anthropic: 'https://api.anthropic.com/v1/messages',
  minimax: 'https://api.minimax.io/anthropic/v1/messages',
};

const OLLAMA_DEFAULT_URL = 'http://localhost:11434';

/** Instructs the model to return a structured diagnosis + recommendations block. */
export const SYSTEM_PROMPT = `You are an expert quantitative analyst specialising in BTC perpetual futures algorithmic trading strategies.

Platform context:
- This is a BTC/USDT perpetual futures strategy builder running on historical OHLCV data.
- Strategies are composed of building blocks drawn from these categories:
  PATTERNS, TREND, OSCILLATORS, MOVING_AVERAGES, PRICE_ACTION, PRICE_LEVELS,
  MARKET_STRUCTURE, SUPPLY_DEMAND, VOLATILITY, RISK_MANAGEMENT, FIBONACCI,
  ELLIOTT_WAVE, SESSIONS, SMC_ICT, WYCKOFF, INSTITUTIONAL, SIGNALS.
- Strategy config keys you may reference (use exact names — do not invent keys):
  timeframe, initialCapital, commissionPercentage, slippagePercentage,
  maxConcurrentPositions, riskPerTradePct, minRiskRewardRatio, maxBarsHeld,
  maxLeverage, confluenceThreshold, tpslMode, slAdjustmentMode, adaptiveSLPreset,
  adaptiveSL.enabled, adaptiveSL.volatilityMultiplier, adaptiveSL.minSlPct,
  adaptiveSL.maxSlPct, adaptiveSL.emergencySlPct, adaptiveSL.delayBars,
  adaptiveSL.volatilityLookback, adaptiveSL.useStructureSl.

You will be given a JSON payload containing a backtest result: strategy configuration, all executed trades, and aggregate performance metrics.

When present, a performance_attribution object gives you pre-computed diagnostics — USE THESE to make your diagnosis and recommendations specific to THIS strategy rather than generic boilerplate:
- metric_divergence: each metric's portfolio-reported value vs the value recomputed per entry. When divergent is true, the aggregate summary disagrees with the per-trade reality (e.g. a few outlier trades inflating profit factor) — call this out and target the recommendation at the discrepancy.
- entry_signal_usage: which entry signals (and their owning block, when known) gated the most trades and the net PnL attributed to each. Prefer adjusting or removing the highest-volume LOSING signal/block, or leaning into the highest-PnL one, over blanket settings changes.
- exit_type_usage: which exit reason closed the most trades and its net PnL. If one exit type dominates losses (e.g. Stop Loss Hit), tailor the SL/TP recommendation to it.
Ground your DIAGNOSIS in the specific signal/block/exit names and numbers from this object. Do not recommend a change that the attribution data does not support.

CRITICAL INSTRUCTION: Your output is machine-parsed. The application reads Block, Parameter, and Suggested Value to auto-apply your recommendations to the live strategy. If you omit any of these fields on an ADJUST_PARAM recommendation, the user will see an error "Cannot apply rec: no Parameter field" and will be unable to apply your recommendation. You MUST include all five fields (Type, Block, Parameter, Suggested Value, Rationale) on every ADJUST_PARAM line.

Respond in EXACTLY this format — copy the structure below verbatim, only substituting the angle-bracket placeholders:

DIAGNOSIS:
<2-4 sentence diagnosis citing real numbers from the payload. What the strategy does, how it actually performed, and the most critical issue or strength.>

RECOMMENDATIONS:
<1-3 numbered recommendations. For each one that adjusts a parameter value, follow Template A exactly. For adding a new block type, follow Template B.>

=== TEMPLATE A (use for every parameter/value change) ===
1. <One-sentence action title>
   Type: ADJUST_PARAM
   Block: <exact value of blocks[].data.name from the payload, OR the word settings>
   Parameter: <exact key from that block's data object or from strategy settings — do NOT invent a name>
   Suggested Value: <new value only, e.g. 1.5 or true — no units, no ranges>
   Rationale: <one sentence explaining why>

=== TEMPLATE B (use only to add an entirely new building block) ===
2. <One-sentence action title>
   Type: ADD_BLOCK
   Block: <block category name, e.g. VOLATILITY>
   Rationale: <one sentence explaining why>

Hard rules — breaking any of these makes your output unparseable:
- Type, Block, Parameter, Suggested Value, Rationale: no asterisks, no markdown, no colons in values.
- Block in Template A must match a name from the strategy_config payload exactly, or be the literal word settings.
- Parameter must be a key that actually exists in that block.data or in strategy settings — never invent a key.
- Suggested Value is a single scalar: a number or string, nothing else.
- No prose, bullet lists, headings, or text outside the DIAGNOSIS and RECOMMENDATIONS sections.
- If the payload contains no trades, say so in DIAGNOSIS and give one ADD_BLOCK recommendation.
- Keep total response under 600 words.

=== WORKED EXAMPLE ===
This is a complete, valid response for a typical backtest. Match this structure and field order exactly. Do not add extra sections, prose, or commentary.

DIAGNOSIS:
The RSI Reversion strategy executed 47 trades over the backtest with a 51% win rate and a -1.8% net return, primarily because exits were triggered too early by the fixed 5-bar hold and stop losses were placed at a uniform 1.5% without adapting to recent volatility.

RECOMMENDATIONS:
1. Widen stop loss to track volatility
   Type: ADJUST_PARAM
   Block: settings
   Parameter: adaptiveSL.enabled
   Suggested Value: true
   Rationale: Switching from a fixed stop to an adaptive volatility-based stop should reduce whipsaw losses in ranging markets.
2. Reduce fixed hold to allow winners to breathe
   Type: ADJUST_PARAM
   Block: settings
   Parameter: maxBarsHeld
   Suggested Value: 8
   Rationale: Extending the hold by 3 bars gives winning setups room to reach their mean-reversion target before time exit.`;

/** Format the user message by appending the payload as a JSON code block. */
function buildUserMessage(prompt: string, payload: unknown): string {
  return `${prompt.trim() || 'Analyze this backtest and return a diagnosis and recommendations.'}\n\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\``;
}

async function withTimeout<T>(
  timeoutMs: number,
  run: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await run(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError';
}

/** Pull a human-readable error message out of a provider error response. */
async function describeError(res: Response): Promise<string> {
  let body = '';
  try {
    body = await res.text();
  } catch {
    /* ignore */
  }
  try {
    const json = JSON.parse(body) as { error?: { message?: string } | string };
    const err = json.error;
    if (typeof err === 'string') return err;
    if (err?.message) return err.message;
  } catch {
    /* not JSON */
  }
  const trimmed = body.trim();
  return trimmed ? trimmed.slice(0, 300) : `HTTP ${res.status} ${res.statusText}`;
}

async function callAnthropic(
  req: AnalyzeRequest,
  deps: Required<AnalyzeDeps>,
): Promise<AnalyzeResult> {
  const endpoint = ANTHROPIC_COMPATIBLE_ENDPOINTS[req.provider];
  if (!endpoint) {
    return { ok: false, error: `Unsupported Anthropic-compatible provider: ${req.provider}.` };
  }
  const providerLabel = req.provider === 'minimax' ? 'MiniMax' : 'Anthropic';
  const res = await withTimeout(deps.timeoutMs, (signal) =>
    deps.fetch(endpoint, {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': req.apiKey ?? '',
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: req.model,
        max_tokens: 2048,
        system: SYSTEM_PROMPT,
        messages: [{ role: 'user', content: buildUserMessage(req.prompt, req.payload) }],
      }),
    }),
  );
  if (!res.ok) {
    return {
      ok: false,
      error: `${providerLabel} rejected the request (HTTP ${res.status}).`,
      detail: await describeError(res),
    };
  }
  const data = (await res.json()) as {
    content?: Array<{ type: string; text?: string }>;
  };
  const text = (data.content ?? [])
    .filter((block) => block.type === 'text')
    .map((block) => block.text ?? '')
    .join('\n')
    .trim();
  if (!text) {
    return { ok: false, error: `${providerLabel} returned an empty response.` };
  }
  return { ok: true, text };
}

async function callOpenAiCompatible(
  req: AnalyzeRequest,
  deps: Required<AnalyzeDeps>,
): Promise<AnalyzeResult> {
  const endpoint = OPENAI_COMPATIBLE_ENDPOINTS[req.provider];
  if (!endpoint) {
    return { ok: false, error: `Unsupported provider: ${req.provider}.` };
  }
  const res = await withTimeout(deps.timeoutMs, (signal) =>
    deps.fetch(endpoint, {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${req.apiKey ?? ''}`,
      },
      body: JSON.stringify({
        model: req.model,
        max_tokens: 2048,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: buildUserMessage(req.prompt, req.payload) },
        ],
      }),
    }),
  );
  if (!res.ok) {
    return {
      ok: false,
      error: `${req.provider} rejected the request (HTTP ${res.status}).`,
      detail: await describeError(res),
    };
  }
  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const text = data.choices?.[0]?.message?.content?.trim() ?? '';
  if (!text) {
    return { ok: false, error: `${req.provider} returned an empty response.` };
  }
  return { ok: true, text };
}

async function callOllama(
  req: AnalyzeRequest,
  deps: Required<AnalyzeDeps>,
): Promise<AnalyzeResult> {
  const raw = (req.ollamaBaseUrl || OLLAMA_DEFAULT_URL).replace(/\/+$/, '');
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return { ok: false, error: `"${raw}" is not a valid Ollama base URL.` };
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, error: 'The Ollama base URL must use http or https.' };
  }
  let res: Response;
  try {
    res = await withTimeout(deps.timeoutMs, (signal) =>
      deps.fetch(`${raw}/api/chat`, {
        method: 'POST',
        signal,
        redirect: 'manual',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: req.model,
          stream: false,
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            { role: 'user', content: buildUserMessage(req.prompt, req.payload) },
          ],
        }),
      }),
    );
  } catch (err) {
    if (isAbortError(err)) {
      return { ok: false, error: `Ollama did not respond within the timeout at ${raw}.` };
    }
    return {
      ok: false,
      error: `Could not reach the Ollama server at ${raw}.`,
      detail: err instanceof Error ? err.message : String(err),
    };
  }
  if (!res.ok) {
    return {
      ok: false,
      error: `Ollama server error (HTTP ${res.status}).`,
      detail: await describeError(res),
    };
  }
  const data = (await res.json()) as {
    message?: { content?: string };
  };
  const text = data.message?.content?.trim() ?? '';
  if (!text) {
    return { ok: false, error: 'Ollama returned an empty response.' };
  }
  return { ok: true, text };
}

/**
 * Run the analyze request against the configured provider. Throws are
 * converted into a failed result so the route always returns a structured
 * payload.
 */
export async function analyze(
  req: AnalyzeRequest,
  deps: AnalyzeDeps,
): Promise<AnalyzeResult> {
  const resolved: Required<AnalyzeDeps> = {
    fetch: deps.fetch,
    runClaudeCli: deps.runClaudeCli,
    timeoutMs: deps.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  };

  if (!req.model || !req.model.trim()) {
    return { ok: false, error: 'Select a model before sending the request.' };
  }

  const needsKey =
    req.provider === 'anthropic' ||
    req.provider === 'minimax' ||
    req.provider === 'openai' ||
    req.provider === 'openrouter' ||
    req.provider === 'deepseek';
  if (needsKey && !(req.apiKey && req.apiKey.trim())) {
    return { ok: false, error: 'Enter and save an API key for this provider first.' };
  }

  try {
    switch (req.provider) {
      case 'claude-code':
        return await resolved.runClaudeCli(req.model, req.prompt, req.payload);
      case 'anthropic':
      case 'minimax':
        return await callAnthropic(req, resolved);
      case 'openai':
      case 'openrouter':
      case 'deepseek':
        return await callOpenAiCompatible(req, resolved);
      case 'ollama':
        return await callOllama(req, resolved);
      default:
        return { ok: false, error: `Unknown provider: ${req.provider}.` };
    }
  } catch (err) {
    if (isAbortError(err)) {
      return { ok: false, error: 'The provider did not respond within the timeout.' };
    }
    return {
      ok: false,
      error: 'The analyze request failed before reaching the provider.',
      detail: err instanceof Error ? err.message : String(err),
    };
  }
}

/** Split the DIAGNOSIS / RECOMMENDATIONS sections from the model output.
 *
 * Handles plain text as well as common AI formatting deviations:
 * - Markdown bold: **DIAGNOSIS:** / **RECOMMENDATIONS:**
 * - Markdown headings: ## DIAGNOSIS / ## RECOMMENDATIONS
 *   (and ## Actionable Recommendations, which DeepSeek emits by default)
 * - No headers: falls back to numbered-list split
 */
export function parseAnalysisResponse(text: string): {
  diagnosis: string;
  recommendations: string;
  raw: string;
} {
  const normalized = text
    .replace(/\*{1,2}\s*(DIAGNOSIS)\s*\*{1,2}/gi, '$1:')
    .replace(/\*{1,2}\s*(?:Actionable\s+)?RECOMMENDATIONS\s*\*{1,2}/gi, '$1:')
    .replace(/^#{1,6}\s+(DIAGNOSIS)\s*[:\-]?\s*$/gim, 'DIAGNOSIS:')
    .replace(
      /^#{1,6}\s+(?:Actionable\s+)?RECOMMENDATIONS\s*[:\-]?\s*$/gim,
      'RECOMMENDATIONS:',
    );

  const diagnosisMatch = normalized.match(
    /DIAGNOSIS\s*:\s*([\s\S]*?)(?=\n\s*RECOMMENDATIONS\s*:|$)/i,
  );
  const recommendationsMatch = normalized.match(
    /RECOMMENDATIONS\s*:\s*([\s\S]*?)$/i,
  );

  let diagnosis = diagnosisMatch?.[1]?.trim() ?? '';
  let recommendations = recommendationsMatch?.[1]?.trim() ?? '';

  if (!diagnosis && !recommendations) {
    const idx = text.search(/(?:^|\n)\s*1[.)]\s+/);
    if (idx > 0) {
      diagnosis = text.slice(0, idx).trim();
      recommendations = text.slice(idx).trim();
    } else {
      diagnosis = text.trim();
    }
  }

  if (diagnosis && !recommendations) {
    const idx = diagnosis.search(/\n\s*1[.)]\s+/);
    if (idx > 0) {
      recommendations = diagnosis.slice(idx).trim();
      diagnosis = diagnosis.slice(0, idx).trim();
    }
  }

  return { diagnosis, recommendations, raw: text };
}
