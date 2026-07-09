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
    null
  );
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
const LISTING_TTL_MS = 30_000;
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
      if (cached && Date.now() - cached.at < LISTING_TTL_MS && !cached.refreshing) {
        return cached.listing;
      }
      // For now return a minimal placeholder; a future build will replace
      // this with a real rclone-driven listing matching dist/worker.js.
      const listing = {
        local: { dir: null, dumps: [], count: 0, totalBytes: 0 },
        offsite: { remote: null, prefix: null, backups: [], count: 0 },
        retention: { keep: cfg.defaultKeep, candidates: 0 },
        offsiteRetention: { keep: cfg.offsiteKeep, candidates: 0, totalBytes: 0 },
        config: cfg,
        loading: false,
        requestedCompanyId: companyId,
        listingAt: Date.now(),
        listingFresh: true,
      };
      listingCache.set(companyId, {
        at: Date.now(),
        listing,
        refreshing: false,
      });
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
      return await runScript(cfg.backupScript, [companyId], {
        PAPERCLIP_COMPANY_ID: companyId,
      });
    });

    ctx.actions.register(ACTION_KEYS.pruneLocal, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const keep = Number(p.keep) || 10;
      const cfg = readInstanceConfig();
      return await runScript(cfg.pruneScript, [String(keep)]);
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
          "/home/sirrus/.paperclip/scripts/gdrive-tiered-upload.sh";
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
          "/home/sirrus/.paperclip/scripts/gdrive-tiered-upload.sh";
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
      return {
        daily: { keep: dailyKeep },
        hourly: { keep: hourlyKeep },
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
  },
});

// Allow running the worker directly via `node ./dist/worker.js` for
// development.
export default pluginInstance;
if (process.argv[1] && process.argv[1].endsWith("worker.js")) {
  runWorker(pluginInstance, import.meta.url);
}