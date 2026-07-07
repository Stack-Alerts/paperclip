import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";
import {
  ACTION_KEYS,
  DATA_KEYS,
  DEFAULT_CONFIG,
  PLUGIN_ID,
  STREAM_CHANNELS,
  type BlockedChain,
  type ChainNode,
  type GitMergesConfig,
  type MergeBlock,
  type MergeQueueSnapshot,
  type ScanRecord,
  type ScanStatus,
} from "./constants.js";
import { parseMergeQueueOutput, diffBlocks } from "./parser.js";
// Type imports only — referenced via `import("./constants.js").MergeBlock` etc.
// in helper signatures below.
import type {} from "./constants.js";

/**
 * Keys used to store plugin state in the Paperclip instance state store.
 * Persisted across worker restarts so scan history and the current
 * config survive plugin reloads.
 */
const CONFIG_STATE_KEY = "config";
const SCAN_STATE_KEY = "latest-scan";
const HISTORY_STATE_KEY = "scan-history";
const STATUS_STATE_KEY = "scan-status";
const PREVIOUS_BLOCKS_KEY = "previous-blocks";
const PREVIOUS_SCAN_STARTED_AT_KEY = "previous-blocks-started-at";
const ISSUE_MAP_KEY = "issue-map";
const HISTORY_LIMIT = 12;

/**
 * ANSI colour escape sequence regex. The Python script emits colour codes
 * when stdout is a TTY; we strip them so the dashboard output renders
 * cleanly in the browser.
 */
const ANSI_REGEX = /\x1b\[[0-9;]*m/g;

function stripAnsi(value: string): string {
  return value.replace(ANSI_REGEX, "");
}

/**
 * Keep only the last `max` characters of `value` and prepend a marker so
 * the UI can show the user that the buffer was truncated. Used to cap
 * memory usage on scans that print a lot.
 */
function clampOutput(value: string, max: number): string {
  if (value.length <= max) return value;
  const tail = value.slice(value.length - max);
  return `[... truncated to last ${max} characters ...]\n${tail}`;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringRecord(value: unknown): value is Record<string, string> {
  if (!isPlainObject(value)) return false;
  return Object.values(value).every((entry) => typeof entry === "string");
}

function emptyTotals(): import("./constants.js").MergeTotals {
  return {
    inReview: 0,
    openPrs: 0,
    queuedRuns: 0,
    inProgressRuns: 0,
    ready: 0,
    waiting: 0,
    failing: 0,
    noPrOrSha: 0,
  };
}

function isMergeBlocksArray(value: unknown): value is MergeBlock[] {
  if (!Array.isArray(value)) return false;
  return value.every((entry) => {
    if (!isPlainObject(entry)) return false;
    return (
      typeof entry.issueUuid === "string" &&
      typeof entry.title === "string" &&
      typeof entry.diffKey === "string"
    );
  });
}

function mergeBlocksWithIdentifierCache(
  blocks: MergeBlock[] | null,
  cache: Record<string, string>,
): MergeBlock[] {
  if (!blocks) return [];
  return blocks.map((block) => {
    const cached = cache[block.issueUuid];
    if (!cached) return block;
    if (block.issueIdentifier === cached) return block;
    return { ...block, issueIdentifier: cached };
  });
}

/**
 * Resolve the absolute path to the script given the configured repoPath and
 * the (relative) scriptPath. Throws if the script would escape repoPath.
 * This is a defensive check — the operator owns the config but we don't
 * want a typo'd `../../etc/passwd` to silently run something unexpected.
 */
function resolveScriptPath(repoPath: string, scriptPath: string): string {
  const root = path.resolve(repoPath);
  const resolved = path.resolve(root, scriptPath);
  const relative = path.relative(root, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(
      `scriptPath "${scriptPath}" resolves outside repoPath "${repoPath}"`,
    );
  }
  return resolved;
}

/**
 * Build the minimal env passed to the python child process. We do NOT
 * spread process.env — Paperclip gives the plugin worker a curated
 * environment and we shouldn't leak the worker's secrets (or pass
 * unrelated host vars) to the child. The script itself reads .env from
 * repoPath, so Paperclip/GitHub credentials don't need to be in here.
 */
function buildChildEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    PYTHONUNBUFFERED: "1",
    PATH: process.env.PATH ?? "",
    HOME: process.env.HOME ?? "",
    LANG: process.env.LANG ?? "C.UTF-8",
    LC_ALL: process.env.LC_ALL ?? "C.UTF-8",
    TZ: process.env.TZ ?? "UTC",
  };
  return env;
}

/**
 * Resolve the Paperclip identifiers (e.g. `BTCAAAAA-38557`) for a list of
 * issue UUIDs by hitting the Paperclip REST API.
 *
 * Reads `.env` from the configured `repoPath` for `PAPERCLIP_API_KEY`,
 * `PAPERCLIP_API_URL`, and `PAPERCLIP_COMPANY_ID`. Returns a UUID→identifier
 * map for any issues the API successfully resolves. Unresolved UUIDs are
 * omitted from the map so the caller can fall back to the UUID itself.
 *
 * We deliberately make these calls best-effort: if the API is unreachable
 * or the key is missing, we return an empty map and the UI falls back to
 * UUIDs in the issue link. The dashboard still works; just the link
 * destination is the issues-by-uuid route instead of the friendly identifier.
 */
async function fetchIssueIdentifiers(
  repoPath: string,
  uuids: string[],
): Promise<Map<string, string>> {
  if (uuids.length === 0) return new Map();
  const env = loadDotenv(repoPath);
  const apiUrl = (env.PAPERCLIP_API_URL ?? process.env.PAPERCLIP_API_URL ?? "").trim();
  const apiKey = (env.PAPERCLIP_API_KEY ?? process.env.PAPERCLIP_API_KEY ?? "").trim();
  const companyId = (env.PAPERCLIP_COMPANY_ID ?? process.env.PAPERCLIP_COMPANY_ID ?? "").trim();
  if (!apiUrl || !apiKey || !companyId) {
    return new Map();
  }

  const out = new Map<string, string>();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8_000);
  try {
    // Fetch issues in parallel — the API key has rate headroom and most
    // scans have <30 issues. Cap at 8s so a slow API doesn't stall scans.
    const tasks = uuids.map(async (uuid) => {
      try {
        const res = await fetch(
          `${apiUrl.replace(/\/$/, "")}/api/issues/${encodeURIComponent(uuid)}`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${apiKey}`,
              Accept: "application/json",
            },
            signal: controller.signal,
          },
        );
        if (!res.ok) return;
        const body = (await res.json()) as { identifier?: unknown };
        if (typeof body.identifier === "string" && body.identifier.length > 0) {
          out.set(uuid, body.identifier);
        }
      } catch {
        // Per-issue failures are non-fatal — keep going.
      }
    });
    await Promise.allSettled(tasks);
  } finally {
    clearTimeout(timeoutId);
  }
  return out;
}

/**
 * Minimal `.env` loader for the BTC repo. Mirrors the python script's
 * behaviour: only sets vars that aren't already in process.env, handles
 * quoted values, ignores comments and blank lines.
 */
function loadDotenv(repoPath: string): Record<string, string> {
  const out: Record<string, string> = {};
  let raw: string;
  try {
    raw = readFileSync(path.join(repoPath, ".env"), "utf8");
  } catch {
    return out;
  }
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

function coerceConfig(value: unknown): GitMergesConfig {
  const base: GitMergesConfig = { ...DEFAULT_CONFIG };
  if (!isPlainObject(value)) return base;
  const v = value as Record<string, unknown>;
  if (typeof v.pythonPath === "string") base.pythonPath = v.pythonPath;
  if (typeof v.repoPath === "string") base.repoPath = v.repoPath;
  if (typeof v.scriptPath === "string") base.scriptPath = v.scriptPath;
  if (typeof v.autoRefreshEnabled === "boolean")
    base.autoRefreshEnabled = v.autoRefreshEnabled;
  if (typeof v.autoRefreshIntervalSeconds === "number" && Number.isFinite(v.autoRefreshIntervalSeconds))
    base.autoRefreshIntervalSeconds = Math.max(
      30,
      Math.min(86_400, Math.floor(v.autoRefreshIntervalSeconds)),
    );
  if (typeof v.timeBlockEnabled === "boolean")
    base.timeBlockEnabled = v.timeBlockEnabled;
  if (typeof v.timeBlockStartHour === "number" && Number.isFinite(v.timeBlockStartHour))
    base.timeBlockStartHour = Math.max(0, Math.min(23, Math.floor(v.timeBlockStartHour)));
  if (typeof v.timeBlockEndHour === "number" && Number.isFinite(v.timeBlockEndHour))
    base.timeBlockEndHour = Math.max(0, Math.min(23, Math.floor(v.timeBlockEndHour)));
  if (typeof v.showJson === "boolean") base.showJson = v.showJson;
  if (typeof v.maxOutputChars === "number" && Number.isFinite(v.maxOutputChars))
    base.maxOutputChars = Math.max(
      1000,
      Math.min(5_000_000, Math.floor(v.maxOutputChars)),
    );
  if (typeof v.scanTimeoutSeconds === "number" && Number.isFinite(v.scanTimeoutSeconds))
    base.scanTimeoutSeconds = Math.max(
      10,
      Math.min(3600, Math.floor(v.scanTimeoutSeconds)),
    );
  return base;
}

function mergeConfigUpdate(
  current: GitMergesConfig,
  update: unknown,
): GitMergesConfig {
  const incoming = coerceConfig(update);
  return {
    pythonPath: incoming.pythonPath || current.pythonPath,
    repoPath: incoming.repoPath || current.repoPath,
    scriptPath: incoming.scriptPath || current.scriptPath,
    autoRefreshEnabled: incoming.autoRefreshEnabled,
    autoRefreshIntervalSeconds: incoming.autoRefreshIntervalSeconds,
    timeBlockEnabled: incoming.timeBlockEnabled,
    timeBlockStartHour: incoming.timeBlockStartHour,
    timeBlockEndHour: incoming.timeBlockEndHour,
    showJson: incoming.showJson,
    maxOutputChars: incoming.maxOutputChars,
    scanTimeoutSeconds: incoming.scanTimeoutSeconds,
  };
}

function isWithinTimeBlock(now: Date, startHour: number, endHour: number): boolean {
  const hour = now.getHours();
  if (startHour === endHour) return false;
  if (startHour < endHour) {
    return hour >= startHour && hour < endHour;
  }
  // Wraps midnight (e.g. 22 -> 6).
  return hour >= startHour || hour < endHour;
}

function makeBlankStatus(): ScanStatus {
  return {
    running: false,
    lastRunAt: null,
    lastAttemptAt: null,
    lastExitCode: null,
    lastSkipped: false,
  };
}

function isScanRecord(value: unknown): value is ScanRecord {
  if (!isPlainObject(value)) return false;
  return (
    typeof value.startedAt === "string" &&
    (value.finishedAt === null || typeof value.finishedAt === "string") &&
    (value.exitCode === null || typeof value.exitCode === "number") &&
    typeof value.stdout === "string" &&
    typeof value.stderr === "string"
  );
}

function coerceStatus(value: unknown): ScanStatus {
  const base = makeBlankStatus();
  if (!isPlainObject(value)) return base;
  if (typeof value.running === "boolean") base.running = value.running;
  if (typeof value.lastRunAt === "string") base.lastRunAt = value.lastRunAt;
  if (typeof value.lastAttemptAt === "string") base.lastAttemptAt = value.lastAttemptAt;
  if (typeof value.lastExitCode === "number") base.lastExitCode = value.lastExitCode;
  if (typeof value.lastSkipped === "boolean") base.lastSkipped = value.lastSkipped;
  return base;
}

function coerceHistory(value: unknown): ScanRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isScanRecord);
}

/**
 * Build a uuid → { chainId, node } lookup so the Awaiting Approval tab
 * can quickly show "this approval unblocks N issues in chain-X" without
 * walking every chain. Empty if there are no chains.
 */
function buildApprovalChainLookup(
  chains: BlockedChain[],
): Record<string, { chainId: string; node: ChainNode }> {
  const out: Record<string, { chainId: string; node: ChainNode }> = {};
  for (const chain of chains) {
    for (const [uuid, node] of Object.entries(chain.nodes)) {
      out[uuid] = { chainId: chain.id, node };
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Plugin definition
// ---------------------------------------------------------------------------

const plugin = definePlugin({
  async setup(ctx) {
    ctx.logger.info(`${PLUGIN_ID} plugin setup complete`);

    // Always (re)write the persisted config from the host's current config so
    // any operator edits via the Git Merges Settings page are picked up
    // after a worker restart. Falls back to defaults on the very first run.
    const hostConfig = await ctx.config.get().catch(() => null);
    const merged = mergeConfigUpdate(
      { ...DEFAULT_CONFIG },
      hostConfig ?? {},
    );
    await ctx.state.set(
      { scopeKind: "instance", stateKey: CONFIG_STATE_KEY },
      merged,
    );
    if (
      (await ctx.state.get({ scopeKind: "instance", stateKey: STATUS_STATE_KEY })) ==
      null
    ) {
      await ctx.state.set(
        { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
        makeBlankStatus(),
      );
    }

    // ---- Data: config --------------------------------------------------
    ctx.data.register(DATA_KEYS.config, async () => {
      const value = await ctx.state.get({
        scopeKind: "instance",
        stateKey: CONFIG_STATE_KEY,
      });
      return coerceConfig(value);
    });

    // ---- Data: status --------------------------------------------------
    ctx.data.register(DATA_KEYS.status, async () => {
      const value = await ctx.state.get({
        scopeKind: "instance",
        stateKey: STATUS_STATE_KEY,
      });
      return coerceStatus(value);
    });

    // ---- Data: snapshot (config + status + latest + history + blocks) ---
    ctx.data.register(DATA_KEYS.snapshot, async () => {
      const [
        configValue,
        latestValue,
        historyValue,
        statusValue,
        previousBlocksValue,
        previousStartedAtValue,
        issueMapValue,
      ] = await Promise.all([
        ctx.state.get({ scopeKind: "instance", stateKey: CONFIG_STATE_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: SCAN_STATE_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: HISTORY_STATE_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: STATUS_STATE_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: PREVIOUS_BLOCKS_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: PREVIOUS_SCAN_STARTED_AT_KEY }),
        ctx.state.get({ scopeKind: "instance", stateKey: ISSUE_MAP_KEY }),
      ]);
      const config = coerceConfig(configValue);
      const rawStatus = coerceStatus(statusValue);
      // Safety net for stale `running: true` from a worker that crashed
      // mid-scan before the try/finally could reset the flag. If the
      // flag has been true for more than `scanTimeoutSeconds * 2`, treat
      // it as a leaked running flag and clear it. The UI would otherwise
      // show the indeterminate "Loading…" bar indefinitely until the
      // next successful scan finally overwrites it.
      const RUNNING_LEAK_TIMEOUT_MS = Math.max(
        30_000,
        config.scanTimeoutSeconds * 2 * 1000,
      );
      let status = rawStatus;
      if (rawStatus.running) {
        const startedAtMs = rawStatus.lastAttemptAt
          ? new Date(rawStatus.lastAttemptAt).getTime()
          : 0;
        const ageMs = startedAtMs > 0 ? Date.now() - startedAtMs : 0;
        if (ageMs > RUNNING_LEAK_TIMEOUT_MS) {
          // Best-effort self-heal. We don't await this write because
          // we're already inside a data handler that should respond
          // quickly; the next scan will overwrite status anyway.
          void ctx.state
            .set(
              { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
              { ...rawStatus, running: false },
            )
            .catch((err) => {
              ctx.logger.warn("Git Merges: leaked running flag self-heal failed", {
                error:
                  err instanceof Error ? err.message : String(err),
              });
            });
          status = { ...rawStatus, running: false };
        }
      }
      const latest = isScanRecord(latestValue) ? latestValue : null;
      const history = coerceHistory(historyValue);
      const previousBlocks = isMergeBlocksArray(previousBlocksValue)
        ? previousBlocksValue
        : null;
      const cachedMap = isStringRecord(issueMapValue) ? issueMapValue : {};
      const blocks = mergeBlocksWithIdentifierCache(latest?.blocks ?? null, cachedMap);
      const totals = latest?.totals ?? emptyTotals();
      const previousStartedAt =
        typeof previousStartedAtValue === "string" &&
        previousStartedAtValue.length > 0
          ? previousStartedAtValue
          : null;
      return {
        config,
        status,
        latest,
        history,
        blocks,
        previousBlocks,
        previousStartedAt,
        totals,
        latestStartedAt: latest?.startedAt ?? null,
        latestFinishedAt: latest?.finishedAt ?? null,
        blockedChains: latest?.blockedChains ?? [],
        approvalRequests: latest?.approvalRequests ?? [],
        approvalChainLookup: buildApprovalChainLookup(latest?.blockedChains ?? []),
        blockedCount: latest?.blockedCount ?? 0,
        chainCount: latest?.chainCount ?? 0,
        approvalCount: latest?.approvalCount ?? 0,
      };
    });

    // ---- Actions ------------------------------------------------------
    ctx.actions.register(ACTION_KEYS.runScan, async (params) => {
      const configValue = await ctx.state.get({
        scopeKind: "instance",
        stateKey: CONFIG_STATE_KEY,
      });
      const config = coerceConfig(configValue);
      const force = params?.force === true;
      const result = await runMergeScan(ctx, config, {
        trigger: "manual",
        force,
      });
      return { ok: result !== null, skipped: result?.skipped ?? false };
    });

    ctx.actions.register(ACTION_KEYS.clearOutput, async () => {
      // Reset history to an empty array (legal JSON) and delete the latest-scan
      // row entirely. Setting `value_json` to `null` is rejected because the
      // column is `NOT NULL`; deleting leaves the row absent and `get` returns
      // null, which is the same shape we use elsewhere.
      await ctx.state.set(
        { scopeKind: "instance", stateKey: HISTORY_STATE_KEY },
        [],
      );
      await ctx.state.delete({
        scopeKind: "instance",
        stateKey: SCAN_STATE_KEY,
      });
      const status = coerceStatus(
        await ctx.state.get({
          scopeKind: "instance",
          stateKey: STATUS_STATE_KEY,
        }),
      );
      status.lastRunAt = null;
      status.lastExitCode = null;
      status.lastSkipped = false;
      await ctx.state.set(
        { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
        status,
      );
      ctx.logger.info("Git Merges: cleared output buffer");
      return { ok: true };
    });

    ctx.actions.register(ACTION_KEYS.saveConfig, async (params) => {
      const current = coerceConfig(
        await ctx.state.get({
          scopeKind: "instance",
          stateKey: CONFIG_STATE_KEY,
        }),
      );
      const next = mergeConfigUpdate(current, params);
      await ctx.state.set(
        { scopeKind: "instance", stateKey: CONFIG_STATE_KEY },
        next,
      );
      ctx.logger.info("Git Merges: saved config", {
        autoRefresh: next.autoRefreshEnabled,
        intervalSeconds: next.autoRefreshIntervalSeconds,
      });
      return { ok: true, config: next };
    });

    // ---- Scheduled auto-scan job --------------------------------------
    // The manifest declares `*/5 * * * *` as the worst-case interval. Inside
    // the handler we re-check the user-configured interval and time-block,
    // so the actual cadence can be 30 s, 5 min, or anything in between
    // without redeploying.
    ctx.jobs.register("git-merges-auto-scan", async () => {
      const configValue = await ctx.state.get({
        scopeKind: "instance",
        stateKey: CONFIG_STATE_KEY,
      });
      const config = coerceConfig(configValue);

      if (!config.autoRefreshEnabled) return;
      const now = new Date();
      if (
        config.timeBlockEnabled &&
        !isWithinTimeBlock(now, config.timeBlockStartHour, config.timeBlockEndHour)
      ) {
        await recordAttempt(ctx, { skipped: true, skipReason: "outside time block" });
        return;
      }

      const statusValue = await ctx.state.get({
        scopeKind: "instance",
        stateKey: STATUS_STATE_KEY,
      });
      const status = coerceStatus(statusValue);
      if (status.running) return; // Skip if a scan is already running.

      const lastAttemptAt = status.lastAttemptAt
        ? new Date(status.lastAttemptAt).getTime()
        : 0;
      const elapsedSec = (now.getTime() - lastAttemptAt) / 1000;
      if (lastAttemptAt > 0 && elapsedSec < config.autoRefreshIntervalSeconds) {
        return; // Too soon for the user-configured interval.
      }

      await runMergeScan(ctx, config, { trigger: "auto", force: false });
    });
  },

  async onHealth() {
    return { status: "ok", pluginId: PLUGIN_ID };
  },

  // Note: we intentionally do not implement onConfigChanged. The host restarts
  // the worker on config save, and the new worker picks up the fresh config
  // from the host in setup() (initialConfig in workerOptions). This is the
  // recommended pattern — onConfigChanged does not receive the plugin ctx, so
  // implementing it without state.merge() support is brittle.
});

// ---------------------------------------------------------------------------
// Scan execution
// ---------------------------------------------------------------------------

type ScanTrigger = "manual" | "auto";

async function recordAttempt(
  ctx: Parameters<NonNullable<Parameters<typeof definePlugin>[0]["setup"]>>[0],
  info: { skipped?: boolean; skipReason?: string } = {},
): Promise<void> {
  const status = coerceStatus(
    await ctx.state.get({
      scopeKind: "instance",
      stateKey: STATUS_STATE_KEY,
    }),
  );
  status.lastAttemptAt = new Date().toISOString();
  if (info.skipped) {
    status.lastSkipped = true;
  } else {
    status.lastSkipped = false;
  }
  await ctx.state.set(
    { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
    status,
  );
}

async function runMergeScan(
  ctx: Parameters<NonNullable<Parameters<typeof definePlugin>[0]["setup"]>>[0],
  config: GitMergesConfig,
  opts: { trigger: ScanTrigger; force: boolean },
): Promise<{ skipped: boolean } | null> {
  // Skip if a scan is already running, unless forced (manual always wins).
  const statusValue = await ctx.state.get({
    scopeKind: "instance",
    stateKey: STATUS_STATE_KEY,
  });
  const status = coerceStatus(statusValue);
  if (status.running && !opts.force) {
    ctx.logger.info("Git Merges: scan already running; skipping");
    return null;
  }

  // Capture the startedAt BEFORE setting running: true so the finally
  // block can record the start time on its forced reset even if the
  // scan crashes before reaching the happy-path final-write below.
  const scanStartedAt = new Date().toISOString();
  status.running = true;
  status.lastAttemptAt = scanStartedAt;
  status.lastSkipped = false;
  await ctx.state.set(
    { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
    status,
  );

  // CRITICAL: every code path from here to the bottom MUST reach the
  // happy-path final write, otherwise `running` stays true forever
  // and the UI shows the indeterminate "Loading…" bar indefinitely.
  // We guarantee the flag is reset by wrapping the entire scan body
  // in try/finally. If anything throws (DB error, parse failure,
  // hot-reload crash, etc.) the finally still flips `running` to
  // false and records the failure timestamp.
  let scanError: string | null = null;
  try {
    return await executeScan(ctx, config, opts, scanStartedAt);
  } catch (err) {
    scanError = err instanceof Error ? err.message : String(err);
    ctx.logger.error("Git Merges: scan crashed", {
      error: scanError,
      trigger: opts.trigger,
      durationMs: Date.now() - new Date(scanStartedAt).getTime(),
    });
    return { skipped: false };
  } finally {
    // Always reset the running flag, even if executeScan threw or the
    // worker was hot-reloaded mid-scan. This is the single source of
    // truth for `running: false` — the happy-path final write also
    // sets it, but a duplicated write here is idempotent and safe.
    try {
      const currentStatus = coerceStatus(
        await ctx.state.get({
          scopeKind: "instance",
          stateKey: STATUS_STATE_KEY,
        }),
      );
      const finalStatus: ScanStatus = {
        running: false,
        lastRunAt: scanError ? scanStartedAt : currentStatus.lastRunAt,
        lastAttemptAt: scanStartedAt,
        lastExitCode: scanError ? null : currentStatus.lastExitCode,
        lastSkipped: scanError ? false : currentStatus.lastSkipped,
      };
      await ctx.state.set(
        { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
        finalStatus,
      );
    } catch (cleanupErr) {
      // Last-resort: if even the cleanup write fails, log loudly so
      // an operator can manually reset the flag.
      ctx.logger.error("Git Merges: failed to reset running flag", {
        error:
          cleanupErr instanceof Error ? cleanupErr.message : String(cleanupErr),
      });
    }
  }
}

async function executeScan(
  ctx: Parameters<NonNullable<Parameters<typeof definePlugin>[0]["setup"]>>[0],
  config: GitMergesConfig,
  opts: { trigger: ScanTrigger; force: boolean },
  scanStartedAt: string,
): Promise<{ skipped: boolean } | null> {
  ctx.streams.emit(STREAM_CHANNELS.output, {
    kind: "scan-start",
    startedAt: scanStartedAt,
    trigger: opts.trigger,
  });

  // Save the previous scan's parsed blocks before we run the script.
  // We do this at the START (not the end) because the data handler polls
  // the snapshot every 1.5s while a scan is running; reading latest at
  // the start guarantees we snapshot what the user actually saw right
  // before kicking off the next scan, regardless of any concurrent
  // writes that happen during the script's runtime.
  const previousRaw = await ctx.state.get({ scopeKind: "instance", stateKey: SCAN_STATE_KEY });
  const previousScanRecord = isScanRecord(previousRaw) ? (previousRaw as ScanRecord) : null;
  if (previousScanRecord?.blocks && previousScanRecord.blocks.length > 0) {
    await ctx.state.set(
      { scopeKind: "instance", stateKey: PREVIOUS_BLOCKS_KEY },
      previousScanRecord.blocks,
    );
    // Persist the previous scan's startedAt so the UI can compute
    // elapsed time per block without a separate scan-history read.
    if (previousScanRecord.startedAt) {
      await ctx.state.set(
        { scopeKind: "instance", stateKey: PREVIOUS_SCAN_STARTED_AT_KEY },
        previousScanRecord.startedAt,
      );
    }
  }

  const startedAt = new Date().toISOString();
  let scriptPath: string;
  try {
    scriptPath = resolveScriptPath(config.repoPath, config.scriptPath);
  } catch (err) {
    // The configured scriptPath escapes the configured repoPath. Don't
    // even attempt to spawn — surface the config error as a synthetic
    // failed scan so the UI can render it instead of silently hanging.
    const message = err instanceof Error ? err.message : String(err);
    const record: ScanRecord = {
      startedAt,
      finishedAt: new Date().toISOString(),
      exitCode: null,
      stdout: "",
      stderr: `scriptPath validation failed: ${message}`,
    };
    await ctx.state.set(
      { scopeKind: "instance", stateKey: SCAN_STATE_KEY },
      record,
    );
    const previousHistory = coerceHistory(
      await ctx.state.get({
        scopeKind: "instance",
        stateKey: HISTORY_STATE_KEY,
      }),
    );
    await ctx.state.set(
      { scopeKind: "instance", stateKey: HISTORY_STATE_KEY },
      [record, ...previousHistory].slice(0, HISTORY_LIMIT),
    );
    const nextStatus: ScanStatus = {
      running: false,
      lastRunAt: record.finishedAt,
      lastAttemptAt: record.finishedAt,
      lastExitCode: null,
      lastSkipped: false,
    };
    await ctx.state.set(
      { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
      nextStatus,
    );
    ctx.streams.emit(STREAM_CHANNELS.output, {
      kind: "scan-finish",
      finishedAt: record.finishedAt!,
      exitCode: null,
      spawnError: message,
    });
    ctx.logger.warn("Git Merges: scriptPath validation failed", { error: message });
    return { skipped: false };
  }
  // Always request --json output. The plugin parses the structured JSON
  // payload to extract blocked chains + approval requests, which the
  // human-readable table does not carry. The `showJson` config flag is
  // preserved as a no-op so existing user settings don't surface an
  // unknown-field validation error.
  const args = ["--json", "--quiet"];

  let stdout = "";
  let stderr = "";
  let exitCode: number | null = null;
  let timedOut = false;
  let spawnError: string | null = null;

  // Throttled partial-state writer. The UI polls `git-merges-snapshot`
  // every ~1.5s while a scan is running; this writer keeps the snapshot's
  // `latest` field in lockstep so the polling UI sees incremental output
  // instead of nothing-until-completion.
  const PARTIAL_WRITE_INTERVAL_MS = 500;
  let lastPartialWriteAt = 0;
  let partialWriteInFlight: Promise<void> | null = null;

  function buildPartialRecord(finished: boolean): ScanRecord {
    return {
      startedAt,
      finishedAt: finished ? new Date().toISOString() : null,
      exitCode: finished ? exitCode : null,
      stdout: clampOutput(stdout, config.maxOutputChars),
      stderr: clampOutput(stderr, Math.floor(config.maxOutputChars / 4)),
    };
  }

  async function persistPartial(finished: boolean): Promise<void> {
    const now = Date.now();
    if (!finished && now - lastPartialWriteAt < PARTIAL_WRITE_INTERVAL_MS) {
      return;
    }
    lastPartialWriteAt = now;
    if (partialWriteInFlight) {
      try {
        await partialWriteInFlight;
      } catch {
        // best-effort
      }
    }
    const record = buildPartialRecord(finished);
    partialWriteInFlight = ctx.state
      .set({ scopeKind: "instance", stateKey: SCAN_STATE_KEY }, record)
      .finally(() => {
        partialWriteInFlight = null;
      });
    return partialWriteInFlight;
  }

  await new Promise<void>((resolve) => {
    let child;
    try {
      child = spawn(config.pythonPath, [scriptPath, ...args], {
        cwd: config.repoPath,
        stdio: ["ignore", "pipe", "pipe"],
        env: buildChildEnv(),
      });
    } catch (err) {
      spawnError = err instanceof Error ? err.message : String(err);
      resolve();
      return;
    }

    const timeoutMs = config.scanTimeoutSeconds * 1000;
    const timer = setTimeout(() => {
      timedOut = true;
      try {
        child.kill("SIGKILL");
      } catch {
        // ignore
      }
    }, timeoutMs);

    child.stdout?.on("data", (chunk: Buffer | string) => {
      const text = stripAnsi(String(chunk));
      stdout += text;
      stdout = clampOutput(stdout, config.maxOutputChars);
      ctx.streams.emit(STREAM_CHANNELS.output, {
        kind: "stdout-chunk",
        chunk: text,
      });
      // Fire-and-forget: the throttled writer will debounce these calls.
      void persistPartial(false);
    });
    child.stderr?.on("data", (chunk: Buffer | string) => {
      const text = stripAnsi(String(chunk));
      stderr += text;
      stderr = clampOutput(stderr, Math.floor(config.maxOutputChars / 4));
      ctx.streams.emit(STREAM_CHANNELS.output, {
        kind: "stderr-chunk",
        chunk: text,
      });
      void persistPartial(false);
    });
    child.on("error", (err) => {
      spawnError = err.message;
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      exitCode = code;
      resolve();
    });
  });

  const finishedAt = new Date().toISOString();

  // Build the final record first so all attached fields (stderr, blocks,
  // totals) end up in one persistent object.
  const record = buildPartialRecord(true);

  if (spawnError) {
    record.stderr =
      (record.stderr ? record.stderr + "\n" : "") +
      `spawn error: ${spawnError}`;
  }
  if (timedOut) {
    record.stderr =
      (record.stderr ? record.stderr + "\n" : "") +
      `scan timed out after ${config.scanTimeoutSeconds}s`;
  }

  // Parse the captured stdout into structured blocks + totals. Even on a
  // non-zero exit code we still try to parse — partial output is useful
  // (and `--quiet` errors are typically printed to stderr, not stdout).
  // The parsed `blocks` and `totals` are attached to the record before
  // the final write below so they're included in the persisted snapshot.
  const parsed = parseMergeQueueOutput(record.stdout);

  // Resolve Paperclip identifiers (BTCAAAAA-N) for each issue UUID via the
  // REST API. Best-effort: the UI falls back to UUID if the lookup fails.
  if (parsed.blocks.length > 0) {
    try {
      const identifiers = await fetchIssueIdentifiers(
        config.repoPath,
        parsed.blocks.map((block) => block.issueUuid),
      );
      if (identifiers.size > 0) {
        // Merge the new mappings with whatever we already cached so we
        // don't lose identifiers for issues that left the queue.
        const previousMap = isStringRecord(
          await ctx.state.get({
            scopeKind: "instance",
            stateKey: ISSUE_MAP_KEY,
          }),
        )
          ? (await ctx.state.get({
              scopeKind: "instance",
              stateKey: ISSUE_MAP_KEY,
            })) as Record<string, string>
          : {};
        const merged: Record<string, string> = { ...previousMap };
        for (const [uuid, identifier] of identifiers) {
          merged[uuid] = identifier;
        }
        await ctx.state.set(
          { scopeKind: "instance", stateKey: ISSUE_MAP_KEY },
          merged,
        );
        for (const block of parsed.blocks) {
          const identifier = identifiers.get(block.issueUuid);
          if (identifier) {
            block.issueIdentifier = identifier;
          } else if (merged[block.issueUuid]) {
            block.issueIdentifier = merged[block.issueUuid];
          }
        }
      }
    } catch (err) {
      ctx.logger.warn("Git Merges: identifier lookup failed", {
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // Attach parsed structure to the record so future scans can read it
  // for diffs, and so the UI's `latest` payload has everything it needs.
  record.blocks = parsed.blocks;
  record.totals = parsed.totals;
  record.blockedChains = parsed.blockedChains;
  record.approvalRequests = parsed.approvalRequests;
  record.blockedCount = parsed.blockedCount;
  record.chainCount = parsed.chainCount;
  record.approvalCount = parsed.approvalCount;

  // Final write directly (NOT via persistPartial, which would build a
  // fresh object and drop the blocks/totals we just attached).
  await ctx.state.set(
    { scopeKind: "instance", stateKey: SCAN_STATE_KEY },
    record,
  );

  const previousHistory = coerceHistory(
    await ctx.state.get({
      scopeKind: "instance", stateKey: HISTORY_STATE_KEY,
    }),
  );
  const nextHistory = [record, ...previousHistory].slice(0, HISTORY_LIMIT);
  await ctx.state.set(
    { scopeKind: "instance", stateKey: HISTORY_STATE_KEY },
    nextHistory,
  );

  const nextStatus: ScanStatus = {
    running: false,
    lastRunAt: finishedAt,
    lastAttemptAt: finishedAt,
    lastExitCode: exitCode,
    lastSkipped: false,
  };
  await ctx.state.set(
    { scopeKind: "instance", stateKey: STATUS_STATE_KEY },
    nextStatus,
  );

  ctx.streams.emit(STREAM_CHANNELS.output, {
    kind: "scan-finish",
    finishedAt,
    exitCode,
    timedOut,
    spawnError,
  });

  ctx.logger.info("Git Merges: scan finished", {
    exitCode,
    durationMs: new Date(finishedAt).getTime() - new Date(startedAt).getTime(),
    trigger: opts.trigger,
    timedOut,
    spawnError,
  });

  return { skipped: false };
}

export default plugin;
runWorker(plugin, import.meta.url);
