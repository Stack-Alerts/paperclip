import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { buildPaperclipWakePayload } from "../services/heartbeat.js";

const ENV_VARS = [
  "PAPERCLIP_WAKE_CONTINUATION_SUMMARY_MAX_CHARS",
  "PAPERCLIP_WAKE_PAYLOAD_COMPRESS_THRESHOLD_CHARS",
  "PAPERCLIP_WAKE_PAYLOAD_COMPRESS_AGGRESSIVE_CHARS",
] as const;

const SAVED_ENV: Record<string, string | undefined> = {};

function withClearedEnv() {
  for (const name of ENV_VARS) {
    SAVED_ENV[name] = process.env[name];
    delete process.env[name];
  }
}

function restoreEnv() {
  for (const name of ENV_VARS) {
    if (SAVED_ENV[name] === undefined) {
      delete process.env[name];
    } else {
      process.env[name] = SAVED_ENV[name];
    }
  }
  for (const name of ENV_VARS) delete SAVED_ENV[name];
}

const FAKE_DB = {} as never;

function baseContextSnapshot(overrides: Record<string, unknown> = {}) {
  return {
    issueId: "issue-1",
    wakeReason: "issue_assigned",
    ...overrides,
  };
}

const ISSUE_SUMMARY = {
  id: "issue-1",
  identifier: "PAP-381",
  title: "Wake payload size reduction",
  status: "in_progress",
  priority: "high",
  workMode: "implementation",
};

function makeLongContinuationSummary(approxChars: number, sections: string[] = []) {
  const header = [
    "# Continuation Summary",
    "",
    "- Issue: PAP-381 — Wake payload size reduction",
    "- Status: in_progress",
    "- Priority: high",
    "- Current mode: implementation",
    "- Last updated by run: run-1",
    "- Agent: PlatformEngineer (claude_local)",
    "",
    "## Objective",
    "",
    "Reduce wake-payload size on transient_failure_retry wakes and compress over-size continuation summaries.",
    "",
    "## Acceptance Criteria",
    "",
    "- Wake payload no longer rejects as Prompt is too long",
    "- Configurable thresholds",
    "- Existing wakes still get full context",
    "",
  ].join("\n");

  const filler = "x".repeat(Math.max(0, approxChars - header.length));
  const extraSections = sections.length > 0 ? ["", ...sections] : [];
  return [header, filler, ...extraSections].join("\n");
}

describe("buildPaperclipWakePayload — wake payload size reduction (CAR-381)", () => {
  beforeEach(() => {
    withClearedEnv();
  });

  afterEach(() => {
    restoreEnv();
  });

  describe("Option 1A — transient_failure_retry drops ancestor context", () => {
    it("drops childIssueSummaries and unresolvedBlockerSummaries on transient_failure_retry", async () => {
      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot({
          wakeReason: "transient_failure_retry",
          childIssueSummaries: [
            { id: "child-1", identifier: "PAP-381-1", title: "Child one", status: "done" },
            { id: "child-2", identifier: "PAP-381-2", title: "Child two", status: "done" },
          ],
          childIssueSummaryTruncated: false,
          unresolvedBlockerIssueIds: ["blocker-1"],
          unresolvedBlockerSummaries: [
            { id: "blocker-1", identifier: "PAP-380", title: "Unblock 380", status: "todo" },
          ],
        }),
        issueSummary: ISSUE_SUMMARY,
      });

      expect(payload).not.toBeNull();
      expect(payload?.childIssueSummaries).toEqual([]);
      expect(payload?.childIssueSummaryTruncated).toBe(false);
      expect(payload?.unresolvedBlockerSummaries).toEqual([]);
      // Machine-readable blocker IDs are preserved — only the human-readable summaries are dropped.
      expect(payload?.unresolvedBlockerIssueIds).toEqual(["blocker-1"]);
    });

    it("preserves childIssueSummaries and unresolvedBlockerSummaries on ordinary wakes", async () => {
      const child = { id: "child-1", identifier: "PAP-381-1", title: "Child one", status: "done" };
      const blocker = { id: "blocker-1", identifier: "PAP-380", title: "Unblock 380", status: "todo" };

      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot({
          wakeReason: "issue_assigned",
          childIssueSummaries: [child],
          childIssueSummaryTruncated: false,
          unresolvedBlockerIssueIds: ["blocker-1"],
          unresolvedBlockerSummaries: [blocker],
        }),
        issueSummary: ISSUE_SUMMARY,
      });

      expect(payload).not.toBeNull();
      expect(payload?.childIssueSummaries).toEqual([child]);
      expect(payload?.childIssueSummaryTruncated).toBe(false);
      expect(payload?.unresolvedBlockerSummaries).toEqual([blocker]);
    });

    it("treats missing wakeReason as a non-transient wake and preserves ancestor context", async () => {
      const child = { id: "child-1", identifier: "PAP-381-1", title: "Child one", status: "done" };
      const blocker = { id: "blocker-1", identifier: "PAP-380", title: "Unblock 380", status: "todo" };

      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot({
          wakeReason: undefined,
          childIssueSummaries: [child],
          unresolvedBlockerIssueIds: ["blocker-1"],
          unresolvedBlockerSummaries: [blocker],
        }),
        issueSummary: ISSUE_SUMMARY,
      });

      expect(payload).not.toBeNull();
      expect(payload?.childIssueSummaries).toEqual([child]);
      expect(payload?.unresolvedBlockerSummaries).toEqual([blocker]);
    });
  });

  describe("Option 1B — continuation summary size compression", () => {
    it("truncates the continuation summary body to the configured max when over the limit", async () => {
      process.env.PAPERCLIP_WAKE_CONTINUATION_SUMMARY_MAX_CHARS = "2000";
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_THRESHOLD_CHARS = "1000000";

      const longBody = makeLongContinuationSummary(6_000);

      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot(),
        issueSummary: ISSUE_SUMMARY,
        continuationSummary: {
          key: "continuation-summary",
          title: "Continuation Summary",
          body: longBody,
          updatedAt: new Date("2026-04-18T12:00:00.000Z"),
        },
      });

      expect(payload).not.toBeNull();
      expect(payload?.continuationSummary).not.toBeNull();
      expect(payload?.continuationSummary?.body.length).toBe(2000);
      expect(payload?.continuationSummary?.bodyTruncated).toBe(true);
      expect(payload?.continuationSummary?.body).not.toContain("# Continuation Summary (compressed)");
    });

    it("compresses to a headline summary when serialized payload exceeds the threshold", async () => {
      process.env.PAPERCLIP_WAKE_CONTINUATION_SUMMARY_MAX_CHARS = "4000";
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_THRESHOLD_CHARS = "4000";
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_AGGRESSIVE_CHARS = "1500";

      const longBody = makeLongContinuationSummary(8_000);

      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot({
          padding: "Y".repeat(20_000),
        }),
        issueSummary: ISSUE_SUMMARY,
        continuationSummary: {
          key: "continuation-summary",
          title: "Continuation Summary",
          body: longBody,
          updatedAt: new Date("2026-04-18T12:00:00.000Z"),
        },
      });

      expect(payload).not.toBeNull();
      const compressed = payload?.continuationSummary;
      expect(compressed).not.toBeNull();
      expect(compressed?.body).toContain("# Continuation Summary (compressed)");
      expect(compressed?.body.length).toBeLessThanOrEqual(1_500);
      expect(compressed?.bodyTruncated).toBe(true);
      expect(compressed?.body).toContain("## Objective");
    });

    it("does not compress when serialized payload stays below the threshold", async () => {
      process.env.PAPERCLIP_WAKE_CONTINUATION_SUMMARY_MAX_CHARS = "4000";
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_THRESHOLD_CHARS = "1000000";

      const body = makeLongContinuationSummary(1_200);

      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot(),
        issueSummary: ISSUE_SUMMARY,
        continuationSummary: {
          key: "continuation-summary",
          title: "Continuation Summary",
          body,
          updatedAt: new Date("2026-04-18T12:00:00.000Z"),
        },
      });

      expect(payload).not.toBeNull();
      const continuation = payload?.continuationSummary;
      expect(continuation).not.toBeNull();
      expect(continuation?.body).toBe(body);
      expect(continuation?.body).not.toContain("# Continuation Summary (compressed)");
      expect(continuation?.bodyTruncated).toBe(false);
    });

    it("returns null continuationSummary when no summary was provided", async () => {
      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot(),
        issueSummary: ISSUE_SUMMARY,
      });

      expect(payload).not.toBeNull();
      expect(payload?.continuationSummary).toBeNull();
    });

    it("preserves continuation summary key/title/updatedAt through compression", async () => {
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_THRESHOLD_CHARS = "1000";
      process.env.PAPERCLIP_WAKE_PAYLOAD_COMPRESS_AGGRESSIVE_CHARS = "1500";

      const updatedAt = new Date("2026-04-18T12:00:00.000Z");
      const payload = await buildPaperclipWakePayload({
        db: FAKE_DB,
        companyId: "company-1",
        contextSnapshot: baseContextSnapshot({
          padding: "Z".repeat(10_000),
        }),
        issueSummary: ISSUE_SUMMARY,
        continuationSummary: {
          key: "continuation-summary",
          title: "Continuation Summary",
          body: makeLongContinuationSummary(3_000),
          updatedAt,
        },
      });

      const continuation = payload?.continuationSummary;
      expect(continuation).not.toBeNull();
      expect(continuation?.key).toBe("continuation-summary");
      expect(continuation?.title).toBe("Continuation Summary");
      expect(continuation?.updatedAt).toBe(updatedAt.toISOString());
    });
  });
});

// ----------------------------------------------------------------------------
// Verification harness: concrete before/after JSON.stringify(payload).length
// measurements for the CAR-381 implementation report. These tests only emit
// measurements via console.log; they are not assertions on behavior. Run
// vitest with --reporter=verbose to see the numbers.
// ----------------------------------------------------------------------------

function makeLockChild(i: number) {
  return { id: `child-${i}`, identifier: `LOCK-${100 + i}`, title: `Unblock child ${i}`, status: "done" };
}

function makeBlocker(i: number) {
  return { id: `blocker-${i}`, identifier: `PAP-380-${i}`, title: `Blocker ${i}`, status: "todo" };
}

function measureAfter(input: Parameters<typeof buildPaperclipWakePayload>[0]) {
  return buildPaperclipWakePayload(input).then((p) => JSON.stringify(p ?? {}).length);
}

function measureBefore(input: {
  contextSnapshot: Record<string, unknown>;
  continuationSummary?: { key: string; title: string; body: string; updatedAt: Date } | null;
}) {
  // Reconstruct what the payload would have been with NO size reduction.
  const ctx = input.contextSnapshot;
  const continuation = input.continuationSummary;
  const reconstructed = {
    issue: ISSUE_SUMMARY,
    wakeReason: ctx.wakeReason ?? null,
    continuationSummary: continuation
      ? {
          key: continuation.key,
          title: continuation.title,
          body: continuation.body,
          bodyTruncated: false,
          updatedAt: continuation.updatedAt,
        }
      : null,
    childIssueSummaries: (ctx.childIssueSummaries as unknown[] | undefined) ?? [],
    childIssueSummaryTruncated: false,
    unresolvedBlockerIssueIds: (ctx.unresolvedBlockerIssueIds as string[] | undefined) ?? [],
    unresolvedBlockerSummaries: (ctx.unresolvedBlockerSummaries as unknown[] | undefined) ?? [],
  };
  return JSON.stringify(reconstructed).length;
}

describe("CAR-381 wake-payload size — concrete before/after measurements", () => {
  it("shape 1 — live CAR-381 issue_commented wake (current state)", async () => {
    const ctx = {
      issueId: "issue-1",
      wakeReason: "issue_commented",
      childIssueSummaries: [],
      unresolvedBlockerIssueIds: [],
      unresolvedBlockerSummaries: [],
    };
    const before = measureBefore({ contextSnapshot: ctx });
    const after = await measureAfter({
      db: FAKE_DB,
      companyId: "company-1",
      contextSnapshot: ctx,
      issueSummary: ISSUE_SUMMARY,
    });
    const delta = before - after;
    const pct = ((delta / Math.max(before, 1)) * 100).toFixed(1);
    // eslint-disable-next-line no-console
    console.log(
      `[CAR-381/01 live issue_commented] before=${before} chars, after=${after} chars, delta=${delta} chars (${pct}%)`,
    );
    expect(after).toBeGreaterThan(0);
  });

  it("shape 2 — transient_failure_retry with 7 LOCK-* children + 3 blockers", async () => {
    const ctx = {
      issueId: "issue-1",
      wakeReason: "transient_failure_retry",
      childIssueSummaries: Array.from({ length: 7 }, (_, i) => makeLockChild(i)),
      childIssueSummaryTruncated: false,
      unresolvedBlockerIssueIds: ["blocker-0", "blocker-1", "blocker-2"],
      unresolvedBlockerSummaries: [makeBlocker(0), makeBlocker(1), makeBlocker(2)],
    };
    const before = measureBefore({ contextSnapshot: ctx });
    const after = await measureAfter({
      db: FAKE_DB,
      companyId: "company-1",
      contextSnapshot: ctx,
      issueSummary: ISSUE_SUMMARY,
    });
    const delta = before - after;
    const pct = ((delta / Math.max(before, 1)) * 100).toFixed(1);
    // eslint-disable-next-line no-console
    console.log(
      `[CAR-381/02 transient+7LOCK+3blockers] before=${before} chars, after=${after} chars, delta=${delta} chars (${pct}%)`,
    );
    expect(after).toBeLessThan(before);
  });

  it("shape 3 — long continuation summary (8KB) on ordinary wake", async () => {
    const longBody = makeLongContinuationSummary(8_000);
    const ctx = {
      issueId: "issue-1",
      wakeReason: "issue_assigned",
      childIssueSummaries: [],
      unresolvedBlockerIssueIds: [],
      unresolvedBlockerSummaries: [],
    };
    const before = measureBefore({
      contextSnapshot: ctx,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const after = await measureAfter({
      db: FAKE_DB,
      companyId: "company-1",
      contextSnapshot: ctx,
      issueSummary: ISSUE_SUMMARY,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const delta = before - after;
    const pct = ((delta / Math.max(before, 1)) * 100).toFixed(1);
    // eslint-disable-next-line no-console
    console.log(
      `[CAR-381/03 long-continuation-8KB] before=${before} chars, after=${after} chars, delta=${delta} chars (${pct}%)`,
    );
    expect(after).toBeLessThan(before);
  });

  it("shape 4 — worst case: transient_failure_retry + 7 children + 3 blockers + 8KB continuation", async () => {
    const longBody = makeLongContinuationSummary(8_000);
    const ctx = {
      issueId: "issue-1",
      wakeReason: "transient_failure_retry",
      childIssueSummaries: Array.from({ length: 7 }, (_, i) => makeLockChild(i)),
      childIssueSummaryTruncated: false,
      unresolvedBlockerIssueIds: ["blocker-0", "blocker-1", "blocker-2"],
      unresolvedBlockerSummaries: [makeBlocker(0), makeBlocker(1), makeBlocker(2)],
    };
    const before = measureBefore({
      contextSnapshot: ctx,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const after = await measureAfter({
      db: FAKE_DB,
      companyId: "company-1",
      contextSnapshot: ctx,
      issueSummary: ISSUE_SUMMARY,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const delta = before - after;
    const pct = ((delta / Math.max(before, 1)) * 100).toFixed(1);
    // eslint-disable-next-line no-console
    console.log(
      `[CAR-381/04 worst-case: transient+7LOCK+3blockers+8KB-continuation] before=${before} chars, after=${after} chars, delta=${delta} chars (${pct}%)`,
    );
    expect(after).toBeLessThan(before);
  });

  it("shape 5 — e718cd0d analogue: transient_failure_retry + 7 LOCK-* + 8KB continuation + 20KB padding", async () => {
    // Mirrors the originally failing run (e718cd0d-12a3-413b-8d09-a4e01c88fe02)
    // which produced the 'Prompt is too long' gate on claude_local. The
    // 20KB padding stands in for the long thread of comments captured in
    // contextSnapshot.padding.
    const longBody = makeLongContinuationSummary(8_000);
    const ctx = {
      issueId: "issue-1",
      wakeReason: "transient_failure_retry",
      childIssueSummaries: Array.from({ length: 7 }, (_, i) => makeLockChild(i)),
      childIssueSummaryTruncated: false,
      unresolvedBlockerIssueIds: ["blocker-0", "blocker-1", "blocker-2"],
      unresolvedBlockerSummaries: [makeBlocker(0), makeBlocker(1), makeBlocker(2)],
      padding: "P".repeat(20_000),
    };
    const before = measureBefore({
      contextSnapshot: ctx,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const after = await measureAfter({
      db: FAKE_DB,
      companyId: "company-1",
      contextSnapshot: ctx,
      issueSummary: ISSUE_SUMMARY,
      continuationSummary: {
        key: "continuation-summary",
        title: "Continuation Summary",
        body: longBody,
        updatedAt: new Date("2026-04-18T12:00:00.000Z"),
      },
    });
    const delta = before - after;
    const pct = ((delta / Math.max(before, 1)) * 100).toFixed(1);
    // Rough token-cost heuristic: ~4 chars/token for English markdown.
    const beforeTokens = Math.round(before / 4);
    const afterTokens = Math.round(after / 4);
    // eslint-disable-next-line no-console
    console.log(
      `[CAR-381/05 e718cd0d analogue] before=${before} chars (~${beforeTokens} tokens), after=${after} chars (~${afterTokens} tokens), delta=${delta} chars (${pct}%)`,
    );
    expect(after).toBeLessThan(before);
    // Confirm the after size is comfortably below a typical 200K-token prompt
    // window even with worst-case padding included.
    expect(after).toBeLessThan(50_000);
  });
});
