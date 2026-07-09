import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Session-end autosave wrapper around scripts/session_end_autosave.py.
 *
 * Invoked from the adapter `execute()` finally block so a Paperclip run
 * that exits (normally, via OOM kill, harness crash, or watchdog SIGTERM)
 * still gets a chance to push in-progress work on protected branches
 * (`fix/BTCAAAAA-*` / `feat/BTCAAAAA-*`). The script itself enforces the
 * branch allowlist and the force-with-lease push policy; this wrapper only
 * plumbs run-id, workspace cwd, and the issue identifier through, and
 * guarantees the call never throws — a snapshot failure must never block
 * run termination.
 *
 * See AGENTS.md §12 for the full contract.
 */

const HERE = path.dirname(fileURLToPath(import.meta.url));
// The script ships in the repo root, three levels above this file. Fall
// back to process.cwd()/scripts/... for callers that ship adapter-utils
// without the script alongside it.
const REPO_ROOT = path.resolve(HERE, "..", "..", "..");
const SCRIPT_PATH_CANDIDATES = [
  path.join(REPO_ROOT, "scripts", "session_end_autosave.py"),
  path.join(process.cwd(), "scripts", "session_end_autosave.py"),
];

const PYTHON_BIN_CANDIDATES = ["python3", "python"];
const AUTOSAVE_LOG_FILENAME = ".paperclip/autosave.log";

function resolveScriptPath(): string | null {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require("node:fs") as typeof import("node:fs");
  for (const candidate of SCRIPT_PATH_CANDIDATES) {
    try {
      fs.accessSync(candidate);
      return candidate;
    } catch {
      // continue
    }
  }
  return null;
}

function pickPythonBin(): string {
  return PYTHON_BIN_CANDIDATES[0];
}

function appendAutosaveLog(repoRoot: string, line: string): void {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const fs = require("node:fs") as typeof import("node:fs");
    const logPath = path.join(repoRoot, AUTOSAVE_LOG_FILENAME);
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    fs.appendFileSync(logPath, line, { encoding: "utf8" });
  } catch {
    // ignore — diagnostics never block the caller
  }
}

export interface RunSessionEndAutosaveOptions {
  /** Paperclip run id; embedded in the WIP commit subject. */
  runId: string;
  /** Absolute path to the agent's workspace (the directory the script should .git-walk from). */
  workspaceCwd: string;
  /** Optional Paperclip issue identifier, e.g. `BTCAAAAA-39074`. */
  issueId?: string | null;
  /**
   * Override the path to the script. Defaults to the script shipped at the
   * repo root; useful for tests that synthesize a temp checkout.
   */
  scriptPath?: string;
  /**
   * Override the Python interpreter. Defaults to `python3` then `python`.
   */
  pythonBin?: string;
  /**
   * Wall-clock budget for the entire subprocess (default 30s). Pushes can be
   * slow on a cold cache; this is plenty for a 1-commit force-with-lease.
   */
  timeoutMs?: number;
  /**
   * Optional sink the wrapper uses to surface the snapshot outcome to the
   * adapter's run log. The wrapper only ever passes strings to it; the sink
   * is responsible for handling its own errors.
   */
  onLog?: (stream: "stdout" | "stderr", chunk: string) => void | Promise<void>;
}

export interface RunSessionEndAutosaveResult {
  /** Whether the wrapper actually invoked the script. */
  invoked: boolean;
  /** Process exit code, or null if the wrapper could not start the process. */
  exitCode: number | null;
  /** True when the call was suppressed (no script, no runId, no cwd, or opt-out). */
  skipped: boolean;
  /** Human-readable reason, suitable for appending to the run log. */
  reason: string;
}

/**
 * Run the SessionEnd autosave hook. NEVER throws — all errors are caught
 * and recorded in `.paperclip/autosave.log` (when reachable) or stderr.
 */
export async function runSessionEndAutosave(
  options: RunSessionEndAutosaveOptions,
): Promise<RunSessionEndAutosaveResult> {
  const opts = options;
  const repoRoot = path.resolve(opts.workspaceCwd);
  const stamp = new Date().toISOString();

  // 1. Caller signals an intentional opt-out (rare; the script also
  //    honors PAPERCLIP_NO_AUTOSAVE=1 internally).
  if (process.env.PAPERCLIP_NO_AUTOSAVE === "1") {
    appendAutosaveLog(
      repoRoot,
      `[session-end-autosave] ${stamp} opt-out via PAPERCLIP_NO_AUTOSAVE=1; runId=${opts.runId}\n`,
    );
    return { invoked: false, exitCode: 3, skipped: true, reason: "PAPERCLIP_NO_AUTOSAVE=1" };
  }

  // 2. Need a runId and a workspace cwd to do anything useful.
  if (!opts.runId || !opts.workspaceCwd) {
    return {
      invoked: false,
      exitCode: null,
      skipped: true,
      reason: "missing runId or workspaceCwd",
    };
  }

  const scriptPath = opts.scriptPath ?? resolveScriptPath();
  if (!scriptPath) {
    appendAutosaveLog(
      repoRoot,
      `[session-end-autosave] ${stamp} session_end_autosave.py not on disk; runId=${opts.runId} cwd=${repoRoot}\n`,
    );
    return {
      invoked: false,
      exitCode: null,
      skipped: true,
      reason: "session_end_autosave.py not found",
    };
  }

  const pythonBin = opts.pythonBin ?? pickPythonBin();
  const args = [
    scriptPath,
    "--cwd",
    repoRoot,
    "--run-id",
    opts.runId,
  ];
  if (opts.issueId && opts.issueId.trim().length > 0) {
    args.push("--issue-id", opts.issueId.trim());
  }

  try {
    const exitCode: number | null = await new Promise((resolve) => {
      const child = spawn(pythonBin, args, {
        cwd: repoRoot,
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, PAPERCLIP_RUN_ID: opts.runId },
      });

      let stdoutBuf = "";
      let stderrBuf = "";
      let settled = false;
      const finish = (code: number | null) => {
        if (settled) return;
        settled = true;
        if (stdoutBuf.length > 0) {
          try {
            const sink = opts.onLog;
            if (sink) {
              const r = sink("stdout", stdoutBuf);
              if (r && typeof (r as Promise<unknown>).then === "function") {
                (r as Promise<unknown>).catch(() => undefined);
              }
            }
          } catch {
            // ignore
          }
        }
        if (stderrBuf.length > 0) {
          try {
            const sink = opts.onLog;
            if (sink) {
              const r = sink("stderr", stderrBuf);
              if (r && typeof (r as Promise<unknown>).then === "function") {
                (r as Promise<unknown>).catch(() => undefined);
              }
            }
          } catch {
            // ignore
          }
        }
        resolve(code);
      };

      child.stdout.on("data", (chunk: Buffer | string) => {
        stdoutBuf += chunk.toString();
      });
      child.stderr.on("data", (chunk: Buffer | string) => {
        stderrBuf += chunk.toString();
      });
      child.on("error", (err) => {
        appendAutosaveLog(
          repoRoot,
          `[session-end-autosave] ${stamp} spawn error runId=${opts.runId} err=${err.message}\n`,
        );
        finish(null);
      });
      child.on("close", (code) => finish(code));

      const timeoutMs = opts.timeoutMs ?? 30_000;
      const timer = setTimeout(() => {
        try {
          child.kill("SIGTERM");
        } catch {
          // ignore
        }
        appendAutosaveLog(
          repoRoot,
          `[session-end-autosave] ${stamp} timeout after ${timeoutMs}ms; killed SIGTERM; runId=${opts.runId}\n`,
        );
      }, timeoutMs);
      child.on("close", () => clearTimeout(timer));
    });

    appendAutosaveLog(
      repoRoot,
      `[session-end-autosave] ${stamp} runId=${opts.runId} exitCode=${exitCode}\n`,
    );
    return { invoked: true, exitCode, skipped: false, reason: "ok" };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    appendAutosaveLog(
      repoRoot,
      `[session-end-autosave] ${stamp} unexpected error runId=${opts.runId} err=${message}\n`,
    );
    return { invoked: false, exitCode: null, skipped: false, reason: `wrapper error: ${message}` };
  }
}

/**
 * Minimal context shape consumed by {@link runAdapterSessionEndAutosave}.
 *
 * We avoid a hard dependency on `AdapterExecutionContext` here so this helper
 * can be imported by every adapter without dragging the full execution-context
 * type-graph into adapter-utils. Adapters `execute()` callers must already
 * have an `AdapterExecutionContext` in scope (it's the function argument), so
 * it's structurally compatible.
 */
export interface AdapterSessionEndAutosaveContextLike {
  runId: string;
  context?: Record<string, unknown> | null | undefined;
}

export interface RunAdapterSessionEndAutosaveOptions {
  /**
   * Optional override for the workspace cwd the autosave script will
   * `.git-walk` from. Defaults to `context.paperclipWorkspace.cwd`, falling
   * back to `process.cwd()` when neither yields an absolute path. Cloud /
   * sandbox adapters usually want to pass the orchestrator-side workspace
   * directory explicitly here; local adapters can usually omit.
   */
  workspaceCwd?: string;
  /** Optional Paperclip issue identifier, e.g. `BTCAAAAA-39074`. */
  issueId?: string | null;
  /**
   * Optional sink so the adapter's onLog can surface the snapshot outcome.
   * The helper swallows any throw from this sink — run termination must never
   * be blocked by a log write failure.
   */
  onLog?: (stream: "stdout" | "stderr", chunk: string) => void | Promise<void>;
  /** Subprocess hard timeout in milliseconds (default 30s). */
  timeoutMs?: number;
  /** Override the path to the script (tests). */
  scriptPath?: string;
  /** Override the Python interpreter (tests). */
  pythonBin?: string;
}

/**
 * Adapter-friendly convenience wrapper. Unpacks the run-id, workspace cwd, and
 * issue identifier from a Paperclip adapter execution context, then calls
 * {@link runSessionEndAutosave}. NEVER throws — adapters can call this from a
 * `finally` block without risking a cascade failure that would block run
 * termination.
 */
export async function runAdapterSessionEndAutosave(
  ctx: AdapterSessionEndAutosaveContextLike,
  options: RunAdapterSessionEndAutosaveOptions = {},
): Promise<RunSessionEndAutosaveResult> {
  const c = parseObject(ctx?.context ?? null);
  const workspaceContext = parseObject(c.paperclipWorkspace);
  const workspaceCwdRaw =
    options.workspaceCwd ?? asString(workspaceContext.cwd, "") ?? "";
  const fallbackCwd = workspaceCwdRaw.length > 0 ? workspaceCwdRaw : process.cwd();
  const explicitIssueId =
    typeof options.issueId === "string" && options.issueId.trim().length > 0
      ? options.issueId.trim()
      : null;
  const contextIssueId =
    typeof c.issueId === "string" && (c.issueId as string).trim().length > 0
      ? ((c.issueId as string).trim() as string)
      : null;
  const issueId = options.issueId !== undefined ? explicitIssueId : contextIssueId;
  try {
    return await runSessionEndAutosave({
      runId: ctx.runId,
      workspaceCwd: fallbackCwd,
      issueId,
      onLog: options.onLog,
      timeoutMs: options.timeoutMs,
      scriptPath: options.scriptPath,
      pythonBin: options.pythonBin,
    });
  } catch (err) {
    // runSessionEndAutosave is contractually non-throwing, but keep this
    // belt-and-suspenders guard so adapters can drop this into a `finally`
    // without ANY risk of throwing to their run-terminator.
    const message = err instanceof Error ? err.message : String(err);
    return { invoked: false, exitCode: null, skipped: false, reason: `helper error: ${message}` };
  }
}

// Small structural parsers local to this file (kept inline so adapter-utils
// doesn't grow a new public surface).
function parseObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asString(value: unknown, fallback: string): string | null {
  if (typeof value === "string" && value.trim().length > 0) return value;
  return fallback.length > 0 ? fallback : null;
}
