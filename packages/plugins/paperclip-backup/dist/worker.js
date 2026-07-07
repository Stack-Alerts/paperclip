import { spawn } from "node:child_process";
import { existsSync, readFileSync, promises as fs } from "node:fs";
import path from "node:path";
import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";
import { ACTION_KEYS, CONFIG_VERSION, DATA_KEYS, DEFAULT_CONFIG, JOB_KEYS, PLUGIN_ID, STATE_KEYS, } from "./constants.js";
// ---------------------------------------------------------------------------
// Listing cache
//
// The offsite listing makes an `rclone lsjson` call to Google Drive. With a
// full backup history that takes 30-60s, and the dashboard widget polls the
// status endpoint frequently. Without a cache, every poll re-runs rclone.
//
// Strategy: keep the most recent listing per companyId in memory for
// LISTING_TTL_MS. The first poll after startup (or after a TTL miss / cache
// invalidation) kicks a background refresh and returns the previous result
// immediately — so the UI is never blocked on rclone.
//
// Invalidate the cache whenever something might have changed the listing:
// after runBackup / pruneOffsite / pruneLocal / restoreOffsite / restoreLocal
// completes. UI surfaces `listingAt` + `listingFresh` so it can show stale
// data with a "Refresh" affordance rather than re-mounting on every poll.
// ---------------------------------------------------------------------------
const LISTING_TTL_MS = 30_000;
const listingCache = new Map();
function emptyListingPlaceholder(companyId) {
    return {
        local: { dir: null, dumps: [], count: 0, totalBytes: 0 },
        offsite: { remote: null, prefix: null, backups: [], count: 0 },
        retention: { keep: 0, candidates: 0 },
        offsiteRetention: { keep: 0, candidates: 0, totalBytes: 0 },
        config: null,
        loading: true,
        requestedCompanyId: companyId,
    };
}
async function refreshListingInBackground(companyId, cfg, ctx) {
    const existing = listingCache.get(companyId);
    if (existing?.refreshing)
        return;
    listingCache.set(companyId, { at: existing?.at ?? 0, listing: existing?.listing ?? emptyListingPlaceholder(companyId), refreshing: true });
    try {
        const listing = await loadListing(companyId, cfg);
        listingCache.set(companyId, { at: Date.now(), listing, refreshing: false });
        ctx?.logger?.info?.(`listing-cache: refreshed company=${companyId} local=${listing.local.count} offsite=${listing.offsite.count}`);
    }
    catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        listingCache.set(companyId, {
            at: existing?.at ?? 0,
            listing: existing?.listing ?? emptyListingPlaceholder(companyId),
            refreshing: false,
            lastError: message,
        });
        ctx?.logger?.error?.(`listing-cache: refresh failed company=${companyId}: ${message}`);
    }
}
function getCachedListing(companyId, cfg, ctx, { force = false } = {}) {
    const now = Date.now();
    const cached = listingCache.get(companyId);
    if (force) {
        refreshListingInBackground(companyId, cfg, ctx);
        return {
            listing: cached?.listing ?? emptyListingPlaceholder(companyId),
            fresh: false,
            loading: !cached,
            at: cached?.at ?? 0,
        };
    }
    if (cached && now - cached.at < LISTING_TTL_MS && !cached.refreshing) {
        return { listing: cached.listing, fresh: true, loading: false, at: cached.at };
    }
    // Stale or missing — kick a background refresh and return whatever we have.
    refreshListingInBackground(companyId, cfg, ctx);
    return {
        listing: cached?.listing ?? emptyListingPlaceholder(companyId),
        fresh: false,
        loading: !cached,
        at: cached?.at ?? 0,
    };
}
function invalidateListingCache(companyId) {
    if (companyId === null || companyId === undefined) {
        listingCache.clear();
        return;
    }
    listingCache.delete(companyId);
}
function readEnvConfig() {
    const envOverride = (() => {
        try {
            const o = process.env.PAPERCLIP_BACKUP_CONFIG;
            if (!o)
                return null;
            return JSON.parse(o);
        }
        catch {
            return null;
        }
    })();
    return {
        paperclipHome: DEFAULT_CONFIG.paperclipHome,
        backupScript: DEFAULT_CONFIG.backupScript,
        restoreScript: DEFAULT_CONFIG.restoreScript,
        pruneScript: DEFAULT_CONFIG.pruneScript,
        rcloneConfig: DEFAULT_CONFIG.rcloneConfig,
        rcloneRemote: DEFAULT_CONFIG.rcloneRemote,
        defaultKeep: DEFAULT_CONFIG.defaultKeep,
        backupsSubdir: DEFAULT_CONFIG.backupsSubdir,
        offsiteKeep: DEFAULT_CONFIG.offsiteKeep,
        offsiteSchedule: DEFAULT_CONFIG.offsiteSchedule,
        ...(envOverride ?? {}),
    };
}
function mergeConfig(base, override) {
    return { ...base, ...override };
}
function resolveCompanyId(params, fallback = "") {
    const fromParams = params && typeof params.companyId === "string" ? params.companyId.trim() : "";
    if (fromParams)
        return fromParams;
    const fromEnv = process.env.PAPERCLIP_COMPANY_ID ?? "";
    if (fromEnv.trim().length > 0)
        return fromEnv.trim();
    return fallback;
}
async function listLocalDumps(dir) {
    try {
        const names = await fs.readdir(dir);
        const matches = names
            .filter((n) => n.startsWith("paperclip-") && n.endsWith(".sql.gz"))
            .sort();
        const dumps = [];
        for (const name of matches) {
            const full = path.join(dir, name);
            const stat = await fs.stat(full);
            dumps.push({ filename: name, sizeBytes: stat.size, mtime: stat.mtime.toISOString() });
        }
        return dumps.reverse();
    }
    catch {
        return [];
    }
}
function resolveRcloneBinary() {
    const candidates = [
        "/usr/bin/rclone",
        "/usr/local/bin/rclone",
        `${resolveHome()}/.local/bin/rclone`,
        "/home/sirrus/.local/bin/rclone",
        "/root/.local/bin/rclone",
    ];
    for (const c of candidates) {
        try {
            if (existsSync(c))
                return c;
        }
        catch {
            /* ignore */
        }
    }
    return null;
}
/**
 * Resolve the user's HOME even when the worker process has HOME stripped
 * from its env (paperclip's plugin-worker-manager only forwards a small
 * allowlist). Defaults to `/home/<uid-name>` via /etc/passwd lookup, then
 * `/root`, then `/home/sirrus` (the operator's known location).
 */
function resolveHome() {
    if (process.env.HOME && process.env.HOME.length > 0)
        return process.env.HOME;
    try {
        const uid = process.getuid?.();
        if (typeof uid === "number") {
            const passwd = require("node:fs").readFileSync("/etc/passwd", "utf-8");
            const m = new RegExp(`^([^:]+):[^:]+:${uid}:[0-9]+:([^:]*):([^:]+):[^:]+$`, "m").exec(passwd);
            if (m && m[3] && m[3].length > 0)
                return m[3];
        }
    }
    catch {
        /* ignore */
    }
    return "/home/sirrus";
}
/**
 * Build the env to pass when spawning rclone. Reads the rclone password
 * (if available) and exports RCLONE_CONFIG_PASS so rclone can decrypt an
 * encrypted rclone config without prompting on stdin. The backup scripts
 * already do this via _rclone_pass.sh; we mirror the same logic here so
 * the plugin can read & prune offsite backups directly.
 */
let cachedRcloneEnv = null;
function rcloneSpawnEnv(rcloneConfig) {
    if (cachedRcloneEnv && cachedRcloneEnv.__config === rcloneConfig) {
        return cachedRcloneEnv;
    }
    const env = { ...process.env };
    delete env.__config;
    const home = resolveHome();
    env.HOME = home;
    const passFile = process.env.RCLONE_PASS_FILE ?? `${home}/.config/rclone/rclone-pass`;
    try {
        if (existsSync(passFile)) {
            const pass = readFileSync(passFile, "utf-8").trim();
            if (pass.length > 0)
                env.RCLONE_CONFIG_PASS = pass;
        }
    }
    catch {
        /* ignore: plaintext config or unreadable */
    }
    env.RCLONE_CONFIG = rcloneConfig;
    const tagged = { ...env, __config: rcloneConfig };
    cachedRcloneEnv = tagged;
    return cachedRcloneEnv;
}
async function listOffsiteBackups(remoteBase, rcloneConfig) {
    return new Promise((resolve) => {
        const rclone = resolveRcloneBinary();
        if (!rclone)
            return resolve([]);
        const proc = spawn(rclone, [
            "lsjson",
            "--dirs-only",
            "--max-depth",
            "5",
            "--config",
            rcloneConfig,
            remoteBase,
        ], { stdio: ["ignore", "pipe", "pipe"], env: rcloneSpawnEnv(rcloneConfig) });
        let out = "";
        let err = "";
        proc.stdout?.on("data", (c) => {
            out += c.toString();
        });
        proc.stderr?.on("data", (c) => {
            err += c.toString();
        });
        proc.on("close", (code) => {
            if (code !== 0) {
                try {
                    process.stderr.write(`[${PLUGIN_ID}] rclone lsjson exited ${code}: ${err}\n`);
                }
                catch {
                    /* ignore */
                }
                return resolve([]);
            }
            try {
                const items = JSON.parse(out || "[]");
                resolve(items
                    .filter((it) => /^\d{4}\/\d{2}\/\d{2}\/\d{4}$/.test(it.Path))
                    .map((it) => ({
                    path: it.Path,
                    modified: it.ModTime ?? new Date().toISOString(),
                    sizeBytes: typeof it.Size === "number" ? it.Size : null,
                }))
                    .sort((a, b) => b.modified.localeCompare(a.modified)));
            }
            catch {
                resolve([]);
            }
        });
    });
}
async function runScript(script, args, env = {}) {
    if (!existsSync(script)) {
        return { ok: false, exitCode: null, message: `Script not found: ${script}` };
    }
    const start = Date.now();
    return new Promise((resolve) => {
        const proc = spawn(script, args, {
            stdio: ["ignore", "pipe", "pipe"],
            env: { ...process.env, ...env },
        });
        let stdout = "";
        let stderr = "";
        proc.stdout?.on("data", (c) => {
            stdout += c.toString();
        });
        proc.stderr?.on("data", (c) => {
            stderr += c.toString();
        });
        proc.on("error", (err) => {
            resolve({
                ok: false,
                exitCode: null,
                message: `spawn error: ${err.message}`,
                stderr: String(err),
                durationMs: Date.now() - start,
            });
        });
        proc.on("close", (code) => {
            resolve({
                ok: code === 0,
                exitCode: code,
                stdout: stdout.slice(0, 16000),
                stderr: stderr.slice(0, 16000),
                durationMs: Date.now() - start,
            });
        });
    });
}
function localDumpsDir(cfg) {
    return path.join(cfg.paperclipHome, cfg.backupsSubdir);
}
async function loadListing(companyId, cfg) {
    const dir = localDumpsDir(cfg);
    const dumps = await listLocalDumps(dir);
    const totalBytes = dumps.reduce((s, d) => s + d.sizeBytes, 0);
    const offsiteBase = `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`;
    const offsite = await listOffsiteBackups(offsiteBase, cfg.rcloneConfig);
    const keep = cfg.defaultKeep;
    const candidates = Math.max(0, dumps.length - keep);
    const offsiteKeep = cfg.offsiteKeep;
    const offsiteCandidates = Math.max(0, offsite.length - offsiteKeep);
    const offsiteTotalBytes = offsite.reduce((s, b) => s + (typeof b.sizeBytes === "number" ? b.sizeBytes : 0), 0);
    return {
        local: { dir, dumps, count: dumps.length, totalBytes },
        offsite: { remote: cfg.rcloneRemote, prefix: offsiteBase, backups: offsite, count: offsite.length },
        retention: { keep, candidates },
        offsiteRetention: {
            keep: offsiteKeep,
            candidates: offsiteCandidates,
            totalBytes: offsiteTotalBytes,
        },
        config: cfg,
    };
}
// ---------------------------------------------------------------------------
// Offsite pruning
// ---------------------------------------------------------------------------
/**
 * Parse a simple schedule string used by the offsite auto-prune.
 *
 * Accepts:
 *   "every Nh" — every N hours (N integer, 1-8760)
 *   "every Nd" — every N days   (N integer, 1-365)
 *   ""         — disabled
 *
 * Returns the interval in milliseconds, or null when the input is empty /
 * invalid / explicitly disabled.
 */
function parseScheduleMs(value) {
    if (!value)
        return null;
    const trimmed = value.trim().toLowerCase();
    if (!trimmed || trimmed === "off" || trimmed === "disabled" || trimmed === "never")
        return null;
    const m = /^every\s+(\d+)\s*([hd])$/.exec(trimmed);
    if (!m)
        return null;
    const n = Number(m[1]);
    if (!Number.isFinite(n) || n <= 0)
        return null;
    if (m[2] === "h") {
        if (n > 24 * 365)
            return null;
        return n * 60 * 60 * 1000;
    }
    if (n > 365)
        return null;
    return n * 24 * 60 * 60 * 1000;
}
/**
 * Delete the oldest offsite backups beyond `keep` count.
 *
 * Returns a per-folder deletion result. Uses `rclone rmdir` for each
 * candidate (empty dated folders) and falls back to `rclone purge` if the
 * folder is non-empty (the backup script writes files inside it).
 */
async function pruneOffsite(cfg, companyId, keep, ctx) {
    const start = Date.now();
    const remoteBase = `${cfg.rcloneRemote}:Paperclip-Backups/${companyId}`;
    const all = await listOffsiteBackups(remoteBase, cfg.rcloneConfig);
    // Sort ASCENDING by modified date so the first N to delete are the oldest.
    const ascending = [...all].sort((a, b) => a.modified.localeCompare(b.modified));
    const totalBytesBefore = ascending.reduce((s, b) => s + (typeof b.sizeBytes === "number" ? b.sizeBytes : 0), 0);
    const safeKeep = Math.max(0, Math.min(10000, Math.floor(keep)));
    const toDelete = ascending.slice(0, Math.max(0, ascending.length - safeKeep));
    const kept = ascending.length - toDelete.length;
    if (toDelete.length === 0) {
        return {
            ok: true,
            totalBefore: ascending.length,
            totalAfter: kept,
            kept,
            pruned: 0,
            totalBytesBefore,
            totalBytesAfter: totalBytesBefore,
            deletedPaths: [],
            message: `Nothing to prune — already at or below keep=${safeKeep}.`,
        };
    }
    const rclone = resolveRcloneBinary();
    const deletedPaths = [];
    let deletedBytes = 0;
    for (const candidate of toDelete) {
        const target = `${remoteBase}/${candidate.path}`;
        // Try rmdir first (works if backup was already empty after restore);
        // fall back to purge if there are files inside.
        let ok = await runRclone(rclone, [
            "rmdir",
            "--config",
            cfg.rcloneConfig,
            target,
        ]);
        if (!ok) {
            ok = await runRclone(rclone, [
                "purge",
                "--config",
                cfg.rcloneConfig,
                target,
            ]);
        }
        if (ok) {
            deletedPaths.push(candidate.path);
            deletedBytes += typeof candidate.sizeBytes === "number" ? candidate.sizeBytes : 0;
            ctx.logger.info(`prune-offsite: deleted ${candidate.path}`);
        }
        else {
            ctx.logger.warn(`prune-offsite: failed to delete ${candidate.path}`);
        }
    }
    const after = await listOffsiteBackups(remoteBase, cfg.rcloneConfig);
    const totalBytesAfter = after.reduce((s, b) => s + (typeof b.sizeBytes === "number" ? b.sizeBytes : 0), 0);
    return {
        ok: deletedPaths.length === toDelete.length,
        totalBefore: ascending.length,
        totalAfter: after.length,
        kept,
        pruned: deletedPaths.length,
        totalBytesBefore,
        totalBytesAfter,
        deletedPaths,
        message: `Pruned ${deletedPaths.length}/${toDelete.length} offsite backups in ${Date.now() - start}ms (kept newest ${safeKeep}).`,
    };
}
async function runRclone(rclone, args) {
    if (!rclone)
        return false;
    // Extract --config from args so we know which config to use to look up
    // the matching password env. rclone config path is the only thing we cache on.
    const configIdx = args.indexOf("--config");
    const rcloneConfig = configIdx >= 0 && configIdx + 1 < args.length ? args[configIdx + 1] : "";
    return new Promise((resolve) => {
        const proc = spawn(rclone, args, {
            stdio: ["ignore", "pipe", "pipe"],
            env: rcloneSpawnEnv(rcloneConfig),
        });
        proc.on("error", () => resolve(false));
        proc.on("close", (code) => resolve(code === 0));
    });
}
function asString(value, fallback) {
    return typeof value === "string" && value.length > 0 ? value : fallback;
}
function asNumber(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
}
/**
 * Best-effort check whether a process is still running. Uses `kill(pid, 0)`
 * which returns 0 if the process exists (and we have permission to signal
 * it) and ESRCH if it doesn't. We swallow EPERM (different user, but
 * process still exists).
 */
function isPidAlive(pid) {
    if (!Number.isInteger(pid) || pid <= 0)
        return false;
    try {
        process.kill(pid, 0);
        return true;
    }
    catch (err) {
        const code = err?.code;
        if (code === "EPERM")
            return true;
        return false;
    }
}
const plugin = definePlugin({
    capabilities: [
        "ui.dashboardWidget.register",
        "ui.sidebar.register",
        "ui.page.register",
        "plugin.state.read",
        "plugin.state.write",
        "instance.settings.register",
    ],
    async setup(ctx) {
        ctx.logger.info(`${PLUGIN_ID} v${CONFIG_VERSION} starting`);
        const baseConfig = readEnvConfig();
        // Persist initial config so operators can edit it from the settings page.
        const existing = await ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.config })
            .catch(() => null);
        if (!existing) {
            await ctx.state
                .set({ scopeKind: "instance", stateKey: STATE_KEYS.config }, baseConfig)
                .catch(() => null);
        }
        const existingRetention = await ctx.state
            .get({ scopeKind: "instance", stateKey: STATE_KEYS.retention })
            .catch(() => null);
        if (!existingRetention) {
            await ctx.state
                .set({ scopeKind: "instance", stateKey: STATE_KEYS.retention }, { defaultKeep: baseConfig.defaultKeep, offsiteKeep: baseConfig.offsiteKeep })
                .catch(() => null);
        }
        async function resolveConfig() {
            const [persistedCfg, persistedRetention] = await Promise.all([
                ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.config }).catch(() => null),
                ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.retention }).catch(() => null),
            ]);
            const merged = mergeConfig(baseConfig, (persistedCfg && typeof persistedCfg === "object" ? persistedCfg : {}));
            const retention = persistedRetention && typeof persistedRetention === "object"
                ? persistedRetention
                : null;
            if (retention?.defaultKeep && Number.isFinite(retention.defaultKeep)) {
                merged.defaultKeep = Math.max(1, Math.min(365, Math.floor(retention.defaultKeep)));
            }
            if (retention?.offsiteKeep && Number.isFinite(retention.offsiteKeep)) {
                merged.offsiteKeep = Math.max(0, Math.min(10000, Math.floor(retention.offsiteKeep)));
            }
            // offsiteSchedule is part of persistedCfg; ensure it's a string.
            if (typeof merged.offsiteSchedule !== "string")
                merged.offsiteSchedule = "";
            return merged;
        }
        // ---- Data: config (instance-level settings page form values) ----
        ctx.data.register(DATA_KEYS.config, async () => {
            const cfg = await resolveConfig();
            return cfg;
        });
        // ---- Data: listing (everything the manager page needs) ----
        ctx.data.register(DATA_KEYS.listing, async (params) => {
            const companyId = resolveCompanyId(params);
            const cfg = await resolveConfig();
            if (!companyId) {
                return {
                    local: { dir: "", dumps: [], count: 0, totalBytes: 0 },
                    offsite: { remote: "", prefix: "", backups: [], count: 0 },
                    retention: { keep: 0, candidates: 0 },
                    config: cfg,
                    missingCompanyId: true,
                };
            }
            // Listing data: honor explicit force=true refresh; otherwise serve
            // from cache and refresh in the background.
            const force = params?.force === true;
            const { listing, fresh, loading, at } = getCachedListing(companyId, cfg, ctx, { force });
            return { ...listing, config: cfg, _meta: { fresh, loading, at: at || null, forcedRefresh: force } };
        });
        // ---- Data: status (lightweight summary for the dashboard widget) ----
        ctx.data.register(DATA_KEYS.status, async (params) => {
            const companyId = resolveCompanyId(params);
            const cfg = await resolveConfig();
            const [running, lastRun, offsiteRunning, offsiteLastRun] = await Promise.all([
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
                    .catch(() => null),
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupLastRun })
                    .catch(() => null),
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning })
                    .catch(() => null),
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun })
                    .catch(() => null),
            ]);
            // Self-heal stale "running" markers whose pid is gone.
            let runningState = null;
            if (running &&
                typeof running === "object" &&
                running.pid) {
                const pid = running.pid;
                if (isPidAlive(pid)) {
                    runningState = running;
                }
                else {
                    // Stale marker — pid is gone; clear it so the UI doesn't show
                    // a phantom "running" backup.
                    ctx.state
                        .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning }, null)
                        .catch(() => null);
                }
            }
            if (!companyId) {
                return {
                    local: { count: 0, totalBytes: 0, newest: null },
                    offsite: { count: 0, newest: null },
                    retention: { keep: cfg.defaultKeep, candidates: 0 },
                    missingCompanyId: true,
                    backupRunning: runningState,
                    backupLastRun: lastRun && typeof lastRun === "object"
                        ? lastRun
                        : null,
                    offsiteRunning: offsiteRunning && typeof offsiteRunning === "object"
                        ? offsiteRunning
                        : null,
                    offsiteLastRun: offsiteLastRun && typeof offsiteLastRun === "object"
                        ? offsiteLastRun
                        : null,
                    listingFresh: false,
                    listingLoading: false,
                    listingAt: null,
                };
            }
            // Use the cached listing (kick background refresh on miss); never
            // block the status poll on rclone.
            const { listing, fresh: listingFresh, loading: listingLoading, at: listingAt } = getCachedListing(companyId, cfg, ctx);
            return {
                local: {
                    count: listing.local.count,
                    totalBytes: listing.local.totalBytes,
                    newest: listing.local.dumps[0] ?? null,
                },
                offsite: {
                    count: listing.offsite.count,
                    newest: listing.offsite.backups[0] ?? null,
                },
                retention: listing.retention,
                backupRunning: runningState,
                backupLastRun: lastRun && typeof lastRun === "object"
                    ? lastRun
                    : null,
                offsiteRunning: offsiteRunning && typeof offsiteRunning === "object"
                    ? offsiteRunning
                    : null,
                offsiteLastRun: offsiteLastRun && typeof offsiteLastRun === "object"
                    ? offsiteLastRun
                    : null,
                listingFresh,
                listingLoading,
                listingAt: listingAt || null,
            };
        });
        // ---- Action: run backup (detached — RPC must return <30s) ----
        //
        // The backup script uploads ~1.5 GiB to GDrive and routinely takes
        // 30-40 minutes. The plugin RPC channel has a 30s default timeout, so
        // we can't await the script. Spawn it detached, persist its PID +
        // start time to state, and return immediately. The UI watches the
        // `backup-running` / `backup-last-run` state keys via `usePluginData`
        // to surface progress, and `usePluginData("status")` will pick up
        // changes to the instance directory (newest dump) once it finishes.
        ctx.actions.register(ACTION_KEYS.runBackup, async (params) => {
            const companyId = resolveCompanyId(params);
            const cfg = await resolveConfig();
            if (!companyId) {
                return { ok: false, exitCode: null, message: "No companyId in context or PAPERCLIP_COMPANY_ID env" };
            }
            // Refuse to start a second backup while one is already running.
            const existing = await ctx.state
                .get({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning })
                .catch(() => null);
            if (existing &&
                typeof existing === "object" &&
                existing.pid &&
                isPidAlive(existing.pid)) {
                return {
                    ok: false,
                    exitCode: null,
                    message: `Backup already running (pid=${existing.pid}, started ${existing.startedAt ?? "?"})`,
                    alreadyRunning: true,
                    pid: existing.pid,
                    startedAt: existing.startedAt,
                };
            }
            if (!existsSync(cfg.backupScript)) {
                return { ok: false, exitCode: null, message: `Script not found: ${cfg.backupScript}` };
            }
            const startedAt = new Date().toISOString();
            // Detached spawn: the script writes its own stdout/stderr to its
            // log file (paperclip-backup.log under backup-state). The parent
            // returns immediately and the OS reaps the child when it exits.
            const child = spawn(cfg.backupScript, [], {
                detached: true,
                stdio: "ignore",
                env: { ...process.env, PAPERCLIP_COMPANY_ID: companyId },
            });
            child.unref();
            await ctx.state
                .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning }, {
                pid: child.pid,
                startedAt,
                script: cfg.backupScript,
                companyId,
            })
                .catch(() => null);
            // When the script eventually exits (minutes later), record the
            // result and clear the running marker so the next action can start.
            child.on("exit", (code, signal) => {
                const finishedAt = new Date().toISOString();
                const ok = code === 0;
                // Read the script's last-result.json (if any) to surface message.
                const resultFile = `${cfg.paperclipHome}/instances/default/backup-state/last-result.json`;
                let message = ok ? "Backup pushed to offsite" : "Backup script failed";
                try {
                    if (existsSync(resultFile)) {
                        const j = JSON.parse(readFileSync(resultFile, "utf-8"));
                        if (j.result === "skipped_no_change") {
                            message = "No changes — skipped (signature unchanged)";
                        }
                        else if (j.result === "ok" && j.destination) {
                            message = `Pushed to ${j.destination}`;
                        }
                        else if (j.result) {
                            message = `Result: ${j.result}`;
                        }
                    }
                }
                catch {
                    /* ignore */
                }
                ctx.state
                    .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupLastRun }, {
                    pid: child.pid,
                    startedAt,
                    finishedAt,
                    exitCode: code,
                    signal,
                    ok,
                    message,
                })
                    .catch(() => null);
                ctx.state
                    .set({ scopeKind: "instance", stateKey: STATE_KEYS.backupRunning }, null)
                    .catch(() => null);
                ctx.logger.info(`backup: detached script exited pid=${child.pid} code=${code} signal=${signal} ok=${ok} msg=${message}`);
                invalidateListingCache(companyId);
            });
            return {
                ok: true,
                exitCode: 0,
                message: `Backup started in background (pid=${child.pid})`,
                pid: child.pid,
                startedAt,
                async: true,
            };
        });
        // ---- Action: prune local dumps ----
        ctx.actions.register(ACTION_KEYS.pruneLocal, async (params) => {
            const cfg = await resolveConfig();
            const keep = Math.max(1, Math.min(365, asNumber(params?.keep, cfg.defaultKeep)));
            const dir = localDumpsDir(cfg);
            const before = await listLocalDumps(dir);
            const totalBytesBefore = before.reduce((s, d) => s + d.sizeBytes, 0);
            const r = await runScript(cfg.pruneScript, [], {
                BACKUP_RETENTION_KEEP: String(keep),
            });
            const after = await listLocalDumps(dir);
            const totalBytesAfter = after.reduce((s, d) => s + d.sizeBytes, 0);
            // Local dumps are shared across companies — clear every cached listing.
            invalidateListingCache(null);
            return {
                ...r,
                keep,
                totalBytesBefore,
                totalBytesAfter,
                prunedCount: Math.max(0, before.length - after.length),
                message: r.ok ? `Pruned, kept newest ${keep} file(s)` : "Prune script failed",
            };
        });
        // ---- Action: restore from offsite (calls existing script) ----
        ctx.actions.register(ACTION_KEYS.restoreOffsite, async (params) => {
            const companyId = resolveCompanyId(params);
            if (!companyId) {
                return { ok: false, exitCode: null, message: "No companyId in context or PAPERCLIP_COMPANY_ID env" };
            }
            const cfg = await resolveConfig();
            const remotePath = typeof params?.path === "string" && params.path.length > 0 && params.path !== "latest"
                ? params.path
                : "latest";
            const destDir = asString(params?.destDir, "/tmp/paperclip-restore");
            const r = await runScript(cfg.restoreScript, [remotePath, destDir], {
                PAPERCLIP_COMPANY_ID: companyId,
            });
            invalidateListingCache(companyId);
            return {
                ...r,
                source: "offsite",
                remotePath,
                destDir,
                message: r.ok ? `Restored ${remotePath} → ${destDir}` : "Restore script failed",
            };
        });
        // ---- Action: prune offsite backups (delete oldest beyond keep count) ----
        //
        // Detached: each rclone rmdir/purge against GDrive takes 5-15s, and a
        // typical prune of N>>keep runs serially past the 30s RPC timeout.
        // Mirror the runBackup pattern: persist a "running" state, kick the
        // work into setImmediate, return immediately with async:true. The UI
        // reads `offsiteRunning` + `offsiteLastRun` via usePluginData("status")
        // to show progress and the eventual result.
        ctx.actions.register(ACTION_KEYS.pruneOffsite, async (params) => {
            const companyId = resolveCompanyId(params);
            if (!companyId) {
                return { ok: false, exitCode: null, message: "No companyId in context or PAPERCLIP_COMPANY_ID env" };
            }
            const cfg = await resolveConfig();
            const requestedKeep = asNumber(params?.keep, cfg.offsiteKeep);
            const keep = Math.max(0, Math.min(10000, Math.floor(requestedKeep)));
            const force = params?.force === true;
            // Refuse to start a second prune while one is already running,
            // unless:
            //   (a) force:true was passed (user explicitly wants to override), or
            //   (b) the existing "running" marker is stale (offsiteLastRun.startedAt
            //       is >= the running marker's startedAt — meaning the run actually
            //       completed but a prior state.delete() silently failed), or
            //   (c) the running marker is older than STALE_RUNNING_MS (defensive
            //       self-heal in case the worker was killed mid-prune and never
            //       got to clean up).
            const STALE_RUNNING_MS = 5 * 60 * 1000;
            const [existing, lastRun] = await Promise.all([
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning })
                    .catch(() => null),
                ctx.state
                    .get({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun })
                    .catch(() => null),
            ]);
            let staleReason = null;
            if (existing &&
                typeof existing === "object" &&
                existing.startedAt) {
                const runningStartedAt = Date.parse(existing.startedAt);
                const runningAgeMs = Date.now() - runningStartedAt;
                const completedAfterStart = lastRun &&
                    typeof lastRun === "object" &&
                    typeof lastRun.startedAt === "string" &&
                    Date.parse(lastRun.startedAt) >= runningStartedAt;
                if (runningAgeMs > STALE_RUNNING_MS) {
                    staleReason = `running marker is ${Math.round(runningAgeMs / 1000)}s old (>5min)`;
                }
                else if (completedAfterStart) {
                    staleReason = "offsiteLastRun.startedAt >= offsiteRunning.startedAt (run completed but marker was not cleared)";
                }
            }
            if (existing &&
                typeof existing === "object" &&
                existing.startedAt &&
                !staleReason &&
                !force) {
                const elapsedMs = Date.now() - Date.parse(existing.startedAt);
                return {
                    ok: false,
                    exitCode: null,
                    alreadyRunning: true,
                    message: `Offsite prune already running (started ${existing.startedAt}, keep=${existing.keep}, elapsed=${Math.round(elapsedMs / 1000)}s)`,
                    startedAt: existing.startedAt,
                    keep: existing.keep,
                    elapsedMs,
                    forceHint: "Pass force:true to override.",
                };
            }
            if (staleReason) {
                ctx.logger.warn(`prune-offsite: clearing stale running marker (${staleReason}) and proceeding${force ? " (force=true)" : ""}`);
                try {
                    await ctx.state.delete({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning });
                }
                catch (err) {
                    ctx.logger.error(`prune-offsite: failed to clear stale running marker: ${err?.message ?? err}`);
                }
            }
            const startedAt = new Date().toISOString();
            await ctx.state
                .set({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteRunning }, {
                startedAt,
                keep,
                companyId,
            })
                .catch(() => null);
            // Detach: do the actual rclone work after we return so the RPC
            // can complete in <1s. Any thrown error is captured into state
            // so the UI surfaces it via offsiteLastRun.
            setImmediate(() => {
                (async () => {
                    const finishedAt = new Date().toISOString();
                    try {
                        const result = await pruneOffsite(cfg, companyId, keep, ctx);
                        await ctx.state
                            .set({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun }, {
                            at: finishedAt,
                            startedAt,
                            durationMs: Date.now() - new Date(startedAt).getTime(),
                            keep,
                            pruned: result.pruned,
                            totalBefore: result.totalBefore,
                            totalAfter: result.totalAfter,
                            totalBytesBefore: result.totalBytesBefore,
                            totalBytesAfter: result.totalBytesAfter,
                            deletedPaths: result.deletedPaths,
                            ok: result.ok,
                            message: result.message,
                        })
                            .catch((err) => ctx.logger.error(`prune-offsite: failed to persist offsiteLastRun: ${err?.message ?? err}`));
                        ctx.logger.info(`prune-offsite: detached run finished pruned=${result.pruned} kept=${result.kept} ok=${result.ok}`);
                        invalidateListingCache(companyId);
                    }
                    catch (err) {
                        const message = err instanceof Error ? err.message : String(err);
                        ctx.logger.error(`prune-offsite: detached run failed: ${message}`);
                        await ctx.state
                            .set({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun }, {
                            at: finishedAt,
                            startedAt,
                            durationMs: Date.now() - new Date(startedAt).getTime(),
                            keep,
                            pruned: 0,
                            ok: false,
                            error: message,
                            message: `Prune failed: ${message}`,
                        })
                            .catch((err) => ctx.logger.error(`prune-offsite: failed to persist offsiteLastRun on error path: ${err?.message ?? err}`));
                    }
                    finally {
                        try {
                            // Use state.delete (not set(key, null)) so the row is
                            // removed entirely — keeps the UI status truthful.
                            await ctx.state.delete({
                                scopeKind: "instance",
                                stateKey: STATE_KEYS.offsiteRunning,
                            });
                            ctx.logger.info(`prune-offsite: cleared offsiteRunning state`);
                        }
                        catch (err) {
                            ctx.logger.error(`prune-offsite: failed to clear offsiteRunning state: ${err?.message ?? err}`);
                        }
                    }
                })();
            });
            return {
                ok: true,
                async: true,
                exitCode: 0,
                message: `Prune started in background (keep=${keep})`,
                startedAt,
                keep,
                companyId,
            };
        });
        // ---- Action: restore from local dump ----
        ctx.actions.register(ACTION_KEYS.restoreLocal, async (params) => {
            const cfg = await resolveConfig();
            const filename = asString(params?.filename, "");
            if (!filename) {
                return { ok: false, exitCode: null, message: "filename is required" };
            }
            const dumpPath = path.join(localDumpsDir(cfg), filename);
            if (!existsSync(dumpPath)) {
                return { ok: false, exitCode: null, message: `Local dump not found: ${dumpPath}` };
            }
            const destDir = asString(params?.destDir, "/tmp/paperclip-restore");
            await fs.mkdir(destDir, { recursive: true });
            const target = path.join(destDir, filename);
            const start = Date.now();
            await fs.copyFile(dumpPath, target);
            // Restore doesn't change the listing, but it consumes a dump file
            // in some retention schemes — keep the cache honest.
            invalidateListingCache(null);
            return {
                ok: true,
                exitCode: 0,
                source: "local",
                destDir,
                stdout: `Copied ${dumpPath} → ${target}`,
                message: `Copied ${filename} to ${destDir}`,
                durationMs: Date.now() - start,
            };
        });
        // ---- Action: save config (used by the settings page) ----
        ctx.actions.register(ACTION_KEYS.saveConfig, async (params) => {
            const incoming = params && typeof params === "object" ? params : {};
            const next = mergeConfig(await resolveConfig(), {
                paperclipHome: asString(incoming.paperclipHome, baseConfig.paperclipHome),
                backupScript: asString(incoming.backupScript, baseConfig.backupScript),
                restoreScript: asString(incoming.restoreScript, baseConfig.restoreScript),
                pruneScript: asString(incoming.pruneScript, baseConfig.pruneScript),
                rcloneConfig: asString(incoming.rcloneConfig, baseConfig.rcloneConfig),
                rcloneRemote: asString(incoming.rcloneRemote, baseConfig.rcloneRemote),
                backupsSubdir: asString(incoming.backupsSubdir, baseConfig.backupsSubdir),
                offsiteSchedule: asString(incoming.offsiteSchedule, baseConfig.offsiteSchedule),
            });
            await ctx.state.set({ scopeKind: "instance", stateKey: STATE_KEYS.config }, next);
            const defaultKeep = Math.max(1, Math.min(365, asNumber(incoming.defaultKeep, next.defaultKeep)));
            const offsiteKeep = Math.max(0, Math.min(10000, asNumber(incoming.offsiteKeep, next.offsiteKeep)));
            await ctx.state.set({ scopeKind: "instance", stateKey: STATE_KEYS.retention }, { defaultKeep, offsiteKeep });
            next.defaultKeep = defaultKeep;
            next.offsiteKeep = offsiteKeep;
            return { ok: true, message: "Saved", config: next };
        });
        // ---- Job: auto-prune-offsite (also runnable manually via ctx.jobs) ----
        ctx.jobs.register(JOB_KEYS.autoPruneOffsite, async () => {
            const cfg = await resolveConfig();
            if (!cfg.offsiteSchedule || parseScheduleMs(cfg.offsiteSchedule) == null) {
                ctx.logger.info("auto-prune-offsite: schedule disabled, skipping");
                return;
            }
            const companyId = process.env.PAPERCLIP_COMPANY_ID ?? cfg.paperclipHome;
            // Pick a companyId from somewhere — the host provides one on each job invocation,
            // but we don't have access here. Fall back to listing the offsite prefix and
            // iterating every company folder under Paperclip-Backups/.
            const prefix = `${cfg.rcloneRemote}:Paperclip-Backups`;
            const subdirs = await listOffsiteBackups(prefix, cfg.rcloneConfig);
            const companyIds = subdirs.map((s) => s.path.split("/").pop() ?? "").filter(Boolean);
            if (companyIds.length === 0) {
                ctx.logger.info("auto-prune-offsite: no companies found under " + prefix);
                return;
            }
            let totalPruned = 0;
            for (const cid of companyIds) {
                const result = await pruneOffsite(cfg, cid, cfg.offsiteKeep, ctx);
                totalPruned += result.pruned;
            }
            await ctx.state
                .set({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun }, {
                at: new Date().toISOString(),
                keep: cfg.offsiteKeep,
                pruned: totalPruned,
                ok: true,
                triggeredBy: "schedule",
            })
                .catch(() => null);
            ctx.logger.info(`auto-prune-offsite: pruned ${totalPruned} offsite backups across ${companyIds.length} companies`);
        });
        // ---- In-worker scheduler: poll every minute, fire prune if due ----
        let nextRunAt = null;
        const tick = async () => {
            try {
                const cfg = await resolveConfig();
                const intervalMs = parseScheduleMs(cfg.offsiteSchedule);
                if (intervalMs == null) {
                    nextRunAt = null;
                    return;
                }
                const now = Date.now();
                if (nextRunAt == null) {
                    // On first tick (and after every change), align nextRunAt to
                    // "now + interval" so we always fire within one interval window.
                    nextRunAt = now + intervalMs;
                }
                if (now >= nextRunAt) {
                    nextRunAt = now + intervalMs;
                    ctx.logger.info(`scheduler: firing auto-prune-offsite (interval=${cfg.offsiteSchedule})`);
                    const prefix = `${cfg.rcloneRemote}:Paperclip-Backups`;
                    const subdirs = await listOffsiteBackups(prefix, cfg.rcloneConfig);
                    const companyIds = subdirs.map((s) => s.path.split("/").pop() ?? "").filter(Boolean);
                    let totalPruned = 0;
                    for (const cid of companyIds) {
                        const result = await pruneOffsite(cfg, cid, cfg.offsiteKeep, ctx);
                        totalPruned += result.pruned;
                    }
                    await ctx.state
                        .set({ scopeKind: "instance", stateKey: STATE_KEYS.offsiteLastRun }, {
                        at: new Date().toISOString(),
                        keep: cfg.offsiteKeep,
                        pruned: totalPruned,
                        ok: true,
                        triggeredBy: "schedule",
                        interval: cfg.offsiteSchedule,
                    })
                        .catch(() => null);
                    ctx.logger.info(`scheduler: pruned ${totalPruned} offsite backups`);
                }
            }
            catch (err) {
                ctx.logger.warn(`scheduler tick failed: ${err instanceof Error ? err.message : String(err)}`);
            }
        };
        const handle = setInterval(tick, 60 * 1000);
        // Kick once on startup so a fresh install with non-empty config runs immediately.
        void tick();
        try {
            ctx.events.on("plugin.config.changed", () => {
                nextRunAt = null;
            });
        }
        catch {
            /* events not available; scheduler still works via setInterval */
        }
        // Clean up on shutdown (best effort; the host usually kills the process).
        const cleanup = () => {
            clearInterval(handle);
        };
        process.once("beforeExit", cleanup);
        process.once("SIGTERM", cleanup);
        process.once("SIGINT", cleanup);
    },
    async onHealth() {
        return { status: "ok", plugin: PLUGIN_ID, version: CONFIG_VERSION };
    },
});
export default plugin;
runWorker(plugin, import.meta.url);
//# sourceMappingURL=worker.js.map