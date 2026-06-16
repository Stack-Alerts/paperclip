import { execFile } from 'node:child_process';
import {
  analyze,
  type AnalyzeProvider,
  type AnalyzeRequest,
  type AnalyzeResult,
} from './analyzer';

// Spawns the local Claude Code CLI, so this route must run on Node.js.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const VALID_PROVIDERS: AnalyzeProvider[] = [
  'claude-code',
  'anthropic',
  'openai',
  'openrouter',
  'deepseek',
  'ollama',
];

const CLI_TIMEOUT_MS = 180_000;

/** Run a Claude Code CLI generation with the analysis prompt + payload. */
function runClaudeCli(
  model: string,
  prompt: string,
  payload: unknown,
): Promise<AnalyzeResult> {
  return new Promise((resolve) => {
    const fullPrompt =
      `${prompt.trim() || 'Analyze this backtest and return a diagnosis and recommendations.'}\n\n` +
      '```json\n' +
      `${JSON.stringify(payload, null, 2)}\n` +
      '```';
    execFile(
      'claude',
      ['--print', '--model', model, fullPrompt],
      { timeout: CLI_TIMEOUT_MS, maxBuffer: 8 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          const errno = (error as NodeJS.ErrnoException).code;
          if (errno === 'ENOENT') {
            resolve({
              ok: false,
              error:
                'The Claude Code CLI is not installed or not on PATH for the server.',
              detail: 'Install Claude Code and ensure `claude` is runnable by the web server.',
            });
            return;
          }
          if ((error as { killed?: boolean }).killed) {
            resolve({
              ok: false,
              error: `Claude Code did not respond within ${CLI_TIMEOUT_MS / 1000}s.`,
            });
            return;
          }
          resolve({
            ok: false,
            error: `Claude Code returned an error for model ${model}.`,
            detail: (stderr || error.message).trim().slice(0, 300),
          });
          return;
        }
        const out = (stdout || '').trim();
        if (out) {
          resolve({ ok: true, text: out });
          return;
        }
        resolve({
          ok: false,
          error: 'Claude Code ran but produced no output.',
          detail: (stderr || '').trim().slice(0, 300),
        });
      },
    );
  });
}

export async function POST(request: Request): Promise<Response> {
  let body: Partial<AnalyzeRequest>;
  try {
    body = (await request.json()) as Partial<AnalyzeRequest>;
  } catch {
    return Response.json(
      { ok: false, error: 'Invalid request body.' },
      { status: 400 },
    );
  }

  const provider = body.provider as AnalyzeProvider | undefined;
  if (!provider || !VALID_PROVIDERS.includes(provider)) {
    return Response.json(
      { ok: false, error: 'Unknown or missing provider.' },
      { status: 400 },
    );
  }

  const req: AnalyzeRequest = {
    provider,
    model: typeof body.model === 'string' ? body.model : '',
    apiKey: typeof body.apiKey === 'string' ? body.apiKey : undefined,
    ollamaBaseUrl:
      typeof body.ollamaBaseUrl === 'string' ? body.ollamaBaseUrl : undefined,
    prompt: typeof body.prompt === 'string' ? body.prompt : '',
    payload: body.payload,
  };

  const result = await analyze(req, { fetch, runClaudeCli });
  return Response.json(result);
}
