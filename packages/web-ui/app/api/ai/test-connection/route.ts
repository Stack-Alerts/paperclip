import { execFile } from 'node:child_process';
import {
  testAiConnection,
  type ConnectionTestConfig,
  type ConnectionTestResult,
  type TestProvider,
} from './tester';

// Spawns the local Claude Code CLI, so this route must run on Node.js.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const VALID_PROVIDERS: TestProvider[] = [
  'claude-code',
  'anthropic',
  'openai',
  'openrouter',
  'deepseek',
  'ollama',
];

const CLI_TIMEOUT_MS = 60_000;

/** Run a minimal Claude Code CLI generation to prove the provider+model work. */
function runClaudeCli(model: string): Promise<ConnectionTestResult> {
  return new Promise((resolve) => {
    execFile(
      'claude',
      ['--print', '--model', model, 'Reply with the single word: pong'],
      { timeout: CLI_TIMEOUT_MS, maxBuffer: 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          const errno = (error as NodeJS.ErrnoException).code;
          if (errno === 'ENOENT') {
            resolve({
              ok: false,
              message:
                'The Claude Code CLI is not installed or not on PATH for the server.',
              detail: 'Install Claude Code and ensure `claude` is runnable by the web server.',
            });
            return;
          }
          if ((error as { killed?: boolean }).killed) {
            resolve({
              ok: false,
              message: `Claude Code did not respond within ${CLI_TIMEOUT_MS / 1000}s.`,
            });
            return;
          }
          resolve({
            ok: false,
            message: `Claude Code returned an error for model ${model}.`,
            detail: (stderr || error.message).trim().slice(0, 300),
          });
          return;
        }
        const out = (stdout || '').trim();
        if (out) {
          resolve({
            ok: true,
            message: `Claude Code responded using ${model}.`,
            detail: out.slice(0, 120),
          });
          return;
        }
        resolve({
          ok: false,
          message: 'Claude Code ran but produced no output.',
          detail: (stderr || '').trim().slice(0, 300),
        });
      },
    );
  });
}

export async function POST(request: Request): Promise<Response> {
  let body: Partial<ConnectionTestConfig>;
  try {
    body = (await request.json()) as Partial<ConnectionTestConfig>;
  } catch {
    return Response.json(
      { ok: false, message: 'Invalid request body.' },
      { status: 400 },
    );
  }

  const provider = body.provider as TestProvider | undefined;
  if (!provider || !VALID_PROVIDERS.includes(provider)) {
    return Response.json(
      { ok: false, message: 'Unknown or missing provider.' },
      { status: 400 },
    );
  }

  const config: ConnectionTestConfig = {
    provider,
    model: typeof body.model === 'string' ? body.model : '',
    apiKey: typeof body.apiKey === 'string' ? body.apiKey : undefined,
    ollamaBaseUrl:
      typeof body.ollamaBaseUrl === 'string' ? body.ollamaBaseUrl : undefined,
  };

  const result = await testAiConnection(config, { fetch, runClaudeCli });
  return Response.json(result);
}
