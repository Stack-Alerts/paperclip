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
// lsjsonDir — top-level helper that spawns `rclone lsjson --dirs-only`
// for a single remote path and returns the parsed entries. Exposed at
// module scope so the data providers (listing, gdrive-tier-status, …)
// can call it without re-implementing the rclone invocation each time.
// ---------------------------------------------------------------------------
type LsjsonEntry = {
  Path: string;
  Name: string;
  Size: number;
  IsDir: boolean;
  ModTime?: string;
};

async function lsjsonDir(
  remotePath: string,
  rcloneConfig: string,
  rclonePass: string,
): Promise<Array<LsjsonEntry>> {
  const child = spawn(
    "rclone",
    ["lsjson", "--dirs-only", "--no-modtime", remotePath],
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
  child.stdout.on("data", (b) => (stdout += b.toString()));
  child.stderr.on("data", (b) => (stderr += b.toString()));
  const code: number = await new Promise((res) => child.on("exit", (c) => res(c ?? 0)));
  if (code !== 0) return [];
  const out: Array<LsjsonEntry> = [];
  for (const line of stdout.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const obj = JSON.parse(trimmed) as Partial<LsjsonEntry> & {
        Path?: string;
        Name?: string;
        Size?: number;
        IsDir?: boolean;
        ModTime?: string;
      };
      if (!obj.Path) continue;
      out.push({
        Path: obj.Path,
        Name: obj.Name ?? obj.Path.split("/").pop() ?? obj.Path,
        Size: obj.Size ?? 0,
        IsDir: !!obj.IsDir,
        ModTime: obj.ModTime,
      });
    } catch {
      /* skip */
    }
  }
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
  return (
    (params?.companyId as string | undefined) ??
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

type OffsiteBackup = {
  path: string;
  modified?: string;
  sizeBytes: number;
};

async function readOffsiteBackups(
  cfg: ReturnType<typeof readInstanceConfig>,
  companyId: string,
): Promise<{ remote: string; prefix: string; backups: OffsiteBackup[]; _error?: string }> {
  const remote = cfg.rcloneRemote;
  const prefix = `Paperclip-Backups/${companyId}`;
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
  // The offsite tree is gdrive:Paperclip-Backups/<companyId>/<YYYY>/<MM>/<DD>/<HHMM>/.
  // Each rclone lsjson call against the encrypted gdrive remote takes 1-3s
  // (first call ~30s due to crypto setup). To bound the listing latency
  // for the UI, walk only the most recent year → month → day → leaf
  // branches, capped at MAX_LEAVES total. Older days / hours are not
  // enumerated; the on-disk script (recovery.sh → gdrive-tiered-upload)
  // prunes aggressively so most users only have the last ~30 leaves on
  // gdrive anyway.
  const MAX_MONTHS_PER_YEAR = 3; // newest first
  const MAX_DAYS_PER_MONTH = 7;
  const MAX_HOURS_PER_DAY = 6;
  const MAX_LEAVES = 80;

  // The plugin worker is spawned by the paperclip server, which sets
  // very few env vars. process.env.HOME is often empty, so we can't use
  // it to find ~/.config/rclone/rclone-pass. The pass-read loop above
  // already tries multiple locations; just proceed to the listing walk.

  async function lsjsonDir(remotePath: string): Promise<Array<{ Path: string; Name: string; Size: number; IsDir: boolean; ModTime?: string }>> {
    const child = spawn(
      "rclone",
      ["lsjson", "--dirs-only", "--no-modtime", remotePath],
      {
        env: {
          ...process.env,
          RCLONE_CONFIG: cfg.rcloneConfig,
          ...(pass ? { RCLONE_CONFIG_PASS: pass } : {}),
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (b) => (stdout += b.toString()));
    child.stderr.on("data", (b) => (stderr += b.toString()));
    const code: number = await new Promise((res) => child.on("exit", (c) => res(c ?? 0)));
    if (code !== 0) return [];
    const out: Array<{ Path: string; Name: string; Size: number; IsDir: boolean; ModTime?: string }> = [];
    for (const line of stdout.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const obj = JSON.parse(trimmed) as { Path?: string; Name?: string; Size?: number; IsDir?: boolean; ModTime?: string };
        if (!obj.Path) continue;
        out.push({
          Path: obj.Path,
          Name: obj.Name ?? obj.Path.split("/").pop() ?? obj.Path,
          Size: obj.Size ?? 0,
          IsDir: !!obj.IsDir,
          ModTime: obj.ModTime,
        });
      } catch {
        /* skip */
      }
    }
    return out;
  }

  // Newest first (alphabetical sort matches YYYY > MM > DD > HHMM)
  function newestFirst<T extends { Path: string }>(arr: T[]): T[] {
    return arr.slice().sort((a, b) => (a.Path < b.Path ? 1 : a.Path > b.Path ? -1 : 0));
  }

  const backups: OffsiteBackup[] = [];
  const years = newestFirst(await lsjsonDir(`${remote}:${prefix}/`));
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
  for (const y of years) {
    if (backups.length >= MAX_LEAVES) break;
    if (!y.IsDir) continue;
    const monthsRaw = newestFirst(await lsjsonDir(`${remote}:${prefix}/${y.Path}/`)).slice(0, MAX_MONTHS_PER_YEAR);
    const monthPaths = monthsRaw.filter((m) => m.IsDir).map((m) => ({ y: y.Path, m }));
    const dayLists = await runWithCap(monthPaths, PARALLEL, async ({ y, m }) =>
      newestFirst(await lsjsonDir(`${remote}:${prefix}/${y}/${m.Path}/`)).slice(0, MAX_DAYS_PER_MONTH),
    );
    const dayPaths: Array<{ y: string; m: string; d: typeof dayLists[0][0] }> = [];
    for (let i = 0; i < dayLists.length; i += 1) {
      for (const d of dayLists[i] ?? []) {
        if (d.IsDir) dayPaths.push({ y: monthPaths[i].y, m: monthPaths[i].m.Path, d });
      }
    }
    const hourLists = await runWithCap(dayPaths, PARALLEL, async ({ y, m, d }) =>
      newestFirst(await lsjsonDir(`${remote}:${prefix}/${y}/${m}/${d.Path}/`)).slice(0, MAX_HOURS_PER_DAY),
    );
    for (let i = 0; i < hourLists.length; i += 1) {
      if (backups.length >= MAX_LEAVES) break;
      for (const h of hourLists[i] ?? []) {
        if (backups.length >= MAX_LEAVES) break;
        if (!h.IsDir) continue;
        if (!/^\d{4}$/.test(h.Name ?? h.Path)) continue;
        const fullPath = `${dayPaths[i].y}/${dayPaths[i].m}/${dayPaths[i].d.Path}/${h.Name ?? h.Path}`;
        backups.push({
          path: `${prefix}/${fullPath}`,
          modified: h.ModTime,
          sizeBytes: h.Size ?? 0,
        });
      }
    }
  }
  return { remote: `${remote}:${prefix}`, prefix, backups };
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
    // Data providers
    // ---------------------------------------------------------------------
    ctx.data.register(DATA_KEYS.config, async () => {
      return readInstanceConfig();
    });

    ctx.data.register(DATA_KEYS.listing, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const companyId = (p.companyId as string) || "default";
      const cfg = readInstanceConfig();
      const cached = listingCache.get(companyId);
      if (cached && Date.now() - cached.at < LISTING_TTL_MS) {
        return cached.listing;
      }
      const resolved = resolveLocalBackupDir(cfg);
      // Local read is fast (~50ms). The offsite walk against the encrypted
      // gdrive takes 30s+ on the first call (crypto setup). To keep the UI
      // responsive we run the offsite walk ASYNCHRONOUSLY: read local now,
      // return immediately with a "loading" marker for offsite. The first
      // call returns the local listing + an empty/loading offsite listing;
      // the offsite walk continues in the background and the next call
      // sees the populated cache.
      const localDumps = await readLocalDumps(resolved.dir);
      const localBytes = localDumps.reduce((s, d) => s + d.sizeBytes, 0);
      const placeholderOffsite = {
        remote: `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`,
        prefix: `Paperclip-Backups/${companyId}`,
        backups: [],
        count: 0,
        totalBytes: 0,
        loading: true,
      };
      const listing = {
        local: {
          dir: resolved.dir,
          dirSource: resolved.source,
          dumps: localDumps,
          count: localDumps.length,
          totalBytes: localBytes,
        },
        offsite: placeholderOffsite,
        retention: {
          keep: cfg.defaultKeep,
          candidates: Math.max(0, localDumps.length - cfg.defaultKeep),
        },
        offsiteRetention: {
          keep: cfg.offsiteKeep,
          candidates: 0,
          totalBytes: 0,
        },
        config: cfg,
        loading: false,
        requestedCompanyId: companyId,
        listingAt: Date.now(),
        listingFresh: false,
      };
      // Mark as refreshing in the cache so the next call doesn't
      // re-fire while the background walk is in flight.
      listingCache.set(companyId, {
        at: Date.now(),
        listing,
        refreshing: true,
      });
      // Fire the offsite walk in the background. Use void (not await)
      // so the RPC returns immediately.
      void (async () => {
        try {
          const offsite = await readOffsiteBackups(cfg, companyId);
          const offsiteBytes = offsite.backups.reduce((s, b) => s + b.sizeBytes, 0);
          listingCache.set(companyId, {
            at: Date.now(),
            listing: {
              ...listing,
              offsite: { ...offsite, loading: false },
              offsiteRetention: {
                keep: cfg.offsiteKeep,
                candidates: Math.max(0, offsite.backups.length - cfg.offsiteKeep),
                totalBytes: offsiteBytes,
              },
              listingFresh: true,
            },
            refreshing: false,
          });
        } catch (err) {
          ctx.logger.warn(
            `paperclip-backup: offsite listing walk failed: companyId=${companyId} err=${err instanceof Error ? err.message : String(err)}`,
          );
          listingCache.set(companyId, {
            at: Date.now(),
            listing: {
              ...listing,
              offsite: {
                ...placeholderOffsite,
                loading: false,
                _error: err instanceof Error ? err.message : String(err),
              },
              listingFresh: true,
            },
            refreshing: false,
          });
        }
      })();
      return listing;
    });

    ctx.data.register(DATA_KEYS.status, async () => {
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
      return {
        backupLastRun: lastRun,
        backupRunning: running,
        offsiteLastRun: offsiteLast,
        offsiteRunning,
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
          child.on("exit", (c) => res(c)),
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
    ctx.actions.register(
      RECOVERY_ACTION_KEYS.uploadDailyBackup,
      async () => {
        const scriptPath =
          (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
          "/home/sirrus/paperclip-btcaaaaa-main/scripts/gdrive-tiered-upload.sh";
        if (!existsSync(scriptPath)) {
          return { ok: false, message: `tiered upload script not found: ${scriptPath}` };
        }
        const child = spawn(scriptPath, ["upload-daily"], {
          detached: true,
          stdio: "ignore",
        });
        child.unref();
        return {
          ok: true,
          pid: child.pid,
          async: true,
          message: `Daily upload started (pid=${child.pid})`,
        };
      },
    );

    ctx.actions.register(
      RECOVERY_ACTION_KEYS.uploadHourlyBackup,
      async () => {
        const scriptPath =
          (process.env.PAPERCLIP_GDRIVE_TIERED_SCRIPT as string) ||
          "/home/sirrus/paperclip-btcaaaaa-main/scripts/gdrive-tiered-upload.sh";
        if (!existsSync(scriptPath)) {
          return { ok: false, message: `tiered upload script not found: ${scriptPath}` };
        }
        const child = spawn(scriptPath, ["upload-hourly"], {
          detached: true,
          stdio: "ignore",
        });
        child.unref();
        return {
          ok: true,
          pid: child.pid,
          async: true,
          message: `Hourly upload started (pid=${child.pid})`,
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
            .sort((a: { id: string }, b: { id: string }) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0));
        } catch {
          return [];
        }
      };
      const [dailyItems, hourlyItems] = await Promise.all([
        listTier("daily"),
        listTier("hourly"),
      ]);
      return {
        daily: { keep: dailyKeep, count: dailyItems.length, items: dailyItems },
        hourly: { keep: hourlyKeep, count: hourlyItems.length, items: hourlyItems },
      };
    });

    // ---------------------------------------------------------------------
    // Scheduled job: auto-prune offsite backups
    // ---------------------------------------------------------------------
    ctx.jobs.register(JOB_KEYS.autoPruneOffsite, async () => {
      const cfg = readInstanceConfig();
      const keep = cfg.offsiteKeep;
      if (!keep || keep <= 0) {
        // job handlers must return void
        return;
      }
      const companyId = process.env.PAPERCLIP_COMPANY_ID;
      if (!companyId) {
        ctx.logger.warn("auto-prune-offsite: PAPERCLIP_COMPANY_ID not set");
        return;
      }
      await runScript(cfg.backupScript, [companyId, "--prune-offsite"], {
        PAPERCLIP_COMPANY_ID: companyId,
      });
    });

    // ---------------------------------------------------------------------
    // Scheduled job: auto offsite backup (DB + worktree) every 2h
    // ---------------------------------------------------------------------
    ctx.jobs.register(JOB_KEYS.autoOffsiteBackup, async () => {
      const cfg = readInstanceConfig();
      const companyId = resolveCompanyId(undefined);
      if (!cfg.worktreeBackupEnabled) return;
      // 1) DB dump upload
      const main = await runScript(cfg.backupScript, [companyId], {
        PAPERCLIP_COMPANY_ID: companyId,
      });
      if (!main.ok) {
        ctx.logger.warn(`auto-offsite-backup: main backup failed: ${main.message}`);
        return;
      }
      // 2) Worktree snapshot upload (same gdrive prefix; prune-offsite
      //    trims them together under the configured retention count).
      if (cfg.worktreeBackupScript && existsSync(cfg.worktreeBackupScript)) {
        const wt = await runScript(cfg.worktreeBackupScript, [], {
          PAPERCLIP_COMPANY_ID: companyId,
        });
        if (!wt.ok) {
          ctx.logger.warn(`auto-offsite-backup: worktree backup failed: ${wt.message}`);
        }
      }
    });
  },
});

// Allow running the worker directly via `node ./dist/worker.js` for
// development.
export default pluginInstance;
if (process.argv[1] && process.argv[1].endsWith("worker.js")) {
  runWorker(pluginInstance, import.meta.url);
}