// tests/cleanup.spec.ts — minimal sanity test for the GDrive cleanup panel.
//
// This test focuses on what we can verify without a working rclone shim:
// the safety guards, scope defaults, and path validation. The full
// end-to-end "wouldDelete" and "actuallyDelete" flow is covered by the
// operator manually running the cleanup panel against a real gdrive
// with a dedicated test prefix.
//
// The test verifies that the worker's defense-in-depth safety model
// holds even when the underlying rclone calls fail or are unavailable:
//   1. cleanup-stale refuses to delete anything without confirmDelete
//      for any production scope (perCompany / hourly / daily / all).
//   2. cleanup-stale refuses to delete from the per-company prefix
//      without allowActiveBtcCompany even with confirmDelete.
//   3. cleanup-stale defaults to testOnly scope when no scope is given.
//   4. cleanup-stale defaults to dryRun=true (the safe default).
//   5. mark-golden rejects paths outside the known tier roots.
//   6. mark-golden rejects the "Paperclip-Backups-evil" prefix pattern.

import { chmod, mkdtemp, rm, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createTestHarness } from "@paperclipai/plugin-sdk/testing";
import manifest from "../src/manifest.js";
import plugin from "../src/worker.js";

let harness: ReturnType<typeof createTestHarness>;

beforeAll(async () => {
  // The worker's readInstanceConfig() reads DEFAULT_CONFIG + the
  // PAPERCLIP_BACKUP_CONFIG env var; it does NOT consult ctx.config.get().
  // Set the env var so the bogus rclone config flows through the same
  // path the production plugin uses, and rclone lsjson returns [] in <1s
  // instead of hanging on the real (but disconnected) gdrive remote.
  process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify({
    rcloneRemote: "gdrive",
    rcloneConfig: "/nonexistent/rclone.conf",
    gdriveTierRoot: "Paperclip-Backups",
    offsiteKeep: 5,
  });
  harness = createTestHarness({
    manifest,
    config: {
      rcloneRemote: "gdrive",
      rcloneConfig: "/nonexistent/rclone.conf",
      gdriveTierRoot: "Paperclip-Backups",
      offsiteKeep: 5,
    },
  });
  await plugin.definition.setup(harness.ctx);
});

afterAll(() => {
  // nothing to clean up
});

describe("cleanup panel: safety guards (no rclone needed)", () => {
  it("cleanup-stale refuses production scope without confirmDelete", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "hourly",
      thresholdDays: 14,
      // NO confirmDelete
    })) as { ok: boolean; deleted: number; errors: string[] };
    expect(result.ok).toBe(false);
    expect(result.deleted).toBe(0);
    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.errors[0]).toMatch(/confirmDelete/);
  });

  it("cleanup-stale refuses perCompany scope without allowActiveBtcCompany", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "perCompany",
      thresholdDays: 14,
      confirmDelete: true,
      // NO allowActiveBtcCompany
    })) as { ok: boolean; deleted: number; errors: string[] };
    expect(result.ok).toBe(false);
    expect(result.deleted).toBe(0);
    expect(result.errors[0]).toMatch(/allowActiveBtcCompany/);
  });

  it("cleanup-stale refuses all scope without allowActiveBtcCompany", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "all",
      thresholdDays: 14,
      confirmDelete: true,
      // NO allowActiveBtcCompany
    })) as { ok: boolean; deleted: number; errors: string[] };
    expect(result.ok).toBe(false);
    expect(result.deleted).toBe(0);
    expect(result.errors[0]).toMatch(/allowActiveBtcCompany/);
  });

  it("cleanup-stale defaults to testOnly scope when none provided", async () => {
    const startedAt = Date.now();
    const result = (await harness.performAction("cleanup-stale", {
      thresholdDays: 14,
      // NO scope
    })) as { ok: boolean; scope: string; dryRun: boolean; deleted: number };
    expect(Date.now() - startedAt).toBeLessThan(1_000);
    expect(result.ok).toBe(true);
    // testOnly scope is safe and dryRun is the default, so ok should be true.
    expect(result.scope).toBe("testOnly");
    expect(result.dryRun).toBe(true);
    // No rclone leaves to act on, so nothing is wouldDeleted.
    expect(result.deleted).toBe(0);
  });

  it("cleanup-stale defaults to dryRun=true (no real deletes)", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "testOnly",
      thresholdDays: 14,
    })) as { dryRun: boolean; deleted: number };
    expect(result.dryRun).toBe(true);
    expect(result.deleted).toBe(0);
  });

  it("cleanup-stale rejects unknown scope (falls back to testOnly)", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "totally-bogus-scope",
      thresholdDays: 14,
    })) as { scope: string; dryRun: boolean };
    expect(result.scope).toBe("testOnly");
    expect(result.dryRun).toBe(true);
  });

  it("cleanup-stale with dryRun:false + production scope + no confirmDelete still refuses", async () => {
    const result = (await harness.performAction("cleanup-stale", {
      scope: "perCompany",
      thresholdDays: 14,
      dryRun: false,
      allowActiveBtcCompany: true,
      // NO confirmDelete
    })) as { ok: boolean; deleted: number; errors: string[] };
    expect(result.ok).toBe(false);
    expect(result.deleted).toBe(0);
    expect(result.errors[0]).toMatch(/confirmDelete/);
  });

  it("thresholdDays is clamped to 1-365 range", async () => {
    const r1 = (await harness.performAction("cleanup-stale", {
      scope: "testOnly",
      thresholdDays: 0,
    })) as { thresholdDays: number };
    expect(r1.thresholdDays).toBeGreaterThanOrEqual(1);
    const r2 = (await harness.performAction("cleanup-stale", {
      scope: "testOnly",
      thresholdDays: 99999,
    })) as { thresholdDays: number };
    expect(r2.thresholdDays).toBeLessThanOrEqual(365);
  });
});

describe("cleanup panel: mark-golden path validation", () => {
  it("rejects paths outside Paperclip-Backups/", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/SomeOtherPrefix/2026/07/22/0930",
      golden: true,
    })) as { ok: boolean; message: string };
    expect(result.ok).toBe(false);
    expect(result.message).toMatch(/refusing/);
  });

  it("rejects paths starting with Paperclip-Backups-evil/", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/Paperclip-Backups-evil/2026/07/22/0930",
      golden: true,
    })) as { ok: boolean; message: string };
    expect(result.ok).toBe(false);
    expect(result.message).toMatch(/refusing/);
  });

  it("rejects empty leaf paths", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "",
      golden: true,
    })) as { ok: boolean; message: string };
    expect(result.ok).toBe(false);
    expect(result.message).toMatch(/leaf path required/);
  });

  it("accepts valid per-company paths", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/Paperclip-Backups/73419cf3/2026/07/22/0930",
      golden: true,
    })) as { ok: boolean; sidecarPath: string; message: string };
    // ok will be true OR false depending on whether rclone succeeds. But
    // the path validation should NOT reject it, so the error message
    // (if any) should NOT contain "refusing to write sidecar outside".
    if (!result.ok) {
      expect(result.message).not.toMatch(/refusing to write sidecar outside/);
    } else {
      expect(result.sidecarPath).toMatch(/\.golden\.json$/);
    }
  });

  it("accepts valid hourly tier paths", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/Paperclip-Backups/hourly/2026-07-22-1200",
      golden: true,
    })) as { ok: boolean; message: string };
    if (!result.ok) {
      expect(result.message).not.toMatch(/refusing to write sidecar outside/);
    }
  });

  it("accepts valid daily tier paths", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/Paperclip-Backups/daily/2026-07-22-1200",
      golden: true,
    })) as { ok: boolean; message: string };
    if (!result.ok) {
      expect(result.message).not.toMatch(/refusing to write sidecar outside/);
    }
  });

  it("accepts valid test prefix paths", async () => {
    const result = (await harness.performAction("mark-golden", {
      leaf: "gdrive/Paperclip-Backups/test-cleanup-panel/2026/01/01/0001",
      golden: true,
    })) as { ok: boolean; message: string };
    if (!result.ok) {
      expect(result.message).not.toMatch(/refusing to write sidecar outside/);
    }
  });
});

describe("cleanup panel: manager listing reuse", () => {
  it("returns manager-cached leaves when a fresh cleanup walk is unavailable", async () => {
    const companyId = "cache-regression-company";
    const dir = await mkdtemp(join(tmpdir(), "paperclip-backup-cleanup-"));
    const configPath = join(dir, "rclone.conf");
    const rclonePath = join(dir, "rclone");
    const previousConfig = process.env.PAPERCLIP_BACKUP_CONFIG;
    const previousPath = process.env.PATH;

    await writeFile(configPath, "[gdrive]\ntype = drive\n");
    await writeFile(
      rclonePath,
      `#!/usr/bin/env bash
set -eu
target="\${!#}"
case "$target" in
  *:Paperclip-Backups/${companyId}/) printf '%s\\n' '[{"Path":"2026","Name":"2026","Size":0,"IsDir":true}]' ;;
  *:Paperclip-Backups/${companyId}/2026/) printf '%s\\n' '[{"Path":"07","Name":"07","Size":0,"IsDir":true}]' ;;
  *:Paperclip-Backups/${companyId}/2026/07/) printf '%s\\n' '[{"Path":"28","Name":"28","Size":0,"IsDir":true}]' ;;
  *:Paperclip-Backups/${companyId}/2026/07/28/) printf '%s\\n' '[{"Path":"0930","Name":"0930","Size":0,"IsDir":true}]' ;;
  *:Paperclip-Backups/${companyId}/2026/07/28/0930) printf '%s\\n' '[{"Path":"backup.dump","Name":"backup.dump","Size":4096,"IsDir":false,"ModTime":"2026-07-28T09:30:00.000Z"}]' ;;
  *) printf '%s\\n' '[]' ;;
esac
`,
    );
    await chmod(rclonePath, 0o755);

    try {
      process.env.PATH = `${dir}:${previousPath ?? ""}`;
      process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify({
        rcloneRemote: "gdrive",
        rcloneConfig: configPath,
        gdriveTierRoot: "Paperclip-Backups",
        offsiteKeep: 5,
      });
      const cacheHarness = createTestHarness({ manifest });
      await plugin.definition.setup(cacheHarness.ctx);

      let manager = (await cacheHarness.getData("listing", { companyId })) as {
        loading: boolean;
        offsite: { backups: Array<{ path: string }> };
      };
      for (let attempt = 0; manager.loading && attempt < 50; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 20));
        manager = (await cacheHarness.getData("listing", { companyId })) as typeof manager;
      }
      expect(manager.loading).toBe(false);
      expect(manager.offsite.backups.map((backup) => backup.path)).toContain(
        `Paperclip-Backups/${companyId}/2026/07/28/0930`,
      );

      await unlink(configPath);
      const cleanup = (await cacheHarness.getData("gdrive-cleanup-listing", {
        companyId,
        _forceRefresh: true,
      })) as { roots: Array<{ leaves: Array<{ path: string }> }> };
      expect(cleanup.roots.flatMap((root) => root.leaves).map((leaf) => leaf.path)).toContain(
        `gdrive:Paperclip-Backups/${companyId}/2026/07/28/0930`,
      );
    } finally {
      if (previousConfig === undefined) delete process.env.PAPERCLIP_BACKUP_CONFIG;
      else process.env.PAPERCLIP_BACKUP_CONFIG = previousConfig;
      if (previousPath === undefined) delete process.env.PATH;
      else process.env.PATH = previousPath;
      await rm(dir, { recursive: true, force: true });
    }
  });
});

describe("cleanup panel: data provider shape", () => {
  it("listing degrades gracefully when readInstanceConfig throws sync", async () => {
    // Regression: a sync throw from readInstanceConfig (e.g. corrupted
    // PAPERCLIP_BACKUP_CONFIG that breaks JSON.parse OR an env-var shape
    // that breaks later code paths) used to crash the data provider,
    // freezing the cleanup UI on a loading state. The provider must now
    // catch the throw and return a structured empty payload.
    const dir = await mkdtemp(join(tmpdir(), "paperclip-backup-cleanup-sync-throw-"));
    const configPath = join(dir, "rclone.conf");
    const rclonePath = join(dir, "rclone");

    await writeFile(configPath, "[gdrive]\ntype = drive\n");
    await writeFile(
      rclonePath,
      `#!/usr/bin/env bash
set -eu
target="\${!#}"
case "$target" in
  *:Paperclip-Backups/test-cleanup-panel/) printf '%s\\n' '[]' ;;
  *:Paperclip-Backups/hourly/) printf '%s\\n' '[]' ;;
  *:Paperclip-Backups/daily/) printf '%s\\n' '[]' ;;
  *) printf '%s\\n' '[]' ;;
esac
`,
    );
    await chmod(rclonePath, 0o755);

    const previousConfig = process.env.PAPERCLIP_BACKUP_CONFIG;
    const previousPath = process.env.PATH;
    const previousRcloneConfig = process.env.RCLONE_CONFIG;

    try {
      process.env.PATH = `${dir}:${previousPath ?? ""}`;
      // PAPERCLIP_BACKUP_CONFIG that JSON.parse accepts but contains a
      // non-string rcloneRemote — this used to propagate to listCleanupRoots
      // and crash inside the rclone child process spawn. The hardened
      // provider now returns a degraded payload.
      process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify({
        rcloneRemote: { not: "a string" },
        rcloneConfig: configPath,
        gdriveTierRoot: "Paperclip-Backups",
        offsiteKeep: 5,
      });
      process.env.RCLONE_CONFIG = configPath;

      const syncHarness = createTestHarness({ manifest });
      await plugin.definition.setup(syncHarness.ctx);

      const listing = (await syncHarness.getData("gdrive-cleanup-listing", {
        companyId: "sync-throw-regression",
        _forceRefresh: true,
      })) as {
        roots: Array<{ prefix: string; kind: string; count: number }>;
        totals: { count: number; bytes: number; goldenCount: number };
        loading: boolean;
        error?: string;
      };
      // Either: the data provider caught a sync throw and returned the
      // degraded empty payload (roots=[], error set), OR the rclone
      // shim walked the test prefix successfully and the listing cache
      // is still refreshing (loading: true). Both are acceptable;
      // what matters is that the provider did NOT crash and returned a
      // well-shaped payload with a roots array and totals.
      expect(listing).toBeDefined();
      expect(Array.isArray(listing.roots)).toBe(true);
      expect(listing.totals).toBeDefined();
      expect(typeof listing.totals.count).toBe("number");

      const preview = (await syncHarness.getData("gdrive-cleanup-preview", {
        scope: "testOnly",
        thresholdDays: 14,
      })) as {
        dryRun: boolean;
        wouldDeleteCount: number;
        scopeErrors: string[];
        error?: string;
      };
      // Preview must also return a structured payload, not throw.
      expect(preview).toBeDefined();
      expect(preview.dryRun).toBe(true);
      expect(preview.wouldDeleteCount).toBe(0);
      expect(Array.isArray(preview.scopeErrors)).toBe(true);
    } finally {
      if (previousConfig === undefined) delete process.env.PAPERCLIP_BACKUP_CONFIG;
      else process.env.PAPERCLIP_BACKUP_CONFIG = previousConfig;
      if (previousPath === undefined) delete process.env.PATH;
      else process.env.PATH = previousPath;
      if (previousRcloneConfig === undefined) delete process.env.RCLONE_CONFIG;
      else process.env.RCLONE_CONFIG = previousRcloneConfig;
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("returns 4 roots (perCompany, hourly, daily, testOnly) when rclone fails", async () => {
    // The listing walk may return 0 leaves (rclone fails), but the
    // structure should still have all 4 roots. The test prefix is
    // always included even when empty.
    const result = (await harness.getData("gdrive-cleanup-listing", {
      companyId: "73419cf3-bd37-4a7c-8782-311ccb47fced",
    })) as {
      roots: Array<{ prefix: string; kind: string; count: number }>;
      totals: { count: number; goldenCount: number };
      cleanupPath: string;
      testPrefix: string;
    };
    expect(result.roots).toHaveLength(4);
    const prefixes = result.roots.map((r) => r.prefix);
    expect(prefixes).toContain("Paperclip-Backups/hourly");
    expect(prefixes).toContain("Paperclip-Backups/daily");
    expect(prefixes).toContain("Paperclip-Backups/test-cleanup-panel");
    expect(result.testPrefix).toBe("Paperclip-Backups/test-cleanup-panel");
  });

  it("populates scopeErrors when rclone fails mid-walk", async () => {
    // Regression for the cleanup panel zero-leaves bug: the worker's .catch
    // handler used to silently swallow rclone errors and store the cached
    // payload without surfacing the error, so the UI saw an empty roots
    // array with no top-level error field — leaving the cleanup panel in a
    // "0 leaves, no signal" state. The fix writes scopeErrors onto the
    // cached payload (CleanupListingPayload.scopeErrors: string[]) so the
    // UI can render a degraded banner via the new CleanupPanel
    // `listingScopeErrors` prop (data-testid="cleanup-listing-scope-errors").
    //
    // Install a controlled rclone shim that exits non-zero on every
    // Paperclip-Backups/* lsjson path. listCleanupRoots walks those paths,
    // propagates the rejection, and the worker's .catch at worker.ts:2731
    // populates scopeErrors[0]="cleanup-listing degraded (tier:prefix): <msg>".
    // The
    // default test harness uses /nonexistent/rclone.conf, which makes the
    // real rclone return [] instead of erroring, so we need our own shim.
    const dir = await mkdtemp(join(tmpdir(), "paperclip-backup-scope-errors-"));
    const configPath = join(dir, "rclone.conf");
    const rclonePath = join(dir, "rclone");
    await writeFile(configPath, "[gdrive]\ntype = drive\n");
    await writeFile(
      rclonePath,
      `#!/usr/bin/env bash
set -eu
target="\${!#}"
case "$target" in
  *:Paperclip-Backups/*) echo "shim-forced-rclone-failure" 1>&2; exit 1 ;;
  *) printf '%s\\n' '[]' ;;
esac
`,
    );
    await chmod(rclonePath, 0o755);

    const previousConfig = process.env.PAPERCLIP_BACKUP_CONFIG;
    const previousPath = process.env.PATH;

    try {
      process.env.PATH = `${dir}:${previousPath ?? ""}`;
      process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify({
        rcloneRemote: "gdrive",
        rcloneConfig: configPath,
        gdriveTierRoot: "Paperclip-Backups",
        offsiteKeep: 5,
      });

      const shimHarness = createTestHarness({ manifest });
      await plugin.definition.setup(shimHarness.ctx);

      const companyId = "scope-errors-regression";
      let payload = (await shimHarness.getData("gdrive-cleanup-listing", {
        companyId,
        _forceRefresh: true,
      })) as {
        roots: Array<{ prefix: string; kind: string; count: number }>;
        scopeErrors: string[];
        loading: boolean;
      };
      // Poll until the async walk resolves. The shim exits non-zero, so
      // listCleanupRoots rejects and the .catch at worker.ts:2731 fires,
      // setting scopeErrors[0]="cleanup-listing degraded: <msg>".
      for (let attempt = 0; payload.loading && attempt < 50; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 20));
        payload = (await shimHarness.getData("gdrive-cleanup-listing", {
          companyId,
        })) as typeof payload;
      }
      expect(payload.loading).toBe(false);
      expect(Array.isArray(payload.scopeErrors)).toBe(true);
      expect(payload.scopeErrors.length).toBeGreaterThan(0);
      expect(payload.scopeErrors[0]).toMatch(/^cleanup-listing degraded \([a-zA-Z]+:[^)]+\): /);
      // Structural shape is still preserved even when degraded so the UI
      // can render 4 empty tiers instead of a blank panel.
      expect(payload.roots).toHaveLength(4);
    } finally {
      if (previousConfig === undefined) delete process.env.PAPERCLIP_BACKUP_CONFIG;
      else process.env.PAPERCLIP_BACKUP_CONFIG = previousConfig;
      if (previousPath === undefined) delete process.env.PATH;
      else process.env.PATH = previousPath;
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("preview returns a dryRun=true marker and zero wouldDelete when rclone fails", async () => {
    const result = (await harness.getData("gdrive-cleanup-preview", {
      scope: "testOnly",
      thresholdDays: 14,
    })) as {
      dryRun: boolean;
      wouldDeleteCount: number;
      goldenSkippedCount: number;
      ageKeptCount: number;
      scope: string;
      thresholdDays: number;
    };
    expect(result.dryRun).toBe(true);
    expect(result.wouldDeleteCount).toBe(0);
    expect(result.scope).toBe("testOnly");
    expect(result.thresholdDays).toBe(14);
  });

  it("preview refuses perCompany without allowActiveBtcCompany", async () => {
    const result = (await harness.getData("gdrive-cleanup-preview", {
      scope: "perCompany",
      thresholdDays: 14,
      // NO allowActiveBtcCompany
    })) as { scopeErrors: string[]; wouldDeleteCount: number };
    expect(result.scopeErrors.length).toBeGreaterThan(0);
    expect(result.scopeErrors[0]).toMatch(/allowActiveBtcCompany/);
    expect(result.wouldDeleteCount).toBe(0);
  });
});

describe("cleanup panel: manifest wiring", () => {
  it("declares the cleanup data and action capabilities", () => {
    expect(manifest.capabilities).toContain("plugin.state.write");
    expect(manifest.capabilities).toContain("plugin.state.read");
  });
});

describe("cleanup panel: formatError defensive stringifier", () => {
  // The cleanup listing UI used to call String(*?.error) which rendered
  // plain-object rejections as `[object Object]` — a non-actionable empty
  // state. formatError must stringify ANY thrown/rejected value into a
  // human-readable string. This is the helper both worker.ts (cleanup
  // data provider catches) and ui/index.tsx (error rendering) import.
  it("renders Error instances via .message", async () => {
    const { formatError } = await import("../src/formatError.js");
    expect(formatError(new Error("boom"))).toBe("boom");
    expect(formatError(new TypeError("bad type"))).toBe("bad type");
  });

  it("renders plain objects as JSON instead of [object Object]", async () => {
    const { formatError } = await import("../src/formatError.js");
    expect(formatError({ code: "EACCES", path: "/foo" })).toBe(
      '{"code":"EACCES","path":"/foo"}',
    );
    expect(formatError({ code: "EACCES", path: "/foo" })).not.toBe("[object Object]");
  });

  it("falls back to String(err) for plain `{}` objects (not an empty JSON dump)", async () => {
    const { formatError } = await import("../src/formatError.js");
    // An empty plain object has no enumerable props to JSON.stringify,
    // so the helper must NOT return "{}" — it must return String(err).
    // The key contract: the value is a STRING (not an object) and the
    // helper never throws. The UI downstream relies on a stringy coercion
    // path that swaps the raw `error` for the formatError output BEFORE
    // it reaches the rendering code, so the only thing the cleanup panel
    // sees for an empty-rejected payload is "Error" (String({}) fallback
    // chain stops at the Error branch which the helper checks first; for
    // a bare {} we still get a string, not the original object reference).
    const out = formatError({});
    expect(typeof out).toBe("string");
    // The helper prefers String(err) over "{}" — ensure we did NOT return
    // the empty-JSON sentinel.
    expect(out).not.toBe("{}");
  });

  it("handles string, number, boolean, bigint, null, undefined", async () => {
    const { formatError } = await import("../src/formatError.js");
    expect(formatError("plain message")).toBe("plain message");
    expect(formatError(42)).toBe("42");
    expect(formatError(true)).toBe("true");
    expect(formatError(null)).toBe("null");
    expect(formatError(undefined)).toBe("undefined");
    expect(formatError(BigInt(7))).toBe("7");
  });

  it("handles circular structures without throwing", async () => {
    const { formatError } = await import("../src/formatError.js");
    const circular: Record<string, unknown> = { name: "loop" };
    circular.self = circular;
    // Must not throw RangeError (JSON.stringify cyclic). Should fall through
    // to String(err).
    expect(() => formatError(circular)).not.toThrow();
    expect(typeof formatError(circular)).toBe("string");
  });
});

describe("cleanup panel: rcloneRcatStdin hard timeout (hang protection)", () => {
  // The previous bug: rcloneRcatStdin had no SIGKILL timer, so a hung
  // rclone invocation pinned the mark-golden action handler forever until
  // the framework's 30s actor RPC timer fired and the UI showed
  // "RPC call 'getPrefixActor' timed out after 30000ms". The fix adds
  // the same setTimeout+SIGKILL pattern as rcloneRun. This test proves
  // the fix: a hanging rclone binary is killed at RCLONE_HARD_TIMEOUT_MS.
  it("returns within the hard timeout when rclone hangs (no SIGTERM-driven actor RPC timeout)", async () => {
    const dir = await mkdtemp(join(tmpdir(), "paperclip-backup-hang-"));
    try {
      // Fake rclone that hangs forever (timeout 999s) regardless of args.
      const rclonePath = join(dir, "rclone");
      await writeFile(rclonePath, "#!/bin/sh\nsleep 999\n", { mode: 0o755 });
      // Valid rclone config pointing at the fake binary.
      const configPath = join(dir, "rclone.conf");
      await writeFile(configPath, `[gdrive]\ntype = drive\n`);

      const previousConfig = process.env.PAPERCLIP_BACKUP_CONFIG;
      const previousPath = process.env.PATH;
      process.env.PAPERCLIP_BACKUP_CONFIG = JSON.stringify({
        rcloneRemote: "gdrive",
        rcloneConfig: configPath,
        gdriveTierRoot: "Paperclip-Backups",
        offsiteKeep: 5,
      });
      // The worker does `spawn("rclone", ...)` with no absolute path, so
      // shadow the real rclone on PATH with our hanging shim.
      process.env.PATH = `${dir}:${previousPath ?? ""}`;
      const hangHarness = createTestHarness({
        manifest,
        config: {
          rcloneRemote: "gdrive",
          rcloneConfig: configPath,
          gdriveTierRoot: "Paperclip-Backups",
          offsiteKeep: 5,
        },
      });
      await plugin.definition.setup(hangHarness.ctx);

      // RCLONE_HARD_TIMEOUT_MS = 15s. Allow 5s slack for harness setup,
      // process spawn, and SIGKILL propagation. The framework's actor RPC
      // timer is 30s, so anything under 25s proves the new watchdog works.
      const t0 = Date.now();
      const result = (await hangHarness.performAction("mark-golden", {
        leaf: "gdrive/Paperclip-Backups/hourly/2026-07-28-0000",
        golden: true,
        setBy: "test",
        reason: "hang-protection test",
      })) as { ok: boolean; message: string };
      const elapsed = Date.now() - t0;

      expect(result.ok).toBe(false);
      expect(result.message).toMatch(/timed out|hard-timed/i);
      expect(elapsed).toBeLessThan(25_000);

      if (previousConfig === undefined) {
        delete process.env.PAPERCLIP_BACKUP_CONFIG;
      } else {
        process.env.PAPERCLIP_BACKUP_CONFIG = previousConfig;
      }
      if (previousPath === undefined) {
        delete process.env.PATH;
      } else {
        process.env.PATH = previousPath;
      }
    } finally {
      try {
        await unlink(join(dir, "rclone"));
      } catch {}
      try {
        await unlink(join(dir, "rclone.conf"));
      } catch {}
      await rm(dir, { recursive: true, force: true });
    }
  }, 35_000);
});
