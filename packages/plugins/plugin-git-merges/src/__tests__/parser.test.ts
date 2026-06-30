import { describe, expect, it } from "vitest";
import { parseMergeQueueOutput } from "../parser.js";

describe("parseMergeQueueOutput — JSON deriveStatus", () => {
  function buildQueueItem(prNumber: number | null, passed: number, total: number, failed = 0, mergeable: string | null = null): string {
    const obj = {
      issue_id: `uuid-${prNumber ?? "none"}`,
      display_key: `BTCAAAAA-${prNumber ?? "X"}`,
      title: "test",
      updated_at: "2026-06-30T00:00:00Z",
      fix_sha: prNumber ? "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" : null,
      already_merged: false,
      pr_number: prNumber,
      pr_title: prNumber ? `feat: PR #${prNumber}` : null,
      pr_mergeable: mergeable,
      passed: String(passed),
      failed: String(failed),
      total: String(total),
      checks: [],
    };
    return JSON.stringify({ queue: [obj], blocked_chains: [], approval_requests: [] });
  }

  it("returns no-pr when there is no PR number", () => {
    const out = parseMergeQueueOutput(buildQueueItem(null, 0, 0));
    expect(out.blocks[0]?.status).toBe("no-pr");
  });

  it("returns ready when CI fully green and mergeable is clean", () => {
    const out = parseMergeQueueOutput(buildQueueItem(271, 25, 25, 0, "clean"));
    expect(out.blocks[0]?.status).toBe("ready");
  });

  it("returns ready when CI fully green and mergeable is blocked (branch protection / required review)", () => {
    // Without this case, every PR that was green but blocked on required-review
    // showed up as "unknown", which made the panel look like every block was
    // stalled even when merge_dispatch was the only thing left to do.
    const out = parseMergeQueueOutput(buildQueueItem(272, 25, 25, 0, "blocked"));
    expect(out.blocks[0]?.status).toBe("ready");
  });

  it("returns ready when CI fully green and mergeable is empty/null", () => {
    const out = parseMergeQueueOutput(buildQueueItem(273, 25, 25, 0, null));
    expect(out.blocks[0]?.status).toBe("ready");
  });

  it("returns waiting (not ready) when CI fully green but mergeable is dirty (conflicts)", () => {
    const out = parseMergeQueueOutput(buildQueueItem(274, 25, 25, 0, "dirty"));
    expect(out.blocks[0]?.status).toBe("waiting");
  });

  it("returns waiting (not ready) when CI fully green but mergeable is draft", () => {
    const out = parseMergeQueueOutput(buildQueueItem(275, 25, 25, 0, "draft"));
    expect(out.blocks[0]?.status).toBe("waiting");
  });

  it("returns failing when any check failed", () => {
    const out = parseMergeQueueOutput(buildQueueItem(280, 5, 10, 5, "clean"));
    expect(out.blocks[0]?.status).toBe("failing");
  });

  it("returns waiting when some checks passed but not all (and no failures)", () => {
    const out = parseMergeQueueOutput(buildQueueItem(281, 19, 24, 0, "blocked"));
    expect(out.blocks[0]?.status).toBe("waiting");
  });

  it("returns unknown when there is a PR but no CI data at all", () => {
    const out = parseMergeQueueOutput(buildQueueItem(282, 0, 0, 0, "clean"));
    expect(out.blocks[0]?.status).toBe("unknown");
  });
});

describe("parseMergeQueueOutput — JSON ready/totals pass-through", () => {
  it("carries passed/total through to the block", () => {
    const obj = {
      issue_id: "uuid-1",
      display_key: "BTCAAAAA-1",
      title: "x",
      updated_at: "2026-06-30T00:00:00Z",
      fix_sha: null,
      already_merged: false,
      pr_number: 1,
      pr_title: "x",
      pr_mergeable: "clean",
      passed: "19",
      failed: "0",
      total: "24",
      checks: [],
    };
    const out = parseMergeQueueOutput(
      JSON.stringify({ queue: [obj], blocked_chains: [], approval_requests: [] }),
    );
    expect(out.blocks[0]?.progressPassed).toBe(19);
    expect(out.blocks[0]?.progressTotal).toBe(24);
  });
});