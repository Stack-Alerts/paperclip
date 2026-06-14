/**
 * Provider connectivity test logic for the AI recommendation settings.
 *
 * Kept free of Node-only APIs so it can be unit-tested under jsdom: the HTTP
 * providers use an injected `fetch`, and the Claude Code CLI path is delegated
 * to an injected `runClaudeCli` (its real implementation lives in route.ts,
 * which runs on the Node.js runtime).
 */

export type TestProvider =
  | 'claude-code'
  | 'anthropic'
  | 'openai'
  | 'openrouter'
  | 'deepseek'
  | 'ollama';

export interface ConnectionTestConfig {
  provider: TestProvider;
  model: string;
  apiKey?: string;
  ollamaBaseUrl?: string;
}

export interface ConnectionTestResult {
  ok: boolean;
  /** Short, user-facing summary. */
  message: string;
  /** Optional extra context (error body, model echo). */
  detail?: string;
}

export interface TesterDeps {
  fetch: typeof fetch;
  /** Runs a minimal Claude Code CLI generation to prove provider+model work. */
  runClaudeCli: (model: string) => Promise<ConnectionTestResult>;
  /** Per-request timeout for HTTP providers. */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 20_000;

const OPENAI_COMPATIBLE_ENDPOINTS: Partial<Record<TestProvider, string>> = {
  openai: 'https://api.openai.com/v1/chat/completions',
  openrouter: 'https://openrouter.ai/api/v1/chat/completions',
  deepseek: 'https://api.deepseek.com/chat/completions',
};

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

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError';
}

async function testAnthropic(
  cfg: ConnectionTestConfig,
  deps: Required<TesterDeps>,
): Promise<ConnectionTestResult> {
  const res = await withTimeout(deps.timeoutMs, (signal) =>
    deps.fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': cfg.apiKey ?? '',
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: cfg.model,
        max_tokens: 1,
        messages: [{ role: 'user', content: 'ping' }],
      }),
    }),
  );
  if (res.ok) {
    return { ok: true, message: `Connected to Anthropic with ${cfg.model}.` };
  }
  return {
    ok: false,
    message: `Anthropic rejected the request (HTTP ${res.status}).`,
    detail: await describeError(res),
  };
}

async function testOpenAiCompatible(
  cfg: ConnectionTestConfig,
  deps: Required<TesterDeps>,
): Promise<ConnectionTestResult> {
  const endpoint = OPENAI_COMPATIBLE_ENDPOINTS[cfg.provider];
  if (!endpoint) {
    return { ok: false, message: `Unsupported provider: ${cfg.provider}.` };
  }
  const res = await withTimeout(deps.timeoutMs, (signal) =>
    deps.fetch(endpoint, {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${cfg.apiKey ?? ''}`,
      },
      body: JSON.stringify({
        model: cfg.model,
        max_tokens: 1,
        messages: [{ role: 'user', content: 'ping' }],
      }),
    }),
  );
  if (res.ok) {
    return { ok: true, message: `Connected to ${cfg.provider} with ${cfg.model}.` };
  }
  return {
    ok: false,
    message: `${cfg.provider} rejected the request (HTTP ${res.status}).`,
    detail: await describeError(res),
  };
}

async function testOllama(
  cfg: ConnectionTestConfig,
  deps: Required<TesterDeps>,
): Promise<ConnectionTestResult> {
  const raw = (cfg.ollamaBaseUrl || 'http://localhost:11434').replace(/\/+$/, '');
  // The base URL is operator-supplied; constrain it to an http(s) origin so the
  // server can't be steered into non-HTTP schemes (file:, etc.). Reaching
  // localhost/LAN is intentional here — Ollama runs locally — so private-range
  // hosts are allowed, but redirects are not followed (redirect: 'manual').
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return { ok: false, message: `"${raw}" is not a valid Ollama base URL.` };
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, message: 'The Ollama base URL must use http or https.' };
  }
  const base = raw;
  let res: Response;
  try {
    res = await withTimeout(deps.timeoutMs, (signal) =>
      deps.fetch(`${base}/api/tags`, { method: 'GET', redirect: 'manual', signal }),
    );
  } catch (err) {
    if (isAbortError(err)) {
      return { ok: false, message: `Ollama did not respond within the timeout at ${base}.` };
    }
    return {
      ok: false,
      message: `Could not reach the Ollama server at ${base}.`,
      detail: err instanceof Error ? err.message : String(err),
    };
  }
  if (!res.ok) {
    return {
      ok: false,
      message: `Ollama server error (HTTP ${res.status}).`,
      detail: await describeError(res),
    };
  }
  const data = (await res.json()) as { models?: Array<{ name?: string }> };
  const names = (data.models ?? []).map((m) => m.name ?? '');
  const present = names.some(
    (name) => name === cfg.model || name.split(':')[0] === cfg.model,
  );
  if (present) {
    return { ok: true, message: `Connected to Ollama; model ${cfg.model} is available.` };
  }
  return {
    ok: false,
    message: `Ollama is reachable but model "${cfg.model}" is not installed.`,
    detail: names.length
      ? `Installed models: ${names.join(', ')}`
      : 'No models are installed. Run `ollama pull <model>`.',
  };
}

/**
 * Run a minimal live request against the configured provider/model and report
 * whether it succeeded. Throws are converted into a failed result so the route
 * always returns a structured payload.
 */
export async function testAiConnection(
  cfg: ConnectionTestConfig,
  deps: TesterDeps,
): Promise<ConnectionTestResult> {
  const resolved: Required<TesterDeps> = {
    fetch: deps.fetch,
    runClaudeCli: deps.runClaudeCli,
    timeoutMs: deps.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  };

  if (!cfg.model || !cfg.model.trim()) {
    return { ok: false, message: 'Select a model before testing the connection.' };
  }

  const needsKey =
    cfg.provider === 'anthropic' ||
    cfg.provider === 'openai' ||
    cfg.provider === 'openrouter' ||
    cfg.provider === 'deepseek';
  if (needsKey && !(cfg.apiKey && cfg.apiKey.trim())) {
    return { ok: false, message: 'Enter and save an API key for this provider first.' };
  }

  try {
    switch (cfg.provider) {
      case 'claude-code':
        return await resolved.runClaudeCli(cfg.model);
      case 'anthropic':
        return await testAnthropic(cfg, resolved);
      case 'openai':
      case 'openrouter':
      case 'deepseek':
        return await testOpenAiCompatible(cfg, resolved);
      case 'ollama':
        return await testOllama(cfg, resolved);
      default:
        return { ok: false, message: `Unknown provider: ${cfg.provider}.` };
    }
  } catch (err) {
    if (isAbortError(err)) {
      return { ok: false, message: 'The provider did not respond within the timeout.' };
    }
    return {
      ok: false,
      message: 'The connection test failed before reaching the provider.',
      detail: err instanceof Error ? err.message : String(err),
    };
  }
}
