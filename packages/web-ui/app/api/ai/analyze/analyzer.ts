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

const OLLAMA_DEFAULT_URL = 'http://localhost:11434';

/** Instructs the model to return a structured diagnosis + recommendations block. */
export const SYSTEM_PROMPT = `You are an expert quantitative trading strategy analyst.

You will be given a JSON payload containing a backtest result: strategy configuration, all executed trades, and aggregate performance metrics.

Respond in EXACTLY this format (do not deviate):

DIAGNOSIS:
<2-4 sentence diagnosis of what this strategy does, how it actually performed, and the most important issue or strength you observe.>

RECOMMENDATIONS:
<Numbered list of 2-5 concrete, actionable recommendations. Each item must be one of:
  (a) a specific parameter change with the new value (e.g. "Increase stop-loss from 2% to 3%"),
  (b) a specific building block to add/remove/replace (e.g. "Replace the SMA crossover block with an EMA pair"),
  (c) a specific risk-management adjustment (e.g. "Cap position size at 1.5% of equity instead of 5%").
Each recommendation must be implementable as a single change to the strategy.>

Rules:
- No prose outside the DIAGNOSIS and RECOMMENDATIONS sections.
- No invented metrics — only reference numbers that appear in the payload.
- If the payload contains no trades, say so in DIAGNOSIS and recommend the user verify the strategy triggers any signals on the chosen data.
- Keep total response under ~600 words.`;

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
  const res = await withTimeout(deps.timeoutMs, (signal) =>
    deps.fetch('https://api.anthropic.com/v1/messages', {
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
      error: `Anthropic rejected the request (HTTP ${res.status}).`,
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
    return { ok: false, error: 'Anthropic returned an empty response.' };
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

/** Strip the DIAGNOSIS:/RECOMMENDATIONS: sections from the model output. */
export function parseAnalysisResponse(text: string): {
  diagnosis: string;
  recommendations: string;
  raw: string;
} {
  const diagnosisMatch = text.match(
    /DIAGNOSIS\s*:\s*([\s\S]*?)(?=\n\s*RECOMMENDATIONS\s*:|$)/i,
  );
  const recommendationsMatch = text.match(
    /RECOMMENDATIONS\s*:\s*([\s\S]*?)$/i,
  );
  return {
    diagnosis: diagnosisMatch?.[1]?.trim() ?? '',
    recommendations: recommendationsMatch?.[1]?.trim() ?? '',
    raw: text,
  };
}
