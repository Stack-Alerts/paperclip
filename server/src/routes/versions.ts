import { Router } from "express";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { eq, ne } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { plugins } from "@paperclipai/db";
import { logger } from "../middleware/logger.js";
import { serverVersion } from "../version.js";

/**
 * versionsRoutes — read-only endpoint exposing the BTC version-control
 * surface area:
 *
 *   GET /api/versions
 *     -> {
 *          btcPaperclip: { version: "1.0.0.0", source: "..." },
 *          paperclip:   { version: "0.3.1",   source: "..." },
 *          plugins: {
 *            "Backup Plugin": { version: "1.0.0.0", source: "..." },
 *            "Git Merges":    { version: "1.0.0.0", source: "..." }
 *          },
 *          generatedAt: "2026-07-15T..."
 *        }
 *
 * Source-of-truth ordering per plugin:
 *   1. <package_path>/VERSION           (BTC-pinned, written by
 *                                        scripts/bump-version.sh)
 *   2. <package_path>/package.json#version (fallback if VERSION is missing)
 *   3. plugins.version (DB)              (last-resort fallback for npm installs)
 *
 * Endpoint is intentionally read-only and unauthenticated (like
 * /api/health) so the top-bar badge can poll it cheaply.
 *
 * Surface filter: only the plugins listed in `SURFACED_PLUGIN_KEYS` are
 * returned in the response. Everything else (npm-installed upstream
 * plugins, disabled plugins, plugin keys we don't own) is omitted. The
 * top-bar badge is the only consumer; keeping the list short matches the
 * operator-facing display contract (BTC-Paperclip + Paperclip + Backup
 * Plugin + Git Merges).
 */

type VersionEntry = {
  version: string;
  source: string;
};

type VersionsResponse = {
  btcPaperclip: VersionEntry;
  paperclip: VersionEntry;
  plugins: Record<string, VersionEntry>;
  generatedAt: string;
};

const PLUGIN_DISPLAY_NAMES: Record<string, string> = {
  "paperclip.backup": "Backup Plugin",
  "paperclip.git-merges": "Git Merges",
};

/**
 * Plugin keys allowed to surface in /api/versions. Order is preserved
 * in the response so the badge renders deterministically. Anything not
 * in this list is filtered out — the badge is the only consumer and
 * matches the operator-facing display contract (BTC-Paperclip + Paperclip
 * + Backup Plugin + Git Merges only).
 */
const SURFACED_PLUGIN_KEYS: readonly string[] = [
  "paperclip.backup",
  "paperclip.git-merges",
] as const;

function readVersionFile(path: string): string | null {
  try {
    if (!existsSync(path)) return null;
    const raw = readFileSync(path, "utf8").trim();
    return raw.length > 0 ? raw : null;
  } catch (err) {
    logger.warn?.(`versionsRoutes: failed to read ${path}: ${(err as Error).message}`);
    return null;
  }
}

function readPackageJsonVersion(packageJsonPath: string): string | null {
  try {
    if (!existsSync(packageJsonPath)) return null;
    const raw = readFileSync(packageJsonPath, "utf8");
    const parsed = JSON.parse(raw) as { version?: unknown };
    return typeof parsed.version === "string" ? parsed.version : null;
  } catch (err) {
    logger.warn?.(`versionsRoutes: failed to parse ${packageJsonPath}: ${(err as Error).message}`);
    return null;
  }
}

function resolveWorktreeRoot(): string {
  // Prefer git's worktree top-level (robust to whichever subdir the
  // server was started from). Fall back to cwd only if git is unavailable.
  try {
    const out = execFileSync("git", ["rev-parse", "--show-toplevel"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 1500,
    }).trim();
    if (out.length > 0) return out;
  } catch {
    // not a git repo or git unavailable — fall through
  }
  return process.cwd();
}

function versionForPlugin(row: {
  pluginKey: string;
  packagePath: string | null;
  version: string | null;
}): VersionEntry | null {
  if (!row.packagePath) {
    // Plugin installed via npm (no local path on disk). Surface the
    // DB-recorded version if present.
    if (row.version) {
      return { version: row.version, source: "plugins.version (npm)" };
    }
    return null;
  }

  // 1. BTC-pinned VERSION file (when present) wins.
  const versionFile = join(row.packagePath, "VERSION");
  const pinned = readVersionFile(versionFile);
  if (pinned) {
    return { version: pinned, source: `${row.packagePath}/VERSION` };
  }

  // 2. package.json#version fallback.
  const pkgJsonPath = join(row.packagePath, "package.json");
  const pkgVersion = readPackageJsonVersion(pkgJsonPath);
  if (pkgVersion) {
    return { version: pkgVersion, source: `${pkgJsonPath}#version` };
  }

  // 3. DB-recorded version last resort.
  if (row.version) {
    return { version: row.version, source: "plugins.version (fallback)" };
  }
  return null;
}

export function versionsRoutes(db: Db): Router {
  const router = Router();

  router.get("/", async (_req, res) => {
    try {
      // 1) BTC-Paperclip version (worktree-root VERSION file)
      const worktreeRoot = resolveWorktreeRoot();
      const btcVersionFile = join(worktreeRoot, "VERSION");
      const btcVersion = readVersionFile(btcVersionFile);
      const btcPaperclip: VersionEntry = btcVersion
        ? { version: btcVersion, source: btcVersionFile }
        : {
            version: "0.0.0.0",
            source: `missing: VERSION not found at ${btcVersionFile}`,
          };

      // 2) Paperclip upstream version (server/package.json)
      const paperclip: VersionEntry = {
        version: serverVersion,
        source: "server/package.json#version",
      };

      // 3) Plugin versions (DB-driven; surface only non-uninstalled AND
      //    only those whose plugin_key is in SURFACED_PLUGIN_KEYS)
      const pluginsResp: Record<string, VersionEntry> = {};
      try {
        const rows = await db
          .select({
            pluginKey: plugins.pluginKey,
            packagePath: plugins.packagePath,
            version: plugins.version,
          })
          .from(plugins)
          .where(ne(plugins.status, "uninstalled"));

        // Iterate SURFACED_PLUGIN_KEYS in declaration order so the
        // response is deterministic regardless of DB row order.
        for (const key of SURFACED_PLUGIN_KEYS) {
          const row = rows.find((r) => r.pluginKey === key);
          if (!row) continue; // plugin not installed in this worktree
          const entry = versionForPlugin(row);
          if (!entry) continue; // no resolvable version
          const label = PLUGIN_DISPLAY_NAMES[key] ?? key;
          pluginsResp[label] = entry;
        }
      } catch (dbErr) {
        // Don't fail the whole endpoint on DB trouble — surface a
        // sentinel key so the badge can render the rest.
        pluginsResp["(db error)"] = {
          version: "?",
          source: `error: ${(dbErr as Error).message}`,
        };
      }

      const body: VersionsResponse = {
        btcPaperclip,
        paperclip,
        plugins: pluginsResp,
        generatedAt: new Date().toISOString(),
      };

      res.json(body);
    } catch (err) {
      logger.error?.(`versionsRoutes: ${(err as Error).message}`);
      res.status(500).json({ error: "version_lookup_failed" });
    }
  });

  return router;
}