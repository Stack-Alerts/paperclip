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

describe("cleanup panel: data provider shape", () => {
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
