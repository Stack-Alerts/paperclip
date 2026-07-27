// worker.ts — paperclip-backup plugin worker
//
// Source for the rebuild artifact at dist/worker.js. The deployed
// dist/worker.js (currently 1730 lines of bundled TS-with-JSDoc) was the
// canonical implementation; this src/ file mirrors it so future
// `pnpm build` invocations don't regress any registered action / data /
// state key.
//
// Behaviour parity targets (all registered below):
//   actions:
//     run-backup, prune-local, restore-offsite, prune-offsite,
//     restore-local, save-config,
//     force-backup, force-restore, delete-recovery-snapshots,
//     upload-daily-backup, upload-hourly-backup, set-tier-keep
//   data:
//     listing, status, config, recovery-snapshots, gdrive-tier-status
//   jobs:
//     auto-prune-offsite

import { spawn } from "node:child_process";
import {
  existsSync,
  readFileSync,
  readdirSync,
  promises as fs,
} from "node:fs";
import nodePath from "node:path";
import path from "node:path";
import {
  definePlugin,
  runWorker,
  type PaperclipPlugin,
} from "@paperclipai/plugin-sdk";

import {
  ACTION_KEYS,
  CONFIG_VERSION,
  DATA_KEYS,
  DEFAULT_CONFIG,
  JOB_KEYS,
  PLUGIN_ID,
  RECOVERY_ACTION_KEYS,
  RECOVERY_DATA_KEYS,
  RECOVERY_SCRIPT_KEY,
  RECOVERY_SCRIPT_KEY_TIERED,
  CLEANUP_DATA_KEYS,
  CLEANUP_ACTION_KEYS,
  TIER_UPLOAD_PROGRESS_KEY,
  CLEANUP_TEST_PREFIX,
  SCRIPT_KEYS,
  STATE_KEYS,
} from "./constants.js";

// ---------------------------------------------------------------------------
// runScript — wraps a shell script call so actions can return the same
// { ok, exitCode, stdout, stderr, durationMs, message } envelope that the
// UI expects. Used by run-backup / prune-local / prune-offsite /
// restore-offsite / restore-local / save-config / set-tier-keep.
// ---------------------------------------------------------------------------
async function runScript(
  scriptPath: string,
  args: string[],
  extraEnv: Record<string, string> = {},
) {
  const startedAt = Date.now();
  return await new Promise<{
    ok: boolean;
    exitCode: number | null;
    stdout: string;
    stderr: string;
    durationMs: number;
    message: string;
  }>((resolve) => {
    if (!existsSync(scriptPath)) {
      resolve({
        ok: false,
        exitCode: null,
        stdout: "",
        stderr: "",
        durationMs: 0,
        message: `script not found: ${scriptPath}`,
      });
      return;
    }
    const child = spawn(scriptPath, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, ...extraEnv } as NodeJS.ProcessEnv,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
    child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
    child.on("exit", (code) => {
      const durationMs = Date.now() - startedAt;
      const ok = code === 0;
      resolve({
        ok,
        exitCode: code,
        stdout,
        stderr,
        durationMs,
        message: ok
          ? `${path.basename(scriptPath)} ${args.join(" ")} completed`
          : `${path.basename(scriptPath)} ${args.join(" ")} failed (exit ${code})`,
      });
    });
    child.on("error", (err) => {
      resolve({
        ok: false,
        exitCode: null,
        stdout,
        stderr: stderr + (stderr ? "\n" : "") + err.message,
        durationMs: Date.now() - startedAt,
        message: `${path.basename(scriptPath)} spawn error: ${err.message}`,
      });
    });
  });
}

// ---------------------------------------------------------------------------
// lsjsonDir — top-level helper that spawns `rclone lsjson` for a single
// remote path and returns the parsed entries. Exposed at module scope so
// the data providers (listing, gdrive-tier-status, …) can call it
// without re-implementing the rclone invocation each time.
//
// Two flavors:
//   - dirsOnly: true → adds `--dirs-only --no-modtime` for cheap enumeration
//     of directory names only (no real size / modtime). Used for the
//     year → month → day → HHMM walk.
//   - dirsOnly: false → no flags, returns real file entries with Size and
//     ModTime populated. Used for the per-leaf follow-up that gets the
//     actual backup payload size and timestamp.
// ---------------------------------------------------------------------------
type LsjsonEntry = {
  Path: string;
  Name: string;
  Size: number;
  IsDir: boolean;
  ModTime?: string;
};

// Module-level getRclonePass for use by both lsjsonDir and rcloneRun
function getRclonePass(): string {
  for (const candidate of [
    process.env.HOME ? `${process.env.HOME}/.config/rclone/rclone-pass` : null,
    "/home/sirrus/.config/rclone/rclone-pass",
    "/root/.config/rclone/rclone-pass",
  ]) {
    if (!candidate) continue;
    try {
      if (existsSync(candidate)) {
        const v = readFileSync(candidate, "utf8").trim();
        if (v) return v;
      }
    } catch {
      // ignore
    }
  }
  return "";
}

// rcloneConfigPresent — quick probe that the rclone config file actually
// exists on disk before we spawn rclone. A bogus / missing config (the
// integration-test fixture is `/nonexistent/rclone.conf`) makes rclone
// hang for 30+ seconds while it tries auth/network and eventually
// returns a config-not-found error. Every individual rclone call in
// this file goes through one of four spawn sites (rcloneRun, lsjsonDir,
// populateManifestSizes, leafHasGoldenSidecar); they all share the same
// failure mode, so we short-circuit at every spawn site instead of only
// in rcloneRun.
//
// Acceptance choice for BTCAAAAA-41513 sub: option (b) — short-circuit
// rclone with a clear error when the config file path is missing on
// disk. The alternative (option a: SIGTERM→SIGKILL after 1s) does not
// solve the test timeout because the cleanup walk fans out to ~4 rclone
// calls per tier — even at 1s/call that runs ~16s for the 4-tier walk,
// and the 15s SIGKILL fallback we'd otherwise keep is still useful as a
// backup defense for hung-but-valid-config cases. So we keep the
// existing 15s SIGKILL guard in rcloneRun AND add this fast-fail probe.
function rcloneConfigPresent(rcloneConfig: string | undefined | null): boolean {
  if (!rcloneConfig || typeof rcloneConfig !== "string") return false;
  try {
    return existsSync(rcloneConfig);
  } catch {
    return false;
  }
}

// MISSING_CONFIG_ERROR_PREFIX — canonical stderr prefix used when the
// rclone config file is missing on disk. Stable across spawn sites so
// callers/tests can pattern-match.
const MISSING_CONFIG_ERROR_PREFIX = "rclone config not found at ";

async function lsjsonDir(
  remotePath: string,
  rcloneConfig: string,
  rclonePass: string,
  opts: { dirsOnly?: boolean } = {},
): Promise<Array<LsjsonEntry>> {
  if (!rcloneConfigPresent(rcloneConfig)) {
    // Missing config — return [] (same shape rclone would emit on a
    // non-zero exit) so callers don't have to special-case the walk.
    // Avoids the 30s+ hang while rclone retries against an unset remote.
    return [];
  }
  const args = ["lsjson"];
  if (opts.dirsOnly ?? true) {
    args.push("--dirs-only", "--no-modtime");
  }
  args.push(remotePath);
  const child = spawn(
    "rclone",
    args,
    {
      env: {
        ...process.env,
        RCLONE_CONFIG: rcloneConfig,
        ...(rclonePass ? { RCLONE_CONFIG_PASS: rclonePass } : {}),
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let stdout = "";
  let stderr = "";
  let settled = false;
  child.stdout.on("data", (b) => (stdout += b.toString()));
  child.stderr.on("data", (b) => (stderr += b.toString()));
  // Wait for "close" not "exit" — "exit" can fire before the parent's
  // stdout pipe has been fully drained, which causes JSON.parse on a
  // truncated buffer to silently throw and the helper to return [].
  // "close" is emitted only after both the child has exited AND all
  // stdio streams have closed.
  const code: number = await new Promise((resolve) => {
    // Backstop valid configs whose remote never responds; 124 is the conventional timeout code.
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try {
        child.kill("SIGKILL");
      } catch {}
      stdout = "";
      stderr = `rclone timed out after ${RCLONE_HARD_TIMEOUT_MS}ms`;
      resolve(124);
    }, RCLONE_HARD_TIMEOUT_MS);
    child.on("close", (c) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(c ?? 0);
    });
  });
  if (code !== 0) return [];
  // rclone lsjson emits a single JSON ARRAY (with the directory listing),
  // not NDJSON. The line-by-line parser mis-identified the leading "["
  // and trailing "]" as malformed lines and dropped everything but the
  // single object line inside the array — that is why offsite listings
  // were returning exactly 1 entry per root even though lsjson produced
  // many. Parse the whole payload as one array; fall back to NDJSON-split
  // for rclone versions that wrap each entry on its own line.
  let entries: unknown;
  try {
    entries = JSON.parse(stdout) as unknown;
  } catch {
    entries = [];
    for (const line of stdout.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === "[" || trimmed === "]") continue;
      try {
        const arr = JSON.parse(trimmed);
        if (Array.isArray(arr)) entries = (entries as unknown[]).concat(arr);
        else (entries as unknown[]).push(arr);
      } catch {
        /* skip */
      }
    }
  }
  const arr = Array.isArray(entries) ? entries : [];
  const out: Array<LsjsonEntry> = [];
  for (const obj of arr) {
    if (!obj || typeof obj !== "object") continue;
    const e = obj as Partial<LsjsonEntry> & {
      Path?: string;
      Name?: string;
      Size?: number;
      IsDir?: boolean;
      ModTime?: string;
    };
    if (!e.Path) continue;
    out.push({
      Path: e.Path,
      Name: e.Name ?? e.Path.split("/").pop() ?? e.Path,
      Size: e.Size ?? 0,
      IsDir: !!e.IsDir,
      ModTime: e.ModTime,
    });
  }
  return out;
}

// RCLONE_HARD_TIMEOUT_MS — hard cap on a single rclone invocation. We
// need a fast failure mode so a bogus rclone config (or a hung drive)
// doesn't pin the cleanup action handlers for minutes. The default 15s
// is enough for normal lsjson/stat/rcat calls against a healthy drive
// while still failing fast in the integration tests where the config
// path is deliberately bogus.
const RCLONE_HARD_TIMEOUT_MS = 15_000;

// rcloneRun — run a single rclone command with the standard env (config
// path + optional password) and capture stdout/stderr. Returns the
// exit code, stdout, and stderr. Used by the cleanup action handlers
// to write/delete sidecars and leaves. Has a hard timeout so a hung
// rclone invocation doesn't pin the caller indefinitely.
function rcloneRun(
  args: string[],
  cfg: { rcloneConfig: string },
  pass: string,
  timeoutMs: number = RCLONE_HARD_TIMEOUT_MS,
): Promise<{ code: number; stdout: string; stderr: string; timedOut: boolean }> {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let settled = false;
    const settle = (payload: { code: number; stdout: string; stderr: string; timedOut: boolean }) => {
      if (settled) return;
      settled = true;
      resolve(payload);
    };
    if (!rcloneConfigPresent(cfg.rcloneConfig)) {
      // Missing/bogus config — short-circuit rather than letting rclone
      // hang for 30+ seconds on auth/network retries. 127 matches the
      // conventional "command not configured" exit code and is distinct
      // from the 124 timeout and from rclone's own exit codes.
      settle({
        code: 127,
        stdout: "",
        stderr: MISSING_CONFIG_ERROR_PREFIX + (cfg.rcloneConfig || "<unset>"),
        timedOut: false,
      });
      return;
    }
    try {
      const child = spawn("rclone", args, {
        env: {
          ...process.env,
          RCLONE_CONFIG: cfg.rcloneConfig,
          ...(pass ? { RCLONE_CONFIG_PASS: pass } : {}),
        },
        stdio: ["ignore", "pipe", "pipe"],
      });
      const timer = setTimeout(() => {
        try {
          child.kill("SIGKILL");
        } catch {}
        settle({
          code: 124, // conventional "timed out" code, distinct from rclone's own codes
          stdout,
          stderr: stderr + (stderr ? "\n" : "") + `rclone timed out after ${timeoutMs}ms`,
          timedOut: true,
        });
      }, timeoutMs);
      if (child.stdout) child.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
      if (child.stderr) child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
      child.on("close", (code) => {
        clearTimeout(timer);
        settle({ code: code ?? 0, stdout, stderr, timedOut: false });
      });
      child.on("error", (err) => {
        clearTimeout(timer);
        settle({ code: -1, stdout, stderr: stderr + (stderr ? "\n" : "") + err.message, timedOut: false });
      });
    } catch (err) {
      settle({ code: -1, stdout, stderr: (err as Error).message, timedOut: false });
    }
  });
}

// rcloneStat — returns true if a remote path exists (file or dir).
// rclone stat exits 0 if present, non-zero otherwise. We treat any
// non-zero (including the rclone "not found" code 9) as "missing".
async function rcloneStat(remote: string, cfg: { rcloneConfig: string }, pass: string): Promise<boolean> {
  const { code } = await rcloneRun(["stat", remote], cfg, pass);
  return code === 0;
}

// rcloneRcat — read a remote file's contents as a string.
async function rcloneRcat(remote: string, cfg: { rcloneConfig: string }, pass: string): Promise<string> {
  const { code, stdout, stderr } = await rcloneRun(["cat", remote], cfg, pass);
  if (code !== 0) {
    throw new Error(`rclone cat ${remote} failed (${code}): ${stderr.slice(0, 200)}`);
  }
  return stdout;
}

// rcloneRcatStdin — write a string to a remote file using `rclone rcat`.
// Used to publish `.golden.json` sidecars without first materializing
// a local temp file.
async function rcloneRcatStdin(
  remote: string,
  contents: string,
  cfg: { rcloneConfig: string },
  pass: string,
): Promise<{ code: number; stderr: string }> {
  if (!rcloneConfigPresent(cfg.rcloneConfig)) {
    // Missing/bogus config — short-circuit rather than letting rclone
    // hang for 30+ seconds on auth/network retries. Mirrors the fast-fail
    // in rcloneRun / lsjsonDir / populateManifestSizes / leafHasGoldenSidecar
    // so the mark-golden action handler is testable without a real drive.
    return { code: 127, stderr: MISSING_CONFIG_ERROR_PREFIX + (cfg.rcloneConfig || "<unset>") };
  }
  return await new Promise((resolve) => {
    try {
      const child = spawn("rclone", ["rcat", remote], {
        env: {
          ...process.env,
          RCLONE_CONFIG: cfg.rcloneConfig,
          ...(pass ? { RCLONE_CONFIG_PASS: pass } : {}),
        },
        stdio: ["pipe", "ignore", "pipe"],
      });
      let stderr = "";
      if (child.stderr) child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
      child.on("close", (code) => resolve({ code: code ?? 0, stderr }));
      child.on("error", (err) => resolve({ code: -1, stderr: stderr + (stderr ? "\n" : "") + err.message }));
      child.stdin?.write(contents);
      child.stdin?.end();
    } catch (err) {
      resolve({ code: -1, stderr: (err as Error).message });
    }
  });
}

// rcloneDeleteDir — delete a remote directory recursively. The
// action handler is responsible for ALL safety checks (golden flag,
// confirmDelete, scope) — this helper just executes the rclone call.
async function rcloneDeleteDir(
  remote: string,
  cfg: { rcloneConfig: string },
  pass: string,
): Promise<{ code: number; stderr: string }> {
  const { code, stderr } = await rcloneRun(["purge", remote], cfg, pass);
  return { code, stderr };
}

// isValidCleanupLeafPath — returns true if `path` is inside one of the
// four known tier roots. The regex for the per-company tier uses
// `^Paperclip-Backups/[^/]+/` so Paperclip-Backups-evil/... is rejected.
export function isValidCleanupLeafPath(path: string): boolean {
  if (typeof path !== "string" || path.length === 0) return false;
  // Strip any leading remote prefix (e.g. "gdrive/" or "gdrive:") so the
  // regex match works on either "Paperclip-Backups/..." or
  // "gdrive:Paperclip-Backups/..." or "gdrive/Paperclip-Backups/...".
  const stripped = path.replace(/^[a-zA-Z0-9_-]+[:/]/, "");
  if (/^Paperclip-Backups-evil(\/|$)/.test(stripped)) return false;
  return (
    /^Paperclip-Backups\/[^/]+\//.test(stripped) ||
    /^Paperclip-Backups\/hourly(\/|$)/.test(stripped) ||
    /^Paperclip-Backups\/daily(\/|$)/.test(stripped) ||
    /^Paperclip-Backups\/test-cleanup-panel(\/|$)/.test(stripped)
  );
}

// ---------------------------------------------------------------------------
// runWithCap — module-level helper that runs async tasks in parallel up
// to a concurrency limit. Used by the offsite and cleanup walks so the
// total rclone-call count is bounded.
// ---------------------------------------------------------------------------
async function runWithCap<T, R>(
  items: T[],
  limit: number,
  fn: (t: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = [];
  let i = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  });
  await Promise.all(workers);
  return out;
}

// ---------------------------------------------------------------------------
// Config helpers — read instance config from disk so the plugin honors the
// operator's saved settings instead of always using DEFAULT_CONFIG.
// ---------------------------------------------------------------------------
function readInstanceConfig(cfg: Record<string, unknown> = {}) {
  const env = process.env.PAPERCLIP_BACKUP_CONFIG;
  let envOverride: Record<string, unknown> | null = null;
  if (env) {
    try {
      envOverride = JSON.parse(env);
    } catch {
      envOverride = null;
    }
  }
  return { ...DEFAULT_CONFIG, ...cfg, ...(envOverride ?? {}) };
}

function resolveCompanyId(params: Record<string, unknown> | undefined) {
  // Accept the caller-provided companyId UNLESS it is the literal "default"
  // sentinel (which the dashboard passes when the active company has no UI
  // route of its own — the "default" Paperclip company). In that case we
  // want to fall through to the host company's id (BTC-Trade-Engine) so
  // /api/plugins/<backup>/data/listing can still find the right gdrive root.
  const fromParams = params?.companyId as string | undefined;
  const usable = fromParams && fromParams !== "default" ? fromParams : undefined;
  return (
    usable ??
    process.env.PAPERCLIP_COMPANY_ID ??
    // Fallback: the canonical BTC-Trade-Engine Paperclip companyId.
    // The plugin's host company is always this; hardcoding lets the
    // auto-offsite-backup job run without requiring the env var to
    // be set in the worker process.
    "73419cf3-bd37-4a7c-8782-311ccb47fced"
  );
}

// ---------------------------------------------------------------------------
// Path / rclone helpers
// ---------------------------------------------------------------------------

/**
 * Resolve the actual local DB-dump directory for the running instance.
 *
 * Priority:
 *  1. <paperclipHome>/<backupsSubdir> from the plugin's saved config
 *  2. <paperclipHome>/<worktree-name>/data/backups derived from env
 *     (PAPERCLIP_HOME + a heuristic on the parent dir name)
 *  3. <cwd>/.paperclip/config.json → .database.backup.dir
 *  4. The first existing candidate
 *  5. DEFAULT_CONFIG.backupsSubdir under DEFAULT_CONFIG.paperclipHome
 *     (always returned so the UI can show the path even if it doesn't
 *     exist on disk yet)
 *
 * Returns the resolved dir along with a "source" tag for diagnostics.
 */
function resolveLocalBackupDir(cfg: ReturnType<typeof readInstanceConfig>): {
  dir: string;
  source: "config" | "env" | "paperclip-config" | "default";
} {
  const candidates: Array<{ path: string; source: "config" | "env" | "paperclip-config" | "default" }> = [];

  // 1) Read .paperclip/config.json (the paperclip server's own config).
  //    This is the canonical, up-to-date source — the plugin's saved
  //    config can go stale when the instance moves worktrees.
  //
  //    The plugin worker is spawned by the server, which runs in
  //    <worktree>/server/. The config file lives at <worktree>/.paperclip/.
  //    Walk up from cwd looking for it.
  try {
    let dir = process.cwd();
    for (let i = 0; i < 6; i += 1) {
      const cfgPath = `${dir}/.paperclip/config.json`;
      if (existsSync(cfgPath)) {
        const raw = readFileSync(cfgPath, "utf8");
        const parsed = JSON.parse(raw) as {
          database?: { backup?: { dir?: string } };
        };
        const backupDir = parsed.database?.backup?.dir;
        if (backupDir) {
          candidates.push({ path: backupDir, source: "paperclip-config" });
        }
        break;
      }
      const parent = nodePath.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  } catch {
    /* ignore */
  }

  // 2) Env-derived (worktree)
  const envHome = process.env.PAPERCLIP_HOME;
  if (envHome) {
    const cwd = process.cwd();
    const cwdName = cwd.split("/").filter(Boolean).pop() ?? "";
    // The worktree root is typically cwd's parent when cwd is <root>/server
    const worktreeRoot = nodePath.resolve(cwd, "..");
    const worktreeName = worktreeRoot.split("/").filter(Boolean).pop() ?? "";
    if (worktreeName) {
      candidates.push({
        path: `${envHome}/instances/${worktreeName}/data/backups`,
        source: "env",
      });
    }
    if (cwdName) {
      candidates.push({
        path: `${envHome}/instances/${cwdName}/data/backups`,
        source: "env",
      });
    }
    candidates.push({ path: `${envHome}/data/backups`, source: "env" });
  }

  // 3) Saved config (lowest priority — may be stale)
  if (cfg.paperclipHome && cfg.backupsSubdir) {
    candidates.push({ path: `${cfg.paperclipHome}/${cfg.backupsSubdir}`, source: "config" });
  }

  // 4) Return the first existing candidate, or fall back to the highest-priority one
  for (const c of candidates) {
    try {
      if (existsSync(c.path)) return { dir: c.path, source: c.source };
    } catch {
      /* ignore */
    }
  }
  // 5) Return the highest-priority candidate anyway so the UI can show the path
  return {
    dir: candidates[0]?.path ?? `${cfg.paperclipHome}/${cfg.backupsSubdir}`,
    source: candidates[0]?.source ?? "default",
  };
}

/**
 * Read a local DB-dump file's metadata and return a normalized dump row
 * suitable for the listing payload.
 */
type LocalDump = {
  filename: string;
  path: string;
  sizeBytes: number;
  mtime: string;
  ageDays: number;
};

async function readLocalDumps(dir: string): Promise<LocalDump[]> {
  try {
    const entries = await fs.readdir(dir);
    const dumps: LocalDump[] = [];
    for (const name of entries) {
      if (!name.startsWith("paperclip-") || !name.endsWith(".sql.gz")) continue;
      try {
        const s = await fs.stat(`${dir}/${name}`);
        dumps.push({
          filename: name,
          path: `${dir}/${name}`,
          sizeBytes: s.size,
          mtime: s.mtime.toISOString(),
          ageDays: Math.max(0, Math.floor((Date.now() - s.mtime.getTime()) / 86_400_000)),
        });
      } catch {
        /* skip unreadable entry */
      }
    }
    dumps.sort((a, b) => (a.mtime < b.mtime ? 1 : a.mtime > b.mtime ? -1 : 0));
    return dumps;
  } catch {
    return [];
  }
}

type OffsiteKind = "perCompany" | "hourly" | "daily";

type OffsiteBackup = {
  path: string;
  modified?: string;
  sizeBytes: number;
  kind?: OffsiteKind;
};

async function readOffsiteBackups(
  cfg: ReturnType<typeof readInstanceConfig>,
  companyId: string,
): Promise<{
  remote: string;
  prefix: string;
  backups: OffsiteBackup[];
  roots: Array<{ kind: OffsiteKind; remote: string; prefix: string; count: number; totalBytes: number }>;
  _error?: string;
}> {
  const remote = cfg.rcloneRemote;
  // rclone needs RCLONE_CONFIG + RCLONE_CONFIG_PASS in its env. The plugin
  // worker is spawned by the paperclip server with very few env vars set,
  // so process.env.HOME is often empty. Look up the rclone pass file in
  // common locations, preferring whichever file actually exists.
  let pass = "";
  for (const candidate of [
    process.env.HOME ? `${process.env.HOME}/.config/rclone/rclone-pass` : null,
    "/home/sirrus/.config/rclone/rclone-pass",
    "/root/.config/rclone/rclone-pass",
  ]) {
    if (!candidate) continue;
    if (existsSync(candidate)) {
      try {
        pass = readFileSync(candidate, "utf8").trim();
        if (pass) break;
      } catch {
        /* ignore */
      }
    }
  }
  // Three offsite trees to walk:
  //   1. per-company: gdrive:Paperclip-Backups/<companyId>/<YYYY>/<MM>/<DD>/<HHMM>/
  //   2. hourly tier: gdrive:Paperclip-Backups/hourly/                (YYYY-MM-DD-HHMM leaves)
  //   3. daily tier:  gdrive:Paperclip-Backups/daily/                 (YYYY-MM-DD-HHMM leaves)
  //
  // The per-company tree is 4 levels deep; the tier trees are 1 level.
  // Each rclone lsjson call against the encrypted gdrive remote takes 1-3s
  // (first call ~30s due to crypto setup). Capped at MAX_LEAVES total
  // across all roots so the UI latency stays bounded.
  const MAX_MONTHS_PER_YEAR = 3;
  const MAX_DAYS_PER_MONTH = 7;
  const MAX_HOURS_PER_DAY = 6;
  const MAX_TIER_LEAVES = 40;
  const MAX_LEAVES = 120;

  // Newest first (alphabetical sort matches YYYY > MM > DD > HHMM)
  function newestFirst<T extends { Path: string }>(arr: T[]): T[] {
    return arr.slice().sort((a, b) => (a.Path < b.Path ? 1 : a.Path > b.Path ? -1 : 0));
  }

  const PARALLEL = 4;
  async function runWithCap<T, R>(items: T[], limit: number, fn: (t: T) => Promise<R>): Promise<R[]> {
    const out: R[] = [];
    let i = 0;
    const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (i < items.length) {
        const idx = i++;
        out[idx] = await fn(items[idx]);
      }
    });
    await Promise.all(workers);
    return out;
  }

  type Leaf = { remotePath: string; relPath: string; kind: OffsiteKind };
  const leaves: Leaf[] = [];
  const roots: Array<{ kind: OffsiteKind; remote: string; prefix: string; count: number; totalBytes: number }> = [];

  async function walkPerCompany(): Promise<void> {
    const prefix = `Paperclip-Backups/${companyId}`;
    const years = newestFirst(await lsjsonDir(`${remote}:${prefix}/`, cfg.rcloneConfig, pass));
    for (const y of years) {
      if (leaves.length >= MAX_LEAVES) break;
      if (!y.IsDir) continue;
      const monthsRaw = newestFirst(
        await lsjsonDir(`${remote}:${prefix}/${y.Path}/`, cfg.rcloneConfig, pass),
      ).slice(0, MAX_MONTHS_PER_YEAR);
      const monthPaths = monthsRaw.filter((m) => m.IsDir).map((m) => ({ y: y.Path, m }));
      const dayLists = await runWithCap(monthPaths, PARALLEL, async ({ y, m }) =>
        newestFirst(
          await lsjsonDir(`${remote}:${prefix}/${y}/${m.Path}/`, cfg.rcloneConfig, pass),
        ).slice(0, MAX_DAYS_PER_MONTH),
      );
      const dayPaths: Array<{ y: string; m: string; d: { Path: string; Name: string; IsDir: boolean } }> = [];
      for (let i = 0; i < dayLists.length; i += 1) {
        for (const d of dayLists[i] ?? []) {
          if (d.IsDir) dayPaths.push({ y: monthPaths[i].y, m: monthPaths[i].m.Path, d });
        }
      }
      const hourLists = await runWithCap(dayPaths, PARALLEL, async ({ y, m, d }) =>
        newestFirst(
          await lsjsonDir(`${remote}:${prefix}/${y}/${m}/${d.Path}/`, cfg.rcloneConfig, pass),
        ).slice(0, MAX_HOURS_PER_DAY),
      );
      for (let i = 0; i < hourLists.length; i += 1) {
        if (leaves.length >= MAX_LEAVES) break;
        for (const h of hourLists[i] ?? []) {
          if (leaves.length >= MAX_LEAVES) break;
          if (!h.IsDir) continue;
          if (!/^\d{4}$/.test(h.Name ?? h.Path)) continue;
          const rel = `${dayPaths[i].y}/${dayPaths[i].m}/${dayPaths[i].d.Path}/${h.Name ?? h.Path}`;
          leaves.push({
            remotePath: `${remote}:${prefix}/${rel}`,
            relPath: `${prefix}/${rel}`,
            kind: "perCompany",
          });
        }
      }
    }
    roots.push({ kind: "perCompany", remote: `${remote}:${prefix}`, prefix, count: 0, totalBytes: 0 });
  }

  async function walkTier(tier: "hourly" | "daily"): Promise<void> {
    const prefix = `Paperclip-Backups/${tier}`;
    const entries = newestFirst(
      await lsjsonDir(`${remote}:${prefix}/`, cfg.rcloneConfig, pass),
    )
      .filter((e) => e.IsDir)
      .slice(0, MAX_TIER_LEAVES);
    for (const e of entries) {
      if (leaves.length >= MAX_LEAVES) break;
      leaves.push({
        remotePath: `${remote}:${prefix}/${e.Path}`,
        relPath: `${prefix}/${e.Path}`,
        kind: tier,
      });
    }
    roots.push({ kind: tier, remote: `${remote}:${prefix}`, prefix, count: 0, totalBytes: 0 });
  }

  await walkPerCompany();
  await walkTier("hourly");
  await walkTier("daily");

  // For each leaf, do a follow-up rclone lsjson WITHOUT --dirs-only so
  // we get the real file metadata: Size (sum across files in the leaf
  // = backup payload size) and ModTime (newest file mtime = leaf's
  // effective modified time). The first pass uses --dirs-only to keep
  // the walk fast; this second pass is per-leaf so total cost is
  // MAX_LEAVES × ~2s ≈ 4 min worst case (cached for LISTING_TTL_MS).
  const backups: OffsiteBackup[] = [];
  const leafDetails = await runWithCap(leaves, PARALLEL, async (leaf) => {
    const files = await lsjsonDir(leaf.remotePath, cfg.rcloneConfig, pass, { dirsOnly: false });
    // If the per-leaf follow-up returned empty, the leaf was either deleted
    // between the directory walk and the follow-up, or the rclone call hit
    // a transient error. Either way, surfacing a row with sizeBytes=0 and
    // modified=null is misleading — the operator sees a "no offsite
    // backups" placeholder while the table also shows bogus 0-byte rows.
    // Skip these so the UI only reflects leaves that actually exist on disk.
    if (!files || files.length === 0) {
      return null;
    }
    let totalBytes = 0;
    let newestMtime = "";
    for (const f of files) {
      totalBytes += f.Size ?? 0;
      if (f.ModTime && (!newestMtime || f.ModTime > newestMtime)) {
        newestMtime = f.ModTime;
      }
    }
    return { leaf, totalBytes, modified: newestMtime };
  });
  for (const detail of leafDetails) {
    // Skip leaves whose per-leaf follow-up returned empty (see comment in
    // the per-leaf closure above). These are deleted/stale directories
    // that should not appear in the UI with sizeBytes=0 / modified=null.
    if (!detail) continue;
    const { leaf, totalBytes, modified } = detail;
    backups.push({
      path: leaf.relPath,
      modified: modified || undefined,
      sizeBytes: totalBytes,
      kind: leaf.kind,
    });
    const root = roots.find((r) => r.kind === leaf.kind);
    if (root) {
      root.count += 1;
      root.totalBytes += totalBytes;
    }
  }
  // Sort newest first by modified time (or path when modified is missing)
  backups.sort((a, b) => {
    const am = a.modified ?? a.path;
    const bm = b.modified ?? b.path;
    return am < bm ? 1 : am > bm ? -1 : 0;
  });

  // Pick the "primary" prefix for backwards-compat with consumers that
  // expected a single (remote, prefix) pair.
  const primaryPrefix = `Paperclip-Backups/${companyId}`;
  return { remote: `${remote}:${primaryPrefix}`, prefix: primaryPrefix, backups, roots };
}

// ---------------------------------------------------------------------------
// Listing cache
//
// The offsite listing makes an `rclone lsjson` call to Google Drive. With
// a full backup history that takes 30-60s, and the dashboard widget polls
// the status endpoint frequently. Without a cache, every poll re-runs
// rclone. Cache the most recent listing per companyId for LISTING_TTL_MS
// and refresh in the background.
// ---------------------------------------------------------------------------
// Cache the offsite listing for 5 minutes. The full rclone walk across
// year → month → day → HHMM is 4 levels deep, and the first rclone call
// against the encrypted gdrive config takes ~30s for crypto setup. With
// 5min TTL the dashboard poll is always a cache hit after the first walk,
// and the slow walk only re-runs every 5min.
const LISTING_TTL_MS = 5 * 60_000;
const listingCache = new Map<
  string,
  { at: number; listing: unknown; refreshing: boolean }
>();

// ---------------------------------------------------------------------------
// Recovery system helpers
// ---------------------------------------------------------------------------
async function findRunningBackupProcs() {
  // Minimal /proc scan — find shell children whose cmdline references
  // recovery.sh so the UI can show a "running" marker for forced snapshots
  // even if the worker's in-state marker was lost on a restart.
  const out: Array<{
    pid: number;
    cmd: string;
    startedAt: string;
  }> = [];
  try {
    const { readdir } = await fs;
    const procs = await readdir("/proc").catch(() => [] as string[]);
    for (const p of procs) {
      if (!/^\d+$/.test(p)) continue;
      try {
        const cmdline = readFileSync(`/proc/${p}/cmdline`, "utf8")
          .split("\0")
          .filter(Boolean)
          .join(" ");
        if (/recovery\.sh/.test(cmdline)) {
          const stat = readFileSync(`/proc/${p}/stat`, "utf8").split(" ");
          const startTicks = Number(stat[21]);
          const clkTck = 100;
          const uptime = readFileSync("/proc/uptime", "utf8")
            .split(" ")[0];
          const startedSecAgo = Math.max(
            0,
            Number(uptime) - startTicks / clkTck,
          );
          const startedAt = new Date(
            Date.now() - startedSecAgo * 1000,
          ).toISOString();
          out.push({ pid: Number(p), cmd: cmdline, startedAt });
        }
      } catch {
        /* proc vanished */
      }
    }
  } catch {
    /* ignore */
  }
  return out;
}

export const pluginInstance: PaperclipPlugin = definePlugin({
  async setup(ctx) {
    // ---------------------------------------------------------------------
    // Stuck-backup watchdog
    //
    // The lifecycle handlers below clear `backupRunning` when the spawned
    // child process emits "exit"/"error"/"close" — but if the child is
    // alive (waiting on rclone, etc.), none of those fire and the UI shows
    // "Working…" forever. This watchdog periodically checks if the
    // running child has been alive longer than the configured threshold,
    // and if so, SIGTERMs the child (which triggers our exit handler
    // and clears the marker). Threshold scales with the script's claimed
    // duration, with an absolute cap.
    // ---------------------------------------------------------------------
    const STUCK_BACKUP_THRESHOLD_MS = 30 * 60_000;
    {
      let killed: ReturnType<typeof setTimeout> | null = null;
      const check = async () => {
        try {
          const entry = (await ctx.state
            .get({ scopeKind: "instance", stateKey: "backup-running" })
            .catch(() => null)) as null | {
            pid?: number;
            startedAt?: string;
            script?: string;
            args?: unknown;
          };
          if (entry && typeof entry.startedAt === "string" && typeof entry.pid === "number") {
            const ageMs = Date.now() - new Date(entry.startedAt).getTime();
            if (ageMs > STUCK_BACKUP_THRESHOLD_MS) {
              // Liveness check: does the PID still exist? If the kernel
              // has reaped the zombie, process.kill throws ESRCH. Treat
              // any failure (including ESRCH) as "the script is gone" and
              // run the normal clear-handler path so the marker doesn't
              // leak. If the script is alive but stuck, SIGTERM it; the
              // child's `exit` handler will then clear the marker.
              try {
                process.kill(entry.pid, 0);
                // Liveness probe succeeded — child is alive. If it's
                // been stuck longer than the threshold, SIGTERM it. The
                // child's "exit" handler will then clear the marker.
                try {
                  process.kill(entry.pid, "SIGTERM");
                  ctx.logger.warn("paperclip-backup: stuck-running watchdog SIGTERMed child pid=" + entry.pid + " ageMs=" + ageMs);
                } catch (sendErr) {
                  ctx.logger.warn("paperclip-backup: stuck-running watchdog could not signal child pid=" + entry.pid + " err=" + (sendErr instanceof Error ? sendErr.message : String(sendErr)));
                }
              } catch {
                // ESRCH or EPERM — process already gone, fall through to clear.
              }
              // Whether the script is gone or stuck, the next status poll
              // should see an empty `running`. Clear the marker explicitly
              // in case no exit handler will fire (the script might still be
              // hung and waiting for rclone to notice the SIGTERM).
              await ctx.state
                .delete({ scopeKind: "instance", stateKey: "backup-running" })
                .catch(() => null);
            }
          }
        } catch (err) {
          ctx.logger.warn("paperclip-backup: stuck-running watchdog error: " + (err instanceof Error ? err.message : String(err)));
        }
      };
      killed = setInterval(check, 60_000);
      // One immediate check on startup so a freshly-restarted worker
      // cleans up state from a stuck previous run before the next 60s tick.
      void check();
      // Don't keep the worker alive solely for this interval — let Node
      // exit naturally when the host closes stdin / the parent dies.
      if (typeof killed.unref === "function") killed.unref();
    }

    // ---------------------------------------------------------------------
    // Data providers
    // ---------------------------------------------------------------------
    ctx.data.register(DATA_KEYS.config, async () => {
      return readInstanceConfig();
    });

    ctx.data.register(DATA_KEYS.listing, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      // Use resolveCompanyId so callers that don't pass companyId still
      // walk the right gdrive root. Falls back to PAPERCLIP_COMPANY_ID
      // env var, then the canonical BTC-Trade-Engine Paperclip companyId.
      // Without this, the UI gets `gdrive:Paperclip-Backups/default` which
      // does not exist and every offsite listing returns empty.
      const companyId = resolveCompanyId(p);
      const cfg = readInstanceConfig();
      const cached = listingCache.get(companyId);
      if (cached && Date.now() - cached.at < LISTING_TTL_MS) {
        return cached.listing;
      }
      // Cache miss. The rclone walk against the encrypted gdrive is slow
      // (~30s first call for crypto setup, then ~2s/lsjson). To avoid the
      // 30s SDK RPC timeout on the first call after worker startup, kick
      // the offsite walk off in the background and return a placeholder
      // (empty results + listingFresh: false) immediately. The next poll
      // hits the populated cache. LISTING_TTL_MS=5min keeps the slow walk
      // from running every poll.
      const inFlight = listingCache.get(companyId);
      if (inFlight && inFlight.refreshing) {
        return inFlight.listing;
      }
      const resolved = resolveLocalBackupDir(cfg);
      // Local read is fast (~50ms). Compute eagerly so the UI gets local
      // dumps immediately; offsite half is filled in by the background
      // walk that fires right after we return.
      const localDumps = await readLocalDumps(resolved.dir);
      const localBytes = localDumps.reduce((s, d) => s + d.sizeBytes, 0);
      const placeholder = {
        local: {
          count: localDumps.length,
          totalBytes: localBytes,
          dumps: localDumps,
          newest: localDumps[0]
            ? { filename: localDumps[0].filename, mtime: localDumps[0].mtime }
            : null,
          dir: resolved.dir,
          source: resolved.source,
          dirSource: resolved.source,
        },
        retention: { keep: cfg.defaultKeep ?? 10, candidates: [] },
        offsiteRetention: {
          keep: cfg.offsiteKeep ?? 30,
          candidates: 0,
          totalBytes: 0,
        },
        spaceUsage: { keep: cfg.defaultKeep ?? 10, offsiteKeep: cfg.offsiteKeep ?? 30 },
        config: cfg,
        loading: true,
        listingAt: Date.now(),
        listingFresh: false,
        requestedCompanyId: companyId,
        offsite: {
          remote: `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`,
          prefix: `Paperclip-Backups/${companyId}`,
          backups: [],
          roots: [
            { kind: "perCompany", remote: `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`, prefix: `Paperclip-Backups/${companyId}`, count: 0, totalBytes: 0 },
            { kind: "hourly", remote: `${cfg.rcloneRemote}:Paperclip-Backups/hourly`, prefix: `Paperclip-Backups/hourly`, count: 0, totalBytes: 0 },
            { kind: "daily", remote: `${cfg.rcloneRemote}:Paperclip-Backups/daily`, prefix: `Paperclip-Backups/daily`, count: 0, totalBytes: 0 },
          ],
        },
      };
      listingCache.set(companyId, { at: Date.now(), listing: placeholder, refreshing: true });
      void (async () => {
        let offsite: Awaited<ReturnType<typeof readOffsiteBackups>>;
        let offsiteError: string | null = null;
        try {
          offsite = await readOffsiteBackups(cfg, companyId);
        } catch (err) {
          offsiteError = err instanceof Error ? err.message : String(err);
          ctx.logger.warn(
            `paperclip-backup: offsite listing walk failed: companyId=${companyId} err=${offsiteError}`,
          );
          offsite = { remote: `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`, prefix: `Paperclip-Backups/${companyId}`, backups: [], roots: [{ kind: "perCompany", remote: `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`, prefix: `Paperclip-Backups/${companyId}`, count: 0, totalBytes: 0 }] };
        }
        const finalListing = { ...placeholder, offsite, offsiteError, loading: false, listingFresh: true, listingAt: Date.now() };
        listingCache.set(companyId, { at: Date.now(), listing: finalListing, refreshing: false });
      })().catch((err) => {
        ctx.logger.warn("paperclip-backup: async offsite walk failed: " + (err instanceof Error ? err.message : String(err)));
        listingCache.set(companyId, { at: Date.now(), listing: { ...placeholder, offsiteError: String(err), loading: false, listingFresh: true, listingAt: Date.now() }, refreshing: false });
      });
      return placeholder;
    });

    ctx.data.register(DATA_KEYS.status, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      // The Backup Manager dashboard widget reads status?.local.count /
      // status?.local.totalBytes / status?.offsite.count / status?.local.newest,
      // so the status handler has to compute the same local+offsite totals
      // the listing handler exposes. We resolve companyId via the same
      // fallback chain the listing handler uses.
      const companyId = resolveCompanyId(p);
      const [lastRun, running, offsiteLast, offsiteRunning] =
        await Promise.all([
          ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupLastRun })
            .catch(() => null),
          ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
            .catch(() => null),
          ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun })
            .catch(() => null),
          ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning })
            .catch(() => null),
        ]);
      // Local: read from the resolved backup dir (cheap fs walk).
      const cfg = readInstanceConfig();
      const resolved = resolveLocalBackupDir(cfg);
      const localDumps = await readLocalDumps(resolved.dir);
      const localBytes = localDumps.reduce((s, d) => s + d.sizeBytes, 0);
      const localNewest = localDumps[0] ?? null;
      // Offsite: try the listing cache first (it has the precomputed
      // walk result). If absent, surface zeros — the next listing poll
      // will populate the cache and a subsequent status poll will see
      // real numbers.
      const cached = listingCache.get(companyId);
      const cachedOffsite =
        cached && cached.listing && typeof cached.listing === "object"
          ? (cached.listing as { offsite?: { count?: number; totalBytes?: number; backups?: Array<{ modified?: string }> } })
              .offsite
          : null;
      const offsiteCount = cachedOffsite?.count ?? 0;
      const offsiteBytes = cachedOffsite?.totalBytes ?? 0;
      const newest =
        cachedOffsite?.backups && cachedOffsite.backups.length > 0
          ? cachedOffsite.backups
              .slice()
              .sort((a, b) => (a.modified ?? "") < (b.modified ?? "") ? 1 : -1)[0]
          : null;
      return {
        backupLastRun: lastRun,
        backupRunning: running,
        offsiteLastRun: offsiteLast,
        offsiteRunning,
        local: {
          count: localDumps.length,
          totalBytes: localBytes,
          newest: localNewest
            ? { filename: localNewest.filename, mtime: localNewest.mtime }
            : null,
          dir: resolved.dir,
        },
        offsite: {
          count: offsiteCount,
          totalBytes: offsiteBytes,
          newest,
        },
      };
    });

    // ---------------------------------------------------------------------
    // Actions: regular backup / restore / prune (shell-script delegation)
    // ---------------------------------------------------------------------

    // run-backup: spawn the DB-dump script and the worktree script
    // detached and return immediately. The 30s RPC timeout would
    // otherwise fire while a normal backup takes 30-60s. The UI reads
    // the "backup-running" plugin_state row to display "Working…"
    // and the new self-heal lifecycle handlers (see below) clear the
    // marker when the child exits.
    ctx.actions.register(ACTION_KEYS.runBackup, async (params: unknown) => {
      const companyId = resolveCompanyId(params as Record<string, unknown>);
      if (!companyId) {
        return {
          ok: false,
          exitCode: null,
          message: "No companyId in context or PAPERCLIP_COMPANY_ID env",
        };
      }
      const cfg = readInstanceConfig();
      const startedAt = new Date().toISOString();
      const childEnv = {
        ...process.env,
        PAPERCLIP_COMPANY_ID: companyId,
      };
      const main = spawn(cfg.backupScript, [companyId], {
        detached: true,
        stdio: "ignore",
        env: childEnv as NodeJS.ProcessEnv,
      });
      main.unref();
      // Track the main DB-dump run so the UI can show "Working…"
      await ctx.state
        .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning }, {
          pid: main.pid,
          startedAt,
          script: cfg.backupScript,
          args: [companyId],
          companyId,
          isForced: false,
          recovery: false,
        })
        .catch(() => null);
      // Fire the worktree snapshot upload in parallel (best effort —
      // doesn't affect the main DB-dump's success state). The prune-offsite
      // action trims everything under the same retention budget.
      if (cfg.worktreeBackupScript && existsSync(cfg.worktreeBackupScript)) {
        const wt = spawn(cfg.worktreeBackupScript, [], {
          detached: true,
          stdio: "ignore",
          env: childEnv as NodeJS.ProcessEnv,
        });
        wt.unref();
      }
      const clearRunning = () => {
        void ctx.state
          .delete({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
          .catch(() => null);
      };
      main.once("exit", clearRunning);
      main.once("error", clearRunning);
      main.once("close", clearRunning);
      return {
        ok: true,
        exitCode: 0,
        message: `Backup started (pid=${main.pid})`,
        pid: main.pid,
        startedAt,
        async: true,
        forced: false,
      };
    });

    ctx.actions.register(ACTION_KEYS.pruneLocal, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const keep = Number(p.keep) || 10;
      const cfg = readInstanceConfig();
      return await runScript(cfg.pruneScript, [String(keep)]);
    });

    // ---------------------------------------------------------------------
    // locations — show the operator where every backup type lives on disk
    // and on gdrive. Consumed by the UI to render a "Locations" panel
    // in the Backup Manager page so it is obvious at a glance where the
    // local DB dumps, the recovery snapshots, the per-company offsite
    // prefix, and the hourly/daily tiered-offsite prefixes all sit.
    // ---------------------------------------------------------------------
    ctx.data.register(DATA_KEYS.locations, async () => {
      const cfg = readInstanceConfig();
      const companyId =
        process.env.PAPERCLIP_COMPANY_ID ||
        "73419cf3-bd37-4a7c-8782-311ccb47fced";
      const rcloneRemote = cfg.rcloneRemote || "gdrive";
      const tierRoot = cfg.gdriveTierRoot || "Paperclip-Backups";
      const paperclipHome = cfg.paperclipHome || "/home/sirrus/.paperclip";
      const snapshotsDir =
        process.env.PAPERCLIP_RECOVERY_DIR || "/home/sirrus/paperclip-snapshots";
      const resolved = resolveLocalBackupDir(cfg);
      return {
        items: [
          {
            id: "local-db-dumps",
            kind: "local",
            path: resolved.dir,
            note: `source=${resolved.source}`,
          },
          {
            id: "recovery-snapshots",
            kind: "local",
            path: snapshotsDir,
            note: "recovery.sh snapshot --no-upload writes here",
          },
          {
            id: "offsite-per-company",
            kind: "offsite-per-company",
            path: `${rcloneRemote}:${tierRoot}/${companyId}/<YYYY>/<MM>/<DD>/<HHMM>/`,
            note: "recovery.sh snapshot + auto-offsite-backup default",
          },
          {
            id: "offsite-tier-hourly",
            kind: "offsite-tier-hourly",
            path: `${rcloneRemote}:${tierRoot}/hourly/`,
            note: "upload-hourly-backup keeps N=2",
          },
          {
            id: "offsite-tier-daily",
            kind: "offsite-tier-daily",
            path: `${rcloneRemote}:${tierRoot}/daily/`,
            note: "upload-daily-backup keeps N=3",
          },
          {
            id: "offsite-worktree",
            kind: "offsite-tier-worktree",
            path: `${rcloneRemote}:${tierRoot}/${companyId}/<YYYY>/<MM>/<DD>/<HHMM>/worktree-snapshot-*.tar.gz`,
            note: "auto-offsite-backup every 2h",
          },
          {
            id: "rclone-config",
            kind: "config",
            path: cfg.rcloneConfig || "/home/sirrus/.config/rclone/rclone.conf",
          },
          {
            id: "rclone-pass",
            kind: "config",
            path: `${process.env.HOME || "/home/sirrus"}/.config/rclone/rclone-pass`,
            note: "read at runtime by every rclone child spawn",
          },
          {
            id: "worktree-backup-script",
            kind: "config",
            path: cfg.worktreeBackupScript || `${paperclipHome}/scripts/worktree-offsite.sh`,
          },
          {
            id: "paperclip-home",
            kind: "config",
            path: paperclipHome,
          },
        ],
        generatedAt: new Date().toISOString(),
      };
    });

    ctx.actions.register(
      ACTION_KEYS.restoreOffsite,
      async (params: unknown) => {
        const companyId = resolveCompanyId(params as Record<string, unknown>);
        if (!companyId) {
          return {
            ok: false,
            exitCode: null,
            message: "No companyId in context or PAPERCLIP_COMPANY_ID env",
          };
        }
        const cfg = readInstanceConfig();
        const p = (params ?? {}) as Record<string, unknown>;
        const remotePath =
          typeof p.path === "string" && p.path.length > 0 && p.path !== "latest"
            ? p.path
            : "latest";
        const destDir = (p.destDir as string) || "/tmp/paperclip-restore";
        const r = await runScript(cfg.restoreScript, [remotePath, destDir], {
          PAPERCLIP_COMPANY_ID: companyId,
        });
        listingCache.delete(companyId);
        return {
          ...r,
          source: "offsite",
          remotePath,
          destDir,
          message: r.ok
            ? `Restored ${remotePath} → ${destDir}`
            : "Restore script failed",
        };
      },
    );

    ctx.actions.register(
      ACTION_KEYS.restoreLocal,
      async (params: unknown) => {
        const p = (params ?? {}) as Record<string, unknown>;
        const filename = p.filename as string;
        const destDir = (p.destDir as string) || "/tmp/paperclip-restore";
        if (!filename) {
          return {
            ok: false,
            exitCode: null,
            message: "filename required",
          };
        }
        const cfg = readInstanceConfig();
        const backupDir = path.join(cfg.paperclipHome, cfg.backupsSubdir);
        const src = path.join(backupDir, filename);
        if (!existsSync(src)) {
          return {
            ok: false,
            exitCode: null,
            message: `local backup not found: ${src}`,
          };
        }
        try {
          await fs.mkdir(destDir, { recursive: true });
          await fs.copyFile(src, path.join(destDir, filename));
          return {
            ok: true,
            exitCode: 0,
            stdout: `Copied ${src} → ${destDir}`,
            stderr: "",
            durationMs: 0,
            source: "local",
            destDir,
            message: `Copied ${filename} → ${destDir}`,
          };
        } catch (err) {
          return {
            ok: false,
            exitCode: null,
            stdout: "",
            stderr: (err as Error).message,
            durationMs: 0,
            message: `Local restore failed: ${(err as Error).message}`,
          };
        }
      },
    );

    ctx.actions.register(
      ACTION_KEYS.pruneOffsite,
      async (params: unknown) => {
        const companyId = resolveCompanyId(params as Record<string, unknown>);
        if (!companyId) {
          return {
            ok: false,
            exitCode: null,
            message: "No companyId in context or PAPERCLIP_COMPANY_ID env",
          };
        }
        const cfg = readInstanceConfig();
        const p = (params ?? {}) as Record<string, unknown>;
        const keep = Math.max(0, Number(p.keep) || cfg.offsiteKeep);
        // Offsite prune is a detach-and-forget operation against GDrive;
        // an immediate RPC return keeps the UI snappy. The UI reads
        // offsiteRunning/offsiteLastRun via usePluginData("status") to
        // show progress and the eventual result.
        const scriptPath =
          (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
          "/home/sirrus/.paperclip/scripts/gdrive-tiered-upload.sh";
        const args = ["prune", String(keep)];
        const child = spawn(scriptPath, args, {
          detached: true,
          stdio: "ignore",
          env: { ...process.env, PAPERCLIP_COMPANY_ID: companyId } as NodeJS.ProcessEnv,
        });
        child.unref();
        await ctx.state
          .set(
            { scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning },
            {
              pid: child.pid,
              startedAt: new Date().toISOString(),
              keep,
              companyId,
            },
          )
          .catch(() => null);
        return {
          ok: true,
          exitCode: 0,
          async: true,
          startedAt: new Date().toISOString(),
          keep,
          message: `Offsite prune started (pid=${child.pid}, keep=${keep})`,
        };
      },
    );

    ctx.actions.register(ACTION_KEYS.saveConfig, async (params: unknown) => {
      // saveConfig accepts the full config from the UI and writes it to
      // PAPERCLIP_BACKUP_CONFIG (a JSON env var) so the next readInstanceConfig
      // call picks it up. A more durable backend can replace this.
      const cfg = params as Record<string, unknown>;
      if (!cfg || typeof cfg !== "object") {
        return { ok: false, message: "config object required" };
      }
      process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify(cfg);
      return {
        ok: true,
        config: readInstanceConfig(cfg),
        message: "Saved (in-memory; persisted via PAPERCLIP_BACKUP_CONFIG env)",
      };
    });

    // ---------------------------------------------------------------------
    // Recovery-system actions
    // ---------------------------------------------------------------------

    // force-backup — spawn recovery.sh snapshot (local incremental)
    ctx.actions.register(RECOVERY_ACTION_KEYS.forceBackup, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const scriptPath =
        (p.scriptPath as string) ||
        process.env.PAPERCLIP_RECOVERY_SCRIPT ||
        "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh";
      if (!existsSync(scriptPath)) {
        return {
          ok: false,
          exitCode: null,
          message: `recovery.sh not found at ${scriptPath}`,
        };
      }
      const subcommand = (p.subcommand as string) || "snapshot";
      const noUpload = p.noUpload === false ? [] : ["--no-upload"];
      const args = [subcommand, ...noUpload].filter(Boolean);
      const startedAt = new Date().toISOString();
      // recovery.sh runs under `set -u` and references $HOME several
      // times; the plugin worker is spawned without HOME, so inject it.
      const childEnv = {
        ...process.env,
        PATH: "/home/sirrus/.local/bin:/usr/local/bin:/usr/bin:/bin:" +
          (process.env.PATH ?? ""),
        HOME: process.env.HOME || "/home/sirrus",
      };
      const child = spawn(scriptPath, args, {
        stdio: "ignore",
        env: childEnv as NodeJS.ProcessEnv,
      });
      child.unref();
      await ctx.state
        .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning }, {
          pid: child.pid,
          startedAt,
          script: scriptPath,
          args,
          companyId: null,
          isForced: true,
          recovery: true,
        })
        .catch(() => null);
      // Self-heal: if the child process dies (exit, error, signal) and
      // nobody updates the state, the UI will get stuck showing
      // "Working…" forever. Clear the marker on every terminal event so
      // the next status poll sees an empty `running` and the UI
      // recomputes the elapsed/working state.
      const clearRunning = () => {
        void ctx.state
          .delete({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
          .catch(() => null);
      };
      child.once("exit", clearRunning);
      child.once("error", clearRunning);
      child.once("close", clearRunning);
      return {
        ok: true,
        exitCode: 0,
        message: `Force backup started (pid=${child.pid})`,
        pid: child.pid,
        startedAt,
        async: true,
        forced: true,
      };
    });

    // force-restore — call recovery.sh with the chosen subcommand + id,
    // auto-confirming via --yes and feeding "restore yes\n" into stdin so
    // legacy script versions that don't yet recognise --yes still work.
    //
    // The plugin worker is spawned without HOME in its env, but recovery.sh
    // runs under `set -u` and references $HOME several times (RCLONE_CONFIG,
    // HOURLY_BACKUP_DIR, source rsync dirs). We inject HOME explicitly and
    // make sure the local pg/rclone binaries are on PATH so the script's
    // dep checks pass. Use `bash -lc` so the script gets a normal login
    // shell context (same pattern as force-backup).
    ctx.actions.register(
      RECOVERY_ACTION_KEYS.forceRestore,
      async (params: unknown) => {
        const p = (params ?? {}) as Record<string, unknown>;
        const scriptPath =
          (p.scriptPath as string) ||
          process.env.PAPERCLIP_RECOVERY_SCRIPT ||
          "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh";
        const sub = (p.subcommand as string) || "restore";
        const idOrFlag = (p.id as string) || (p.flag as string) || "list";
        const dryRun = !!p.dry_run;
        const args: string[] = [sub, idOrFlag];
        if (dryRun) args.push("--dry-run");
        if (!dryRun && sub === "restore") args.push("--yes");
        const childEnv: NodeJS.ProcessEnv = {
          ...process.env,
          PATH:
            "/home/sirrus/.local/bin:/usr/local/bin:/usr/bin:/bin:" +
            (process.env.PATH ?? ""),
          HOME: process.env.HOME || "/home/sirrus",
        };
        // Use bash -lc so the script runs as if invoked from a login shell;
        // this matches the pattern the deployed force-backup action uses
        // and ensures rclone/psql/pg_dump are found via /etc/profile.d paths.
        const bashArgs = [
          "-lc",
          "exec " +
            JSON.stringify(scriptPath) +
            " " +
            args.map((a) => JSON.stringify(a)).join(" "),
        ];
        const child = spawn("bash", bashArgs, {
          stdio: ["pipe", "pipe", "pipe"],
          env: childEnv,
        });
        if (!dryRun && sub === "restore") {
          try {
            child.stdin.write("restore yes\n");
            child.stdin.end();
          } catch {
            /* --yes alone should suffice */
          }
        } else {
          child.stdin.end();
        }
        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
        child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
        const code = await new Promise<number | null>((res) =>
          // "close" fires after "exit" once all stdio streams are
          // fully drained; using "exit" can leave stdout truncated
          // and the rclone JSON parse throws silently, returning [].
          child.on("close", (c) => res(c)),
        );
        return {
          ok: code === 0,
          exitCode: code,
          stdout,
          stderr,
          message:
            code === 0
              ? `Recovery ${sub} ${idOrFlag} completed`
              : `Recovery ${sub} ${idOrFlag} failed (exit ${code})`,
        };
      },
    );

    // delete-recovery-snapshots — protected = newest 2; refuses pattern mismatch.
    ctx.actions.register(
      RECOVERY_ACTION_KEYS.deleteRecoverySnapshots,
      async (params: unknown) => {
        const p = (params ?? {}) as Record<string, unknown>;
        const ids = Array.isArray(p.ids) ? (p.ids as string[]) : [];
        const dir =
          (p.dir as string) ||
          process.env.PAPERCLIP_RECOVERY_DIR ||
          "/home/sirrus/paperclip-snapshots";
        if (ids.length === 0) {
          return { ok: false, message: "No ids provided" };
        }
        const root = path.resolve(dir);
        let existing: string[] = [];
        try {
          existing = await fs.readdir(root);
        } catch (err) {
          return {
            ok: false,
            message: `Could not read dir ${root}: ${(err as Error).message}`,
          };
        }
        const snapshotPattern = /^\d{4}-\d{2}-\d{2}-\d{4}$/;
        const sortedDesc = existing
          .filter((n) => snapshotPattern.test(n))
          .sort()
          .reverse();
        const protectedSet = new Set(sortedDesc.slice(0, 2));
        const deleted: string[] = [];
        const skipped: Array<{ id: string; reason: string }> = [];
        const errors: Array<{ id: string; error: string }> = [];
        for (const raw of ids) {
          const id = String(raw);
          if (!snapshotPattern.test(id)) {
            skipped.push({ id, reason: "does not match YYYY-MM-DD-HHMM pattern" });
            continue;
          }
          if (protectedSet.has(id)) {
            skipped.push({ id, reason: "newest 2 snapshots are protected" });
            continue;
          }
          const target = path.join(root, id);
          try {
            await fs.rm(target, { recursive: true, force: true });
            deleted.push(id);
          } catch (err) {
            errors.push({
              id,
              error: (err as Error).message,
            });
          }
        }
        return {
          ok: errors.length === 0,
          deleted,
          skipped,
          errors,
          message:
            errors.length === 0
              ? `Deleted ${deleted.length} snapshot(s)`
              : `Deleted ${deleted.length}, ${errors.length} error(s)`,
        };
      },
    );

    // upload-daily-backup / upload-hourly-backup — kick gdrive-tiered-upload.sh
    // with the proper --tier and --keep args. The script rejects any unknown
    // positional arg, so callers must use the canonical flag form.
    const resolveTierKeep = async (
      tier: "daily" | "hourly",
    ): Promise<number> => {
      const stateKey =
        tier === "daily"
          ? "backup-tier-daily-keep"
          : "backup-tier-hourly-keep";
      const cfg = readInstanceConfig();
      const fallback = tier === "daily" ? cfg.gdriveTierDailyKeep : cfg.gdriveTierHourlyKeep;
      try {
        const raw = await ctx.state.get({
          scopeKind: "instance",
          stateKey,
        });
        if (raw && typeof raw === "object" && "keep" in raw) {
          const k = Number((raw as { keep: unknown }).keep);
          if (Number.isFinite(k) && k >= 1) return Math.floor(k);
        }
      } catch {
        /* fall through to config default */
      }
      return fallback && fallback >= 1 ? Math.floor(fallback) : tier === "daily" ? 3 : 2;
    };

    // Tier upload progress store. We capture the last few lines of
    // stderr from `gdrive-tiered-upload.sh` so the UI can show a simple
    // ticker with the rclone --stats output. stdio is now pipe (was
    // "ignore") so the user can actually see upload progress.
    type TierUploadProgress = {
      tier: "daily" | "hourly" | null;
      pid: number | null;
      startedAt: number | null;
      finishedAt: number | null;
      lines: string[];
      exitCode: number | null;
    };
    let tierUploadProgress: TierUploadProgress = {
      tier: null,
      pid: null,
      startedAt: null,
      finishedAt: null,
      lines: [],
      exitCode: null,
    };
    const TIER_UPLOAD_MAX_LINES = 6;
    const appendTierLine = (line: string): void => {
      const trimmed = line.replace(/\x1b\[[0-9;]*m/g, "").trimEnd();
      if (!trimmed) return;
      tierUploadProgress = {
        ...tierUploadProgress,
        lines: [...tierUploadProgress.lines, trimmed].slice(-TIER_UPLOAD_MAX_LINES),
      };
    };

    ctx.data.register(TIER_UPLOAD_PROGRESS_KEY, async () => tierUploadProgress);

    const startTierUpload = (tier: "daily" | "hourly", snapshotId: string, keep: number) => {
      const scriptPath =
        (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
        "/home/sirrus/paperclip-btcaaaaa-main/scripts/gdrive-tiered-upload.sh";
      if (!existsSync(scriptPath)) {
        return { ok: false, message: `tiered upload script not found: ${scriptPath}` };
      }
      const startedAt = Date.now();
      const child = spawn(
        scriptPath,
        ["--tier", tier, "--keep", String(keep), "--snapshot-id", snapshotId],
        {
          detached: true,
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
      child.unref();
      tierUploadProgress = {
        tier,
        pid: child.pid ?? null,
        startedAt,
        finishedAt: null,
        lines: [
          `Started ${tier} upload of ${snapshotId} (pid=${child.pid}, keep=${keep})`,
        ],
        exitCode: null,
      };
      const captureStream = (stream: NodeJS.ReadableStream | null) => {
        if (!stream) return;
        let buf = "";
        stream.on("data", (chunk: Buffer) => {
          buf += chunk.toString("utf8");
          let nl = buf.indexOf("\n");
          while (nl >= 0) {
            appendTierLine(buf.slice(0, nl));
            buf = buf.slice(nl + 1);
            nl = buf.indexOf("\n");
          }
        });
        stream.on("end", () => {
          if (buf.length > 0) appendTierLine(buf);
        });
      };
      captureStream(child.stderr);
      captureStream(child.stdout);
      child.on("exit", (code) => {
        tierUploadProgress = {
          ...tierUploadProgress,
          finishedAt: Date.now(),
          exitCode: code ?? null,
        };
        const tag = code === 0 ? "done" : `exit ${code}`;
        appendTierLine(`${tag} after ${Math.round((Date.now() - startedAt) / 1000)}s`);
      });
      return { ok: true, pid: child.pid, async: true };
    };

    // Pick the latest local snapshot id (the user just clicked "Upload
    // latest" — the script needs an explicit --snapshot-id to avoid
    // pulling from a different machine's snapshots dir).
    const resolveLatestSnapshotId = (): string | null => {
      const dir = process.env.PAPERCLIP_HOME
        ? `${process.env.PAPERCLIP_HOME}/paperclip-snapshots`
        : "/home/sirrus/paperclip-snapshots";
      try {
        const names = readdirSync(dir);
        return names
          .filter((n) => /^\d{4}-\d{2}-\d{2}-\d{4}$/.test(n))
          .sort()
          .pop() ?? null;
      } catch {
        return null;
      }
    };

    ctx.actions.register(
      RECOVERY_ACTION_KEYS.uploadDailyBackup,
      async () => {
        const snapshotId = resolveLatestSnapshotId();
        if (!snapshotId) {
          return { ok: false, message: "no local snapshot found to upload" };
        }
        const keep = await resolveTierKeep("daily");
        const r = startTierUpload("daily", snapshotId, keep);
        if (!r.ok) return r;
        return {
          ok: true,
          pid: r.pid,
          async: true,
          message: `Daily upload started (pid=${r.pid}, snapshot=${snapshotId}, keep=${keep}) — check on this`,
        };
      },
    );

    ctx.actions.register(
      RECOVERY_ACTION_KEYS.uploadHourlyBackup,
      async () => {
        const snapshotId = resolveLatestSnapshotId();
        if (!snapshotId) {
          return { ok: false, message: "no local snapshot found to upload" };
        }
        const keep = await resolveTierKeep("hourly");
        const r = startTierUpload("hourly", snapshotId, keep);
        if (!r.ok) return r;
        return {
          ok: true,
          pid: r.pid,
          async: true,
          message: `Hourly upload started (pid=${r.pid}, snapshot=${snapshotId}, keep=${keep}) — check on this`,
        };
      },
    );

    // set-tier-keep — write tier keep counts to plugin state so the
    // tier-status data provider can show them in the UI.
    ctx.actions.register(RECOVERY_ACTION_KEYS.setTierKeep, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const tier = String(p.tier || "");
      const keep = Math.max(1, Math.min(365, Number(p.keep) || 1));
      const stateKey =
        tier === "daily"
          ? "backup-tier-daily-keep"
          : tier === "hourly"
          ? "backup-tier-hourly-keep"
          : null;
      if (!stateKey) {
        return { ok: false, message: "tier must be 'daily' or 'hourly'" };
      }
      await ctx.state
        .set({ scopeKind: "instance", stateKey }, { keep, updatedAt: new Date().toISOString() })
        .catch(() => null);
      return { ok: true, tier, keep, message: `Set ${tier} keep = ${keep}` };
    });

    // ---------------------------------------------------------------------
    // gDrive cleanup panel — actions
    //
    // The golden sidecar `.golden.json` ALWAYS protects a leaf, no
    // matter what flags are passed. `dryRun` defaults to `true`; a
    // bare invocation is always safe. The default scope is `testOnly`
    // which only touches the test prefix. `confirmDelete:true` is
    // required for any production scope, and `allowActiveBtcCompany:true`
    // is additionally required for `perCompany` / `all`.
    // ---------------------------------------------------------------------

    // mark-golden — write or delete a `.golden.json` sidecar for the
    // given backup leaf. We never touch existing backup files — the
    // golden flag is a brand-new sidecar (or the removal of one).
    ctx.actions.register(CLEANUP_ACTION_KEYS.markGolden, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const leaf = typeof p.leaf === "string" ? p.leaf.trim() : "";
      const golden = p.golden === true;
      const setBy = typeof p.setBy === "string" ? p.setBy : "operator";
      const reason = typeof p.reason === "string" ? p.reason : "";
      if (!leaf) {
        return { ok: false, message: "leaf path required", sidecarPath: "" };
      }
      if (!isValidCleanupLeafPath(leaf)) {
        return {
          ok: false,
          message: `refusing to write sidecar outside known tier roots: ${leaf}`,
          sidecarPath: "",
        };
      }
      const cfg = readInstanceConfig();
      const pass = getRclonePass();
      // Normalize the leaf path to "<remote>:<path-without-remote-prefix>"
      const stripped = leaf.replace(/^[a-zA-Z0-9_-]+[:/]/, "");
      const remote = `${cfg.rcloneRemote}:${stripped}`;
      const sidecarRemote = remote.endsWith("/")
        ? `${remote}.golden.json`
        : `${remote}/.golden.json`;
      const sidecarPath = sidecarRemote.slice(`${cfg.rcloneRemote}:`.length);
      if (golden) {
        const payload = JSON.stringify({
          golden: true,
          setBy,
          reason,
          setAt: new Date().toISOString(),
        });
        ctx.logger.warn(
          `cleanup-panel: writing golden sidecar=${sidecarPath} setBy=${setBy} reason=${reason}`,
        );
        const { code, stderr } = await rcloneRcatStdin(sidecarRemote, payload, cfg, pass);
        if (code !== 0) {
          return {
            ok: false,
            message: `rclone rcat failed (${code}): ${stderr.slice(0, 200)}`,
            sidecarPath,
          };
        }
        return { ok: true, sidecarPath, message: `Marked ${sidecarPath} as golden` };
      }
      // unmark — delete the sidecar. rclone deletefile on a missing file
      // returns non-zero; we treat that as success (already not golden).
      ctx.logger.warn(`cleanup-panel: removing golden sidecar=${sidecarPath} setBy=${setBy}`);
      const { code, stderr } = await rcloneRun(["deletefile", sidecarRemote], cfg, pass);
      if (code !== 0 && !/not found/i.test(stderr)) {
        return {
          ok: false,
          message: `rclone deletefile failed (${code}): ${stderr.slice(0, 200)}`,
          sidecarPath,
        };
      }
      return { ok: true, sidecarPath, message: `Removed golden flag from ${sidecarPath}` };
    });

    // cleanup-stale — delete non-golden leaves older than `thresholdDays`
    // in the given scope. Defaults to testOnly + dryRun. The decision
    // logic lives in decideCleanupTargets (which honors the golden
    // flag and scope filters); this handler is just the safety gate
    // and the actual delete loop.
    ctx.actions.register(CLEANUP_ACTION_KEYS.cleanupStale, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const scopeRaw = typeof p.scope === "string" ? p.scope : "testOnly";
      const scope: "perCompany" | "hourly" | "daily" | "testOnly" | "all" =
        scopeRaw === "perCompany" ||
        scopeRaw === "hourly" ||
        scopeRaw === "daily" ||
        scopeRaw === "testOnly" ||
        scopeRaw === "all"
          ? scopeRaw
          : "testOnly";
      const dryRun = p.dryRun !== false; // default true
      const confirmDelete = p.confirmDelete === true;
      const allowActiveBtcCompany = p.allowActiveBtcCompany === true;
      const thresholdDays = Math.max(1, Math.min(365, Number(p.thresholdDays) || 14));
      const errors: string[] = [];

      // Scope-specific safety gates. We do these BEFORE any rclone
      // call so a misconfigured invocation never reaches the wire.
      if (scope !== "testOnly" && !confirmDelete) {
        errors.push(
          `refusing cleanup-stale for scope=${scope}: confirmDelete:true is required for any production scope`,
        );
        return { ok: false, scope, dryRun, thresholdDays, deleted: 0, errors };
      }
      if ((scope === "perCompany" || scope === "all") && !allowActiveBtcCompany) {
        errors.push(
          `refusing cleanup-stale for scope=${scope}: allowActiveBtcCompany:true is required (the per-company tier is the only one with real production backups)`,
        );
        return { ok: false, scope, dryRun, thresholdDays, deleted: 0, errors };
      }

      const cfg = readInstanceConfig();
      const companyId = resolveCompanyId(p);
      const roots = await listCleanupRoots(cfg, companyId);
      const decision = decideCleanupTargets(roots, { scope, thresholdDays });
      const { wouldDelete } = decision;
      const wouldDeleteBytes = wouldDelete.reduce(
        (s, l) => s + (l.coreBytes ?? 0),
        0,
      );
      const goldenSkipped = decision.goldenSkipped;
      const ageKept = decision.ageKept;

      if (dryRun) {
        // Dry run — return the wouldDelete list but do not call rclone.
        return {
          ok: true,
          scope,
          dryRun: true,
          thresholdDays,
          deleted: 0,
          wouldDelete,
          wouldDeleteBytes,
          goldenSkipped,
          ageKept,
          errors,
        };
      }
      // Real delete path. We trust decideCleanupTargets' golden check
      // (the flag is honored in this handler too) and the user's
      // confirmDelete + allowActiveBtcCompany opt-ins. We do NOT
      // re-probe sidecars here — walkCleanupTier already did that
      // and cached the result in `leaves[i].golden`.
      const pass = getRclonePass();
      let deleted = 0;
      for (const leaf of wouldDelete) {
        if (leaf.golden) {
          errors.push(`refusing to delete golden leaf: ${leaf.path}`);
          continue;
        }
        ctx.logger.warn(
          `cleanup-stale: deleting leaf path=${leaf.path} scope=${scope} thresholdDays=${thresholdDays}`,
        );
        const { code, stderr } = await rcloneDeleteDir(leaf.path, cfg, pass);
        if (code === 0) {
          deleted += 1;
        } else {
          errors.push(`rclone purge ${leaf.path} failed (${code}): ${stderr.slice(0, 200)}`);
        }
      }
      // Invalidate the listing cache so the next read reflects the deletes.
      cleanupListingCache = null;
      return {
        ok: errors.length === 0,
        scope,
        dryRun: false,
        thresholdDays,
        deleted,
        wouldDeleteBytes,
        goldenSkipped,
        ageKept,
        errors,
      };
    });

    // set-golden-cleanup-threshold — persist a preferred default
    // retention threshold (days) for the cleanup panel so the UI
    // pre-fills the form.
    ctx.actions.register(CLEANUP_ACTION_KEYS.setGoldenThreshold, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const thresholdDays = Math.max(1, Math.min(365, Number(p.thresholdDays) || 14));
      await ctx.state
        .set(
          { scopeKind: "instance", stateKey: "cleanup-default-threshold-days" },
          { thresholdDays, updatedAt: new Date().toISOString() },
        )
        .catch(() => null);
      return { ok: true, thresholdDays, message: `Set default cleanup threshold = ${thresholdDays}d` };
    });

    // ---------------------------------------------------------------------
    // Recovery-system data providers
    // ---------------------------------------------------------------------
    ctx.data.register(RECOVERY_DATA_KEYS.snapshots, async () => {
      const dir =
        process.env.PAPERCLIP_RECOVERY_DIR || "/home/sirrus/paperclip-snapshots";
      try {
        const entries = await fs.readdir(dir);
        const snaps = await Promise.all(
          entries
            .filter((n) => /^\d{4}-\d{2}-\d{2}-\d{4}$/.test(n))
            .map(async (n) => {
              const p = `${dir}/${n}`;
              const s = await fs.stat(p).catch(() => null);
              return {
                id: n,
                path: p,
                timestamp: s?.mtime?.toISOString() ?? null,
                bytes: s?.size ?? 0,
              };
            }),
        );
        snaps.sort((a, b) => (b.id < a.id ? -1 : 1));
        const runningSnapshots = await findRunningBackupProcs();
        return {
          dir,
          snapshots: snaps,
          count: snaps.length,
          runningSnapshots,
        };
      } catch (err) {
        const runningSnapshots = await findRunningBackupProcs().catch(
          () => [] as Array<{ pid: number; cmd: string; startedAt: string }>,
        );
        return {
          dir,
          snapshots: [],
          count: 0,
          runningSnapshots,
          error: (err as Error).message,
        };
      }
    });

    ctx.data.register(RECOVERY_DATA_KEYS.recoveryStatus, async () => {
      const [last, running] = await Promise.all([
        ctx.state
          .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupLastRun })
          .catch(() => null),
        ctx.state
          .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
          .catch(() => null),
      ]);
      return { last, running };
    });

    ctx.data.register(RECOVERY_DATA_KEYS.tierStatus, async () => {
      const [dailyKeepRaw, hourlyKeepRaw] = await Promise.all([
        ctx.state
          .get({ scopeKind: "instance", stateKey: "backup-tier-daily-keep" })
          .catch(() => null),
        ctx.state
          .get({ scopeKind: "instance", stateKey: "backup-tier-hourly-keep" })
          .catch(() => null),
      ]);
      const dailyKeep =
        dailyKeepRaw && typeof dailyKeepRaw === "object" && "keep" in dailyKeepRaw
          ? (dailyKeepRaw as { keep: number }).keep
          : 3;
      const hourlyKeep =
        hourlyKeepRaw && typeof hourlyKeepRaw === "object" && "keep" in hourlyKeepRaw
          ? (hourlyKeepRaw as { keep: number }).keep
          : 2;
      // Look up the actual current counts of snapshots in each tier by
      // listing the corresponding gdrive directories. The UI shows the
      // count next to each tier so the user can see at a glance whether
      // retention has been enforced.
      const cfg = readInstanceConfig();
      const rclonePassFile = `${process.env.HOME ?? "/home/sirrus"}/.config/rclone/rclone-pass`;
      let rclonePass = "";
      try {
        if (existsSync(rclonePassFile)) {
          rclonePass = readFileSync(rclonePassFile, "utf8").trim();
        }
      } catch {
        /* ignore */
      }
      const tierRoot =
        (cfg as { gdriveTierRoot?: string }).gdriveTierRoot || "Paperclip-Backups";
      const remote =
        (cfg as { rcloneRemote?: string }).rcloneRemote || "gdrive";
      const listTier = async (tier: "daily" | "hourly") => {
        try {
          const items = await lsjsonDir(
            `${remote}:${tierRoot}/${tier}/`,
            cfg.rcloneConfig,
            rclonePass,
          );
          return items
            .map((i: LsjsonEntry) => ({ id: i.Name, path: i.Path }))
            .sort((a: { id: string }, b: { id: string }) =>
              a.id < b.id ? 1 : a.id > b.id ? -1 : 0,
            );
        } catch {
          return [];
        }
      };
      const [dailyItems, hourlyItems] = await Promise.all([
        listTier("daily"),
        listTier("hourly"),
      ]);
      // The prebuilt UI bundle reads this payload in `TierPanel` /
      // `Tier` and expects the fields at the top level (not nested
      // under each tier). Specifically it reads:
      //   tierStatus.daily / tierStatus.hourly — raw items arrays
      //   tierStatus.keep.daily / .hourly — keep counts
      //   tierStatus.counts.daily / .hourly — current counts
      //   tierStatus.lastUpload.daily / .hourly — most recent timestamp
      //   tierStatus.errors.daily / .hourly — per-tier error strings
      //   tierStatus.tierRoot — displayed as "root: <tierRoot>"
      //   tierStatus.enabled — gates the "Tiered backup is disabled" notice
      // Returning the items inline at the top level (so `tierStatus.daily`
      // is the items array the UI maps over) while keeping the per-tier
      // counts and keep values in sibling top-level fields.
      return {
        enabled: true,
        tierRoot,
        keep: { daily: dailyKeep, hourly: hourlyKeep },
        counts: { daily: dailyItems.length, hourly: hourlyItems.length },
        lastUpload: { daily: null, hourly: null },
        errors: { daily: null, hourly: null },
        daily: dailyItems,
        hourly: hourlyItems,
      };
    });

    // ---------------------------------------------------------------------
    // ---------------------------------------------------------------------
    // gDrive cleanup panel — operators can flag a backup leaf as "golden"
    // (protected from cleanup-stale) by creating a sidecar `.golden.json`
    // next to it. We never touch existing backup files. The golden flag
    // is a brand-new sidecar, and the cleanup-stale action only deletes
    // leaves without that sidecar (and that are older than the configured
    // retention threshold).
    //
    // Defense-in-depth safety model:
    //   1. The golden sidecar `.golden.json` ALWAYS protects a leaf,
    //      no matter what flags are passed.
    //   2. `dryRun` defaults to `true` — a bare invocation is always safe.
    //   3. The default scope is `testOnly` — never touches real backups.
    //   4. `confirmDelete:true` is required for any production scope.
    //   5. `allowActiveBtcCompany:true` is required for the per-company
    //      tier (the only tier containing real production backups).
    // ---------------------------------------------------------------------
    type CleanupLeaf = {
      path: string;
      modified: string;
      sizeBytes: number;
      coreBytes?: number;
      changesBytes?: number;
      fileCount?: number;
      kind: "perCompany" | "hourly" | "daily";
      golden: boolean;
    };
    type CleanupTierSummary = {
      kind: "perCompany" | "hourly" | "daily";
      remote: string;
      prefix: string;
      count: number;
      totalBytes: number;
      goldenCount: number;
      goldenBytes: number;
      leaves: CleanupLeaf[];
    };

    function emptyTierSummary(tier: { kind: "perCompany" | "hourly" | "daily"; remote: string; prefix: string }): CleanupTierSummary {
      return {
        kind: tier.kind,
        remote: `${tier.remote}/${tier.prefix}`,
        prefix: tier.prefix,
        count: 0,
        totalBytes: 0,
        goldenCount: 0,
        goldenBytes: 0,
        leaves: [],
      };
    }

    // populateManifestSizes — read manifest.json from each leaf and
    // back-fill coreBytes (totalBytes) and changesBytes (deltaBytes). The
    // upload script writes these values after each upload, so reading the
    // manifest is the authoritative source of leaf size — much faster than
    // walking each leaf directory. Runs in parallel and falls back silently
    // if a leaf has no manifest (older snapshots, deleted files, etc.).
    async function populateManifestSizes(
      leaves: CleanupLeaf[],
      cfg: ReturnType<typeof readInstanceConfig>,
      pass: string,
      tier: { kind: "perCompany" | "hourly" | "daily" },
    ): Promise<void> {
      if (leaves.length === 0) return;
      const settled = await Promise.all(
        leaves.map(
          (leaf) =>
            new Promise<CleanupLeaf>((resolve) => {
              try {
                if (!rcloneConfigPresent(cfg.rcloneConfig)) {
                  // Missing config — resolve with the leaf unchanged.
                  // Same effect as a silent rclone failure but without
                  // the 30s+ spawn-and-retry hang.
                  resolve(leaf);
                  return;
                }
                const manifestPath = leaf.path.endsWith("/")
                  ? `${leaf.path}manifest.json`
                  : `${leaf.path}/manifest.json`;
                const c = spawn("rclone", ["cat", manifestPath], {
                  env: {
                    ...process.env,
                    RCLONE_CONFIG: cfg.rcloneConfig,
                    ...(pass ? { RCLONE_CONFIG_PASS: pass } : {}),
                  },
                  stdio: ["ignore", "pipe", "pipe"],
                });
                let stdout = "";
                if (c.stdout)
                  c.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
                const finish = () => {
                  try {
                    const m = JSON.parse(stdout);
                    const totalBytes =
                      typeof m.totalBytes === "number" && m.totalBytes > 0
                        ? m.totalBytes
                        : undefined;
                    const deltaBytes =
                      tier.kind === "hourly" &&
                      typeof m.deltaBytes === "number" &&
                      m.deltaBytes > 0
                        ? m.deltaBytes
                        : undefined;
                    resolve({
                      ...leaf,
                      coreBytes: totalBytes,
                      changesBytes: deltaBytes,
                    });
                  } catch {
                    resolve(leaf);
                  }
                };
                c.on("close", finish);
                c.on("error", () => resolve(leaf));
              } catch {
                resolve(leaf);
              }
            }),
        ),
      );
      for (let i = 0; i < leaves.length; i++) leaves[i] = settled[i];
    }

    // leafHasGoldenSidecar — returns true if `<leaf>/.golden.json`
    // exists on the remote. Used to mark each CleanupLeaf with its
    // golden status during walkCleanupTier. We use `rclone stat`
    // because the remote may be a crypt overlay; stat works for both
    // encrypted and unencrypted remotes. Any non-zero exit is treated
    // as "not golden" (the typical non-zero code is 9 = not-found).
    function leafHasGoldenSidecar(
      leaf: CleanupLeaf,
      cfg: ReturnType<typeof readInstanceConfig>,
      pass: string,
    ): Promise<boolean> {
      const remote = leaf.path.endsWith("/")
        ? `${leaf.path}.golden.json`
        : `${leaf.path}/.golden.json`;
      return new Promise<boolean>((resolve) => {
        try {
          if (!rcloneConfigPresent(cfg.rcloneConfig)) {
            // Missing config — treat as "not golden" so the cleanup
            // walker keeps moving without a 30s+ spawn hang.
            resolve(false);
            return;
          }
          const c = spawn("rclone", ["stat", remote], {
            env: {
              ...process.env,
              RCLONE_CONFIG: cfg.rcloneConfig,
              ...(pass ? { RCLONE_CONFIG_PASS: pass } : {}),
            },
            stdio: ["ignore", "ignore", "ignore"],
          });
          c.on("close", (code) => resolve(code === 0));
          c.on("error", () => resolve(false));
        } catch {
          resolve(false);
        }
      });
    }

    async function walkCleanupTier(
      cfg: ReturnType<typeof readInstanceConfig>,
      tier: { kind: "perCompany" | "hourly" | "daily"; remote: string; prefix: string },
    ): Promise<CleanupTierSummary> {
      // The per-company tier has 4 levels of nesting and many rclone
      // calls. To fit in the 30s RPC timeout we limit the walk to the
      // most recent months. The hourly/daily tiers are 1 level and
      // complete in <1s.
      const MAX_MONTHS = tier.kind === "perCompany" ? 1 : 12;
      const MAX_DAYS = tier.kind === "perCompany" ? 7 : 1;
      const pass = getRclonePass();
      const leaves: CleanupLeaf[] = [];
      try {
        if (tier.kind === "perCompany") {
          // per-company: YYYY/MM/DD/HHMM (data may be shallower)
          const year = (
            await lsjsonDir(`${tier.remote}:${tier.prefix}/`, cfg.rcloneConfig, pass)
          ).filter((y) => y.IsDir && /^\d{4}$/.test(y.Name))[0];
          if (!year) {
            return emptyTierSummary(tier);
          }
          const months = (
            await lsjsonDir(
              `${tier.remote}:${tier.prefix}/${year.Name}/`,
              cfg.rcloneConfig,
              pass,
            )
          )
            .filter((m) => m.IsDir && /^\d{2}$/.test(m.Name))
            .slice(0, MAX_MONTHS);
          for (const m of months) {
            const days = (
              await lsjsonDir(
                `${tier.remote}:${tier.prefix}/${year.Name}/${m.Name}/`,
                cfg.rcloneConfig,
                pass,
              )
            )
              .filter((d) => d.IsDir && /^\d{2}$/.test(d.Name))
              .slice(0, MAX_DAYS);
            if (days.length === 0) {
              leaves.push({
                path: `${tier.remote}:${tier.prefix}/${year.Name}/${m.Name}`,
                modified: m.ModTime ?? year.ModTime ?? "",
                sizeBytes: 0,
                kind: tier.kind,
                golden: false,
              });
              continue;
            }
            for (const d of days) {
              leaves.push({
                path: `${tier.remote}:${tier.prefix}/${year.Name}/${m.Name}/${d.Name}`,
                modified: d.ModTime ?? "",
                sizeBytes: 0,
                kind: tier.kind,
                golden: false,
              });
            }
          }
        } else {
          // hourly / daily: YYYY-MM-DD-HHMM leaves (1 level)
          const entries = (
            await lsjsonDir(`${tier.remote}:${tier.prefix}/`, cfg.rcloneConfig, pass)
          )
            .filter((e) => e.IsDir)
            .slice(0, 40);
          for (const e of entries) {
            leaves.push({
              path: `${tier.remote}:${tier.prefix}/${e.Name}`,
              modified: e.ModTime ?? "",
              sizeBytes: 0,
              kind: tier.kind,
              golden: false,
            });
          }
        }
      } catch {
        // fall through — empty tier
      }
      // Read manifest.json for each leaf to get authoritative totalBytes /
      // deltaBytes. The upload script writes these values after each
      // upload. Reading the manifest is fast (1-2KB per call) and runs in
      // parallel — we don't walk any leaf directories. Falls back silently
      // if a leaf has no manifest (older snapshots, deleted files, etc.).
      await populateManifestSizes(leaves, cfg, pass, tier);
      // Probe each leaf for a `.golden.json` sidecar in parallel and
      // set the `golden` flag. Without this probe the flag stays false
      // and decideCleanupTargets has no signal to skip protected leaves.
      // rclone `stat` returns exit 0 if the file exists, 9 (not found)
      // otherwise — we treat any non-zero as "not golden".
      if (leaves.length > 0) {
        const goldenFlags = await Promise.all(
          leaves.map((leaf) => leafHasGoldenSidecar(leaf, cfg, pass)),
        );
        for (let i = 0; i < leaves.length; i++) {
          if (goldenFlags[i]) {
            leaves[i] = { ...leaves[i], golden: true };
          }
        }
      }
      const totalBytes = leaves.reduce((s, l) => s + (l.coreBytes ?? 0), 0);
      const goldenCount = leaves.filter((l) => l.golden).length;
      const goldenBytes = leaves
        .filter((l) => l.golden)
        .reduce((s, l) => s + (l.coreBytes ?? 0), 0);
      return {
        kind: tier.kind,
        remote: `${tier.remote}/${tier.prefix}`,
        prefix: tier.prefix,
        count: leaves.length,
        totalBytes,
        goldenCount,
        goldenBytes,
        leaves: leaves.sort((a, b) => (a.path < b.path ? 1 : a.path > b.path ? -1 : 0)),
      };
    }

    async function listCleanupRoots(
      cfg: ReturnType<typeof readInstanceConfig>,
      companyId: string,
    ): Promise<CleanupTierSummary[]> {
      const results: CleanupTierSummary[] = [];
      try {
        results.push(
          await walkCleanupTier(cfg, {
            kind: "perCompany",
            remote: cfg.rcloneRemote,
            prefix: `Paperclip-Backups/${companyId}`,
          }),
        );
      } catch {
        results.push(emptyTierSummary({
          kind: "perCompany",
          remote: cfg.rcloneRemote,
          prefix: `Paperclip-Backups/${companyId}`,
        }));
      }
      results.push(
        await walkCleanupTier(cfg, {
          kind: "hourly",
          remote: cfg.rcloneRemote,
          prefix: "Paperclip-Backups/hourly",
        }),
      );
      results.push(
        await walkCleanupTier(cfg, {
          kind: "daily",
          remote: cfg.rcloneRemote,
          prefix: "Paperclip-Backups/daily",
        }),
      );
      results.push(
        await walkCleanupTier(cfg, {
          kind: "perCompany",
          remote: cfg.rcloneRemote,
          prefix: CLEANUP_TEST_PREFIX,
        }),
      );
      return results;
    }

    function decideCleanupTargets(
      roots: CleanupTierSummary[],
      opts: {
        scope: "perCompany" | "hourly" | "daily" | "testOnly" | "all";
        thresholdDays: number;
        allowActiveBtcCompany?: boolean;
      },
    ): {
      wouldDelete: CleanupLeaf[];
      goldenSkipped: CleanupLeaf[];
      ageKept: CleanupLeaf[];
      scopeErrors: string[];
    } {
      const thresholdMs = opts.thresholdDays * 86_400_000;
      const cutoff = Date.now() - thresholdMs;
      const wouldDelete: CleanupLeaf[] = [];
      const goldenSkipped: CleanupLeaf[] = [];
      const ageKept: CleanupLeaf[] = [];
      const scopeErrors: string[] = [];
      // Mirror the cleanup-stale action's scope guard: the per-company
      // tier holds real production backups, so any caller targeting
      // perCompany / all without the explicit allowActiveBtcCompany
      // opt-in must be rejected before we return wouldDelete.
      // The preview data provider relies on scopeErrors for this signal;
      // the cleanup-stale action enforces it independently in its own
      // pre-walk gate.
      if ((opts.scope === "perCompany" || opts.scope === "all") && opts.allowActiveBtcCompany !== true) {
        scopeErrors.push(
          `refusing cleanup-preview for scope=${opts.scope}: allowActiveBtcCompany:true is required (the per-company tier is the only one with real production backups)`,
        );
      }
      for (const root of roots) {
        if (opts.scope === "perCompany" && root.kind !== "perCompany") continue;
        if (opts.scope === "hourly" && root.kind !== "hourly") continue;
        if (opts.scope === "daily" && root.kind !== "daily") continue;
        if (opts.scope === "testOnly" && !root.prefix.startsWith(CLEANUP_TEST_PREFIX)) continue;
        for (const leaf of root.leaves) {
          if (leaf.golden) {
            goldenSkipped.push(leaf);
            continue;
          }
          const mtime = leaf.modified ? Date.parse(leaf.modified) : NaN;
          if (Number.isFinite(mtime) && mtime < cutoff) {
            wouldDelete.push(leaf);
          } else {
            ageKept.push(leaf);
          }
        }
      }
      return { wouldDelete, goldenSkipped, ageKept, scopeErrors };
    }

    // Cleanup panel listing cache (60s TTL) — the walk does 1+ rclone
    // calls per tier which can take a few seconds combined.
    let cleanupListingCache: {
      expiresAt: number;
      payload: {
        roots: CleanupTierSummary[];
        totals: { count: number; totalBytes: number; goldenCount: number; goldenBytes: number };
        config: ReturnType<typeof readInstanceConfig>;
        cleanupPath: string;
        testPrefix: string;
      };
    } | null = null;
    const CLEANUP_LISTING_TTL_MS = 60_000;

    ctx.data.register(CLEANUP_DATA_KEYS.listing, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const forceRefresh = p._forceRefresh === true;
      const now = Date.now();
      if (!forceRefresh && cleanupListingCache && cleanupListingCache.expiresAt > now) {
        return cleanupListingCache.payload;
      }
      const cfg = readInstanceConfig();
      const companyId = resolveCompanyId(p);
      const roots = await listCleanupRoots(cfg, companyId);
      const totals = roots.reduce(
        (acc, r) => {
          acc.count += r.count;
          acc.totalBytes += r.totalBytes;
          acc.goldenCount += r.goldenCount;
          acc.goldenBytes += r.goldenBytes;
          return acc;
        },
        { count: 0, totalBytes: 0, goldenCount: 0, goldenBytes: 0 },
      );
      const payload = {
        roots,
        totals,
        config: cfg,
        cleanupPath: `${cfg.rcloneRemote}/Paperclip-Backups/`,
        testPrefix: CLEANUP_TEST_PREFIX,
      };
      cleanupListingCache = { payload, expiresAt: now + CLEANUP_LISTING_TTL_MS };
      return payload;
    });

    // Safe dry-run preview: always returns wouldDelete/ageKept counts
    // without touching any data. The UI uses this to render the
    // "would delete" list before the user confirms a real cleanup.
    ctx.data.register(CLEANUP_DATA_KEYS.preview, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const cfg = readInstanceConfig();
      const thresholdDays = Math.max(
        1,
        Math.min(365, Number(p.thresholdDays) || 14),
      );
      const scopeRaw = typeof p.scope === "string" ? p.scope : "testOnly";
      const scope: "perCompany" | "hourly" | "daily" | "testOnly" | "all" =
        scopeRaw === "perCompany" || scopeRaw === "hourly" || scopeRaw === "daily" || scopeRaw === "testOnly" || scopeRaw === "all"
          ? scopeRaw
          : "testOnly";
      const allowActiveBtcCompany = p.allowActiveBtcCompany === true;
      const companyId = resolveCompanyId(p);
      const roots = await listCleanupRoots(cfg, companyId);
      const decision = decideCleanupTargets(roots, { scope, thresholdDays, allowActiveBtcCompany });
      // If the scope guard rejected the request, surface wouldDelete=0
      // so the UI can't accidentally render a "would delete" list from a
      // refused preview. The guard message is in scopeErrors.
      const wouldDeleteCount = decision.scopeErrors.length > 0 ? 0 : decision.wouldDelete.length;
      const wouldDeleteBytes = decision.scopeErrors.length > 0
        ? 0
        : decision.wouldDelete.reduce((s, l) => s + l.sizeBytes, 0);
      return {
        scope,
        thresholdDays,
        dryRun: true,
        wouldDelete: decision.wouldDelete.map((leaf: CleanupLeaf) => ({
          path: leaf.path,
          modified: leaf.modified,
          sizeBytes: leaf.sizeBytes,
          kind: leaf.kind,
        })),
        wouldDeleteCount,
        wouldDeleteBytes,
        goldenSkippedCount: decision.goldenSkipped.length,
        ageKeptCount: decision.ageKept.length,
        scopeErrors: decision.scopeErrors,
      };
    });

    // rclone encryption password lookup
    function getRclonePass(): string {
      for (const candidate of [
        process.env.HOME ? `${process.env.HOME}/.config/rclone/rclone-pass` : null,
        "/home/sirrus/.config/rclone/rclone-pass",
        "/root/.config/rclone/rclone-pass",
      ]) {
        if (!candidate) continue;
        if (existsSync(candidate)) {
          try {
            const v = readFileSync(candidate, "utf8").trim();
            if (v) return v;
          } catch {
            // ignore
          }
        }
      }
      return "";
    }

        // Scheduled job: auto-prune offsite backups
    // ---------------------------------------------------------------------
    // Fire-and-forget the prune script so the 5-min runJob RPC timeout
    // doesn't kill an in-flight prune of a large offsite set.
    ctx.jobs.register(JOB_KEYS.autoPruneOffsite, async () => {
      const cfg = readInstanceConfig();
      const keep = cfg.offsiteKeep;
      if (!keep || keep <= 0) {
        // job handlers must return void
        return;
      }
      const companyId = resolveCompanyId(undefined);
      const child = spawn(
        cfg.backupScript,
        [companyId, "--prune-offsite"],
        {
          detached: true,
          stdio: "ignore",
          env: {
            ...process.env,
            PAPERCLIP_COMPANY_ID: companyId,
          } as NodeJS.ProcessEnv,
        },
      );
      child.unref();
      ctx.logger.info(
        `auto-prune-offsite: spawned offsite prune pid=${child.pid} companyId=${companyId} keep=${keep} script=${cfg.backupScript}`,
      );
    });

    // ---------------------------------------------------------------------
    // Scheduled job: auto offsite backup (DB + worktree) every 2h
    // ---------------------------------------------------------------------
    // Fire-and-forget the heavy DB-dump + worktree snapshot scripts so the
    // 5-minute runJob RPC timeout doesn't kill an upload that legitimately
    // takes longer than that (1.5GB+ at home-Wi-Fi speeds). The run-backup
    // action tracks the running PID via plugin_state so the UI / status
    // endpoint can reflect it. The RPC resolves as soon as the spawn
    // returns; the actual backup runs detached in the background.
    ctx.jobs.register(JOB_KEYS.autoOffsiteBackup, async () => {
      const cfg = readInstanceConfig();
      const companyId = resolveCompanyId(undefined);
      if (!cfg.worktreeBackupEnabled) return;
      const env = { PAPERCLIP_COMPANY_ID: companyId };
      const main = spawn(cfg.backupScript, [companyId], {
        detached: true,
        stdio: "ignore",
        env: { ...process.env, ...env } as NodeJS.ProcessEnv,
      });
      main.unref();
      ctx.logger.info(
        `auto-offsite-backup: spawned main DB-dump upload pid=${main.pid} companyId=${companyId} script=${cfg.backupScript}`,
      );
      // 2) Worktree snapshot upload (same gdrive prefix; prune-offsite
      //    trims them together under the configured retention count).
      if (cfg.worktreeBackupScript && existsSync(cfg.worktreeBackupScript)) {
        const wt = spawn(cfg.worktreeBackupScript, [], {
          detached: true,
          stdio: "ignore",
          env: { ...process.env, ...env } as NodeJS.ProcessEnv,
        });
        wt.unref();
ctx.logger.info(
        `auto-offsite-backup: spawned worktree snapshot upload pid=${wt.pid} companyId=${companyId} script=${cfg.worktreeBackupScript}`,
      );
      }
    });

    // ---------------------------------------------------------------------
    // Scheduled job: tiered-hourly-upload
    // Promote the latest recovery snapshot into the gdrive 'hourly' tier
    // so the last ~6h of state stays recoverable at short retention.
    // Invokes gdrive-tiered-upload.sh with --tier hourly --keep N (where
    // N comes from the configured gdriveTierHourlyKeep, fallback 2).
    // ---------------------------------------------------------------------
    ctx.jobs.register(JOB_KEYS.tieredHourlyUpload, async () => {
      const cfg = readInstanceConfig();
      const tierScriptPath =
        (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
        "/home/sirrus/paperclip-btcaaaaa-main/scripts/gdrive-tiered-upload.sh";
      if (!existsSync(tierScriptPath)) {
        ctx.logger.warn(`tiered-hourly-upload: script not found: ${tierScriptPath}`);
        return;
      }
      const keep = cfg.gdriveTierHourlyKeep && cfg.gdriveTierHourlyKeep >= 1
        ? Math.floor(cfg.gdriveTierHourlyKeep)
        : 2;
      const child = spawn(
        tierScriptPath,
        ["--tier", "hourly", "--keep", String(keep)],
        {
          detached: true,
          stdio: "ignore",
        },
      );
      child.unref();
      ctx.logger.info(
        `tiered-hourly-upload: spawned tier promotion pid=${child.pid} keep=${keep} tier=hourly`,
      );
    });

    // ---------------------------------------------------------------------
    // Scheduled job: tiered-daily-upload
    // Promote the latest recovery snapshot into the gdrive 'daily' tier
    // so the last ~3 days of state stays recoverable at medium retention.
    // ---------------------------------------------------------------------
    ctx.jobs.register(JOB_KEYS.tieredDailyUpload, async () => {
      const cfg = readInstanceConfig();
      const tierScriptPath =
        (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
        "/home/sirrus/paperclip-btcaaaaa-main/scripts/gdrive-tiered-upload.sh";
      if (!existsSync(tierScriptPath)) {
        ctx.logger.warn(`tiered-daily-upload: script not found: ${tierScriptPath}`);
        return;
      }
      const keep = cfg.gdriveTierDailyKeep && cfg.gdriveTierDailyKeep >= 1
        ? Math.floor(cfg.gdriveTierDailyKeep)
        : 3;
      const child = spawn(
        tierScriptPath,
        ["--tier", "daily", "--keep", String(keep)],
        {
          detached: true,
          stdio: "ignore",
        },
      );
      child.unref();
      ctx.logger.info(
        `tiered-daily-upload: spawned tier promotion pid=${child.pid} keep=${keep} tier=daily`,
      );
    });
  },
});

// Allow running the worker directly via `node ./dist/worker.js` for
// development.
export default pluginInstance;
if (process.argv[1] && process.argv[1].endsWith("worker.js")) {
  runWorker(pluginInstance, import.meta.url);
}