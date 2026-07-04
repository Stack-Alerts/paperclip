import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import {
  activityLog,
  agentRuntimeState,
  agentTaskSessions,
  agents,
  companies,
  createDb,
  projects,
  projectWorkspaces,
} from "@paperclipai/db";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "./helpers/embedded-postgres.js";
import {
  preflightAgentSessionResume,
  sweepAgentSessionPointers,
} from "../services/agent-session-coherence.ts";
import { encodeClaudeProjectDirSegment } from "../services/claude-local-session.ts";

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

if (!embeddedPostgresSupport.supported) {
  console.warn(
    `Skipping embedded Postgres coherence tests on this host: ${embeddedPostgresSupport.reason ?? "unsupported environment"}`,
  );
}

describeEmbeddedPostgres("agent-session-coherence", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;
  let tempRoot: string | null = null;
  let companyId: string;
  let projectId: string;
  let projectWorkspaceId: string;
  const previousClaudeConfigDir = process.env.CLAUDE_CONFIG_DIR;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-agent-session-coherence-");
    db = createDb(tempDb.connectionString);

    tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-coherence-"));
    process.env.CLAUDE_CONFIG_DIR = tempRoot;

    companyId = randomUUID();
    projectId = randomUUID();
    projectWorkspaceId = randomUUID();
    const workspaceCwd = `/home/sirrus/projects/repo-${projectWorkspaceId.slice(0, 8)}`;

    await db.insert(companies).values({
      id: companyId,
      name: "Coherence Test Co",
      issuePrefix: `COH${companyId.replace(/-/g, "").slice(0, 4).toUpperCase()}`,
    });
    await db.insert(projects).values({
      id: projectId,
      companyId,
      name: "Coherence Test Project",
      status: "active",
    });
    await db.insert(projectWorkspaces).values({
      id: projectWorkspaceId,
      companyId,
      projectId,
      name: "primary",
      cwd: workspaceCwd,
      isPrimary: true,
    });
  }, 20_000);

  beforeEach(async () => {
    // Clean state between tests; structure persists across tests.
    // Delete order respects FKs (activity_log -> agents).
    await db.delete(activityLog).where(eq(activityLog.companyId, companyId));
    await db.delete(agentTaskSessions).where(eq(agentTaskSessions.companyId, companyId));
    await db.delete(agentRuntimeState).where(eq(agentRuntimeState.companyId, companyId));
    await db.delete(agents).where(eq(agents.companyId, companyId));
    if (tempRoot) {
      await fs.rm(tempRoot, { recursive: true, force: true });
      tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-coherence-"));
      // Keep the env var in sync with the latest tempRoot so
      // resolveSharedClaudeConfigDir() picks up the new directory.
      process.env.CLAUDE_CONFIG_DIR = tempRoot;
    }
  });

  afterAll(async () => {
    if (previousClaudeConfigDir === undefined) delete process.env.CLAUDE_CONFIG_DIR;
    else process.env.CLAUDE_CONFIG_DIR = previousClaudeConfigDir;
    if (tempRoot) await fs.rm(tempRoot, { recursive: true, force: true });
    // Delete order respects FKs (activity_log -> agents).
    await db.delete(activityLog).where(eq(activityLog.companyId, companyId));
    await db.delete(agentTaskSessions).where(eq(agentTaskSessions.companyId, companyId));
    await db.delete(agentRuntimeState).where(eq(agentRuntimeState.companyId, companyId));
    await db.delete(agents).where(eq(agents.companyId, companyId));
    await db.delete(projectWorkspaces).where(eq(projectWorkspaces.companyId, companyId));
    await db.delete(projects).where(eq(projects.companyId, companyId));
    await db.delete(companies).where(eq(companies.id, companyId));
    await tempDb?.cleanup();
  });

  async function insertAgent(opts: { adapterType: string; name: string }) {
    const id = randomUUID();
    await db.insert(agents).values({
      id,
      companyId,
      name: opts.name,
      role: "engineer",
      status: "running",
      adapterType: opts.adapterType,
      adapterConfig: {},
      runtimeConfig: {},
      permissions: {},
    });
    return id;
  }

  async function insertRuntimeState(agentId: string, sessionId: string | null) {
    await db.insert(agentRuntimeState).values({
      agentId,
      companyId,
      adapterType: "claude_local",
      sessionId,
      stateJson: {},
    });
  }

  async function insertTaskSession(agentId: string, sessionParamsJson: Record<string, unknown>) {
    const id = randomUUID();
    await db.insert(agentTaskSessions).values({
      id,
      companyId,
      agentId,
      adapterType: "claude_local",
      taskKey: `task-${id}`,
      sessionParamsJson,
    });
    return id;
  }

  async function touchSessionFile(cwd: string, sessionId: string): Promise<void> {
    const target = path.join(
      tempRoot!,
      "projects",
      encodeClaudeProjectDirSegment(cwd),
      `${sessionId}.jsonl`,
    );
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, "{}", "utf8");
  }

  async function readActivityLogCount(reason: string): Promise<number> {
    const rows = await db
      .select({ id: activityLog.id, details: activityLog.details })
      .from(activityLog)
      .where(eq(activityLog.companyId, companyId));
    return rows.filter((row) => {
      const details = row.details && typeof row.details === "object"
        ? (row.details as Record<string, unknown>)
        : null;
      return details?.reason === reason;
    }).length;
  }

  describe("preflightAgentSessionResume", () => {
    it("returns resume when the session file exists on disk", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "Alpha" });
      const cwd = `/home/sirrus/projects/repo-${randomUUID().slice(0, 6)}`;
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      await insertTaskSession(agentId, { cwd, sessionId });
      await touchSessionFile(cwd, sessionId);

      const outcome = await preflightAgentSessionResume(db, agentId);

      expect(outcome).toEqual({ kind: "resume", sessionId });
    });

    it("clears the runtime session pointer and writes an activity log entry when the file is gone", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "Bravo" });
      const cwd = `/home/sirrus/projects/repo-${randomUUID().slice(0, 6)}`;
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      await insertTaskSession(agentId, { cwd, sessionId });
      // Note: no touchSessionFile call.

      const outcome = await preflightAgentSessionResume(db, agentId);

      expect(outcome).toEqual({ kind: "fresh" });

      const [runtime] = await db
        .select({ sessionId: agentRuntimeState.sessionId, stateJson: agentRuntimeState.stateJson })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, agentId))
        .limit(1);
      expect(runtime?.sessionId).toBeNull();
      const stateJson = (runtime?.stateJson ?? {}) as Record<string, unknown>;
      const health = stateJson.sessionHealth as Record<string, unknown> | undefined;
      expect(health?.lastOutcome).toBe("missing");
      expect(health?.lastKnownSessionId).toBe(sessionId);
      expect(typeof health?.lastCheckedAt).toBe("string");

      const logCount = await readActivityLogCount("preflight_missing_session_file");
      expect(logCount).toBe(1);
    });

    it("returns fresh when runtime sessionId is null (no work to do)", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "Charlie" });
      await insertRuntimeState(agentId, null);

      const outcome = await preflightAgentSessionResume(db, agentId);

      expect(outcome).toEqual({ kind: "fresh" });
    });

    it("returns skipped for non-claude_local adapters", async () => {
      const agentId = await insertAgent({ adapterType: "codex_local", name: "Delta" });
      await insertRuntimeState(agentId, randomUUID());

      const outcome = await preflightAgentSessionResume(db, agentId);

      expect(outcome).toEqual({ kind: "skipped", reason: "adapter_type_unsupported" });
    });

    it("falls back to agent_home when the agent has no task session cwd", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "Echo" });
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      // No task session, no on-disk file under agent_home. Should report missing
      // and clear the pointer.
      const outcome = await preflightAgentSessionResume(db, agentId);

      expect(outcome).toEqual({ kind: "fresh" });
      const [runtime] = await db
        .select({ sessionId: agentRuntimeState.sessionId })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, agentId))
        .limit(1);
      expect(runtime?.sessionId).toBeNull();
    });
  });

  describe("sweepAgentSessionPointers", () => {
    it("clears stale pointers and skips fresh ones", async () => {
      const freshAgentId = await insertAgent({ adapterType: "claude_local", name: "Fresh" });
      const staleAgentId = await insertAgent({ adapterType: "claude_local", name: "Stale" });

      const freshCwd = `/home/sirrus/projects/fresh-${randomUUID().slice(0, 6)}`;
      const freshSession = randomUUID();
      const staleCwd = `/home/sirrus/projects/stale-${randomUUID().slice(0, 6)}`;
      const staleSession = randomUUID();

      await insertRuntimeState(freshAgentId, freshSession);
      await insertTaskSession(freshAgentId, { cwd: freshCwd, sessionId: freshSession });
      await touchSessionFile(freshCwd, freshSession);

      await insertRuntimeState(staleAgentId, staleSession);
      await insertTaskSession(staleAgentId, { cwd: staleCwd, sessionId: staleSession });
      // No file for stale agent.

      // A non-claude agent must be ignored entirely.
      const otherAgentId = await insertAgent({ adapterType: "codex_local", name: "OtherAdapter" });
      await insertRuntimeState(otherAgentId, randomUUID());

      const result = await sweepAgentSessionPointers(db);

      expect(result.checked).toBe(2); // fresh + stale (other adapter excluded)
      expect(result.cleared).toBe(1); // only stale

      const [freshRuntime] = await db
        .select({ sessionId: agentRuntimeState.sessionId })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, freshAgentId))
        .limit(1);
      expect(freshRuntime?.sessionId).toBe(freshSession);

      const [staleRuntime] = await db
        .select({
          sessionId: agentRuntimeState.sessionId,
          stateJson: agentRuntimeState.stateJson,
        })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, staleAgentId))
        .limit(1);
      expect(staleRuntime?.sessionId).toBeNull();
      const health = ((staleRuntime?.stateJson ?? {}) as Record<string, unknown>)
        .sessionHealth as Record<string, unknown>;
      expect(health?.lastOutcome).toBe("missing");

      const logCount = await readActivityLogCount("sweeper_detected_missing_session");
      expect(logCount).toBe(1);
    });

    it("skips re-checking agents within the recheck floor", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "RateLimit" });
      const cwd = `/home/sirrus/projects/ratelimit-${randomUUID().slice(0, 6)}`;
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      await insertTaskSession(agentId, { cwd, sessionId });
      await touchSessionFile(cwd, sessionId);

      const first = await sweepAgentSessionPointers(db);
      const second = await sweepAgentSessionPointers(db);

      expect(first.checked).toBe(1);
      expect(second.checked).toBe(1);
      expect(second.cleared).toBe(0);
    });

    it("the preflight's ok path clears staleSince once the session file is back", async () => {
      // The sweeper drops cleared agents from its candidate set, so the
      // "recovery" path is exercised by the preflight when a subsequent
      // manual/automation wake brings the session back. This test verifies
      // that preflight re-establishes ok state when the file is present.
      const agentId = await insertAgent({ adapterType: "claude_local", name: "PreflightRecovery" });
      const cwd = `/home/sirrus/projects/recovery-${randomUUID().slice(0, 6)}`;
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      await insertTaskSession(agentId, { cwd, sessionId });

      // First preflight: file missing → clears pointer and records staleness.
      const cleared = await preflightAgentSessionResume(db, agentId);
      expect(cleared).toEqual({ kind: "fresh" });

      // Restore the runtime pointer + touch the file (simulates a fresh run
      // establishing a session that happens to share the previous id).
      await db
        .update(agentRuntimeState)
        .set({ sessionId })
        .where(eq(agentRuntimeState.agentId, agentId));
      await touchSessionFile(cwd, sessionId);

      // Bump the recheck floor so the next preflight doesn't skip.
      const pastIso = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      const [existing] = await db
        .select({ stateJson: agentRuntimeState.stateJson })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, agentId))
        .limit(1);
      const seededStateJson = {
        ...((existing?.stateJson ?? {}) as Record<string, unknown>),
        sessionHealth: {
          ...(((existing?.stateJson ?? {}) as Record<string, unknown>).sessionHealth as Record<string, unknown> ?? {}),
          lastCheckedAt: pastIso,
        },
      };
      await db
        .update(agentRuntimeState)
        .set({ stateJson: seededStateJson })
        .where(eq(agentRuntimeState.agentId, agentId));

      const resumed = await preflightAgentSessionResume(db, agentId);
      expect(resumed).toEqual({ kind: "resume", sessionId });

      const [runtime] = await db
        .select({ stateJson: agentRuntimeState.stateJson, sessionId: agentRuntimeState.sessionId })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, agentId))
        .limit(1);
      expect(runtime?.sessionId).toBe(sessionId);
      const health = ((runtime?.stateJson ?? {}) as Record<string, unknown>)
        .sessionHealth as Record<string, unknown>;
      expect(health?.lastOutcome).toBe("ok");
      expect(health?.staleSince ?? null).toBeNull();
    });

    it("uses the latest task session cwd when runtime_state has no cwd", async () => {
      const agentId = await insertAgent({ adapterType: "claude_local", name: "LatestCwd" });
      const cwd = `/home/sirrus/projects/latestcwd-${randomUUID().slice(0, 6)}`;
      const sessionId = randomUUID();
      await insertRuntimeState(agentId, sessionId);
      await insertTaskSession(agentId, { cwd, sessionId });
      await touchSessionFile(cwd, sessionId);

      const result = await sweepAgentSessionPointers(db);

      expect(result.checked).toBe(1);
      expect(result.cleared).toBe(0);
      const [runtime] = await db
        .select({ stateJson: agentRuntimeState.stateJson })
        .from(agentRuntimeState)
        .where(eq(agentRuntimeState.agentId, agentId))
        .limit(1);
      const health = ((runtime?.stateJson ?? {}) as Record<string, unknown>)
        .sessionHealth as Record<string, unknown>;
      expect(health?.lastOutcome).toBe("ok");
      expect(health?.lastKnownSessionId).toBe(sessionId);
    });
  });
});