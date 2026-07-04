import { and, desc, eq, isNotNull } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { agentRuntimeState, agentTaskSessions, agents } from "@paperclipai/db";
import { claudeLocalSessionFilePath, isClaudeLocalSessionFileMissing } from "./claude-local-session.js";
import { logActivity } from "./activity-log.js";
import { resolveDefaultAgentWorkspaceDir } from "../home-paths.js";

const CLAUDE_LOCAL_ADAPTER_TYPE = "claude_local";
const AGENT_SESSION_HEALTH_KEY = "sessionHealth";
const SESSION_HEALTH_STALE_GRACE_MS = 60 * 60 * 1000;
const SESSION_HEALTH_RECHECK_FLOOR_MS = 60 * 1000;

type SessionHealthState = {
  lastCheckedAt?: string;
  lastKnownSessionId?: string | null;
  staleSince?: string | null;
  lastClearedAt?: string | null;
  lastOutcome?: "ok" | "missing" | "error";
  lastError?: string | null;
};

function readSessionHealth(stateJson: Record<string, unknown>): SessionHealthState {
  const value = stateJson[AGENT_SESSION_HEALTH_KEY];
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as SessionHealthState;
}

function shouldSkipAgentForRateLimit(input: {
  nowMs: number;
  health: SessionHealthState;
  candidateSessionId: string | null;
}): boolean {
  if (!input.health.lastCheckedAt) return false;
  const last = Date.parse(input.health.lastCheckedAt);
  if (!Number.isFinite(last)) return false;
  if (input.nowMs - last < SESSION_HEALTH_RECHECK_FLOOR_MS) {
    if (input.health.lastKnownSessionId === input.candidateSessionId) return true;
  }
  if (input.health.staleSince) {
    const stale = Date.parse(input.health.staleSince);
    if (Number.isFinite(stale) && input.nowMs - stale < SESSION_HEALTH_STALE_GRACE_MS) {
      return true;
    }
  }
  return false;
}

async function readLatestTaskSessionCwd(
  db: Db,
  agentId: string,
): Promise<string | null> {
  const [row] = await db
    .select({ sessionParamsJson: agentTaskSessions.sessionParamsJson })
    .from(agentTaskSessions)
    .where(eq(agentTaskSessions.agentId, agentId))
    .orderBy(desc(agentTaskSessions.updatedAt), desc(agentTaskSessions.createdAt))
    .limit(1);
  if (!row) return null;
  const params = row.sessionParamsJson && typeof row.sessionParamsJson === "object" && !Array.isArray(row.sessionParamsJson)
    ? (row.sessionParamsJson as Record<string, unknown>)
    : null;
  const cwd = params ? params.cwd : null;
  return typeof cwd === "string" && cwd.trim().length > 0 ? cwd.trim() : null;
}

async function readCwdForAgent(db: Db, agentId: string): Promise<string> {
  const fromTaskSession = await readLatestTaskSessionCwd(db, agentId);
  if (fromTaskSession) return fromTaskSession;
  return resolveDefaultAgentWorkspaceDir(agentId);
}

export type PreflightAgentSessionResumeOutcome =
  | { kind: "resume"; sessionId: string }
  | { kind: "fresh" }
  | { kind: "skipped"; reason: "adapter_type_unsupported" | "runtime_state_missing" };

/**
 * Verifies that the agent's runtime_state.session_id is still backed by a
 * real on-disk session file before we hand it to the claude_local adapter as
 * a resume target. When the file is gone, this clears the runtime pointer
 * (and writes an activity-log entry) so the next run starts fresh instead of
 * paying for one failed resume + retry per wake.
 *
 * Safe to call on every heartbeat wake. Cheap when nothing changed (one DB
 * select + one early return). Falls back to "not cleared" on stat errors so a
 * transient fs problem doesn't wipe a valid pointer.
 */
export async function preflightAgentSessionResume(
  db: Db,
  agentId: string,
): Promise<PreflightAgentSessionResumeOutcome> {
  const [agent] = await db
    .select({ id: agents.id, companyId: agents.companyId, adapterType: agents.adapterType })
    .from(agents)
    .where(eq(agents.id, agentId))
    .limit(1);
  if (!agent) return { kind: "skipped", reason: "runtime_state_missing" };
  if (agent.adapterType !== CLAUDE_LOCAL_ADAPTER_TYPE) {
    return { kind: "skipped", reason: "adapter_type_unsupported" };
  }

  const [runtime] = await db
    .select({
      sessionId: agentRuntimeState.sessionId,
      companyId: agentRuntimeState.companyId,
      stateJson: agentRuntimeState.stateJson,
    })
    .from(agentRuntimeState)
    .where(eq(agentRuntimeState.agentId, agentId))
    .limit(1);
  if (!runtime) return { kind: "skipped", reason: "runtime_state_missing" };

  const sessionId = typeof runtime.sessionId === "string" && runtime.sessionId.trim().length > 0
    ? runtime.sessionId.trim()
    : null;
  if (!sessionId) return { kind: "fresh" };

  const cwd = await readCwdForAgent(db, agentId);
  const missing = await isClaudeLocalSessionFileMissing({ cwd, sessionId });
  if (!missing) {
    const priorHealth = readSessionHealth(runtime.stateJson ?? {});
    await persistSessionHealth(db, agentId, runtime.stateJson ?? {}, {
      lastCheckedAt: new Date().toISOString(),
      lastKnownSessionId: sessionId,
      lastOutcome: "ok",
      lastError: null,
      ...(priorHealth.staleSince ? { staleSince: null, lastClearedAt: null } : {}),
    });
    return { kind: "resume", sessionId };
  }

  await db
    .update(agentRuntimeState)
    .set({
      sessionId: null,
      stateJson: withSessionHealth(runtime.stateJson ?? {}, {
        lastCheckedAt: new Date().toISOString(),
        lastKnownSessionId: sessionId,
        staleSince: new Date().toISOString(),
        lastClearedAt: new Date().toISOString(),
        lastOutcome: "missing",
        lastError: null,
      }),
      updatedAt: new Date(),
    })
    .where(eq(agentRuntimeState.agentId, agentId));

  await logActivity(db, {
    companyId: runtime.companyId ?? agent.companyId,
    actorType: "system",
    actorId: "system",
    agentId,
    runId: null,
    action: "claude_local.session_pointer_cleared",
    entityType: "agent",
    entityId: agentId,
    details: {
      reason: "preflight_missing_session_file",
      clearedSessionId: sessionId,
      expectedPath: claudeLocalSessionPathForLog({ cwd, sessionId }),
      cwd,
    },
  });

  return { kind: "fresh" };
}

export type SweepAgentSessionPointersResult = {
  checked: number;
  cleared: number;
  alreadyStale: number;
  errors: number;
};

export async function sweepAgentSessionPointers(
  db: Db,
  opts: { now?: Date } = {},
): Promise<SweepAgentSessionPointersResult> {
  const result: SweepAgentSessionPointersResult = {
    checked: 0,
    cleared: 0,
    alreadyStale: 0,
    errors: 0,
  };
  const now = opts.now ?? new Date();
  const nowMs = now.getTime();

  const candidates = await db
    .select({
      agentId: agentRuntimeState.agentId,
      companyId: agentRuntimeState.companyId,
      sessionId: agentRuntimeState.sessionId,
      stateJson: agentRuntimeState.stateJson,
      adapterType: agents.adapterType,
    })
    .from(agentRuntimeState)
    .innerJoin(agents, eq(agents.id, agentRuntimeState.agentId))
    .where(
      and(
        eq(agents.adapterType, CLAUDE_LOCAL_ADAPTER_TYPE),
        isNotNull(agentRuntimeState.sessionId),
      ),
    );

  for (const row of candidates) {
    result.checked += 1;
    const sessionId = typeof row.sessionId === "string" && row.sessionId.trim().length > 0
      ? row.sessionId.trim()
      : null;
    if (!sessionId) continue;

    const cwd = await readCwdForAgent(db, row.agentId);
    const health = readSessionHealth(row.stateJson ?? {});
    if (shouldSkipAgentForRateLimit({ nowMs, health, candidateSessionId: sessionId })) {
      if (health.staleSince) result.alreadyStale += 1;
      continue;
    }

    let missing = false;
    try {
      missing = await isClaudeLocalSessionFileMissing({ cwd, sessionId });
    } catch (err) {
      result.errors += 1;
      await persistSessionHealth(db, row.agentId, row.stateJson ?? {}, {
        lastCheckedAt: now.toISOString(),
        lastKnownSessionId: sessionId,
        lastOutcome: "error",
        lastError: err instanceof Error ? err.message : String(err),
      });
      continue;
    }

    if (!missing) {
      await persistSessionHealth(db, row.agentId, row.stateJson ?? {}, {
        lastCheckedAt: now.toISOString(),
        lastKnownSessionId: sessionId,
        lastOutcome: "ok",
        lastError: null,
        ...(health.staleSince ? { staleSince: null } : {}),
        ...(health.staleSince ? { lastClearedAt: null } : {}),
      });
      continue;
    }

    result.cleared += 1;
    const nowIso = now.toISOString();
    await db
      .update(agentRuntimeState)
      .set({
        sessionId: null,
        stateJson: withSessionHealth(row.stateJson ?? {}, {
          lastCheckedAt: nowIso,
          lastKnownSessionId: sessionId,
          staleSince: health.staleSince ?? nowIso,
          lastClearedAt: nowIso,
          lastOutcome: "missing",
          lastError: null,
        }),
        updatedAt: now,
      })
      .where(eq(agentRuntimeState.agentId, row.agentId));

    await logActivity(db, {
      companyId: row.companyId,
      actorType: "system",
      actorId: "system",
      agentId: row.agentId,
      runId: null,
      action: "claude_local.session_pointer_cleared",
      entityType: "agent",
      entityId: row.agentId,
      details: {
        reason: health.staleSince ? "sweeper_redetected_missing_session" : "sweeper_detected_missing_session",
        clearedSessionId: sessionId,
        expectedPath: claudeLocalSessionPathForLog({ cwd, sessionId }),
        cwd,
      },
    });
  }

  return result;
}

function claudeLocalSessionPathForLog(input: { cwd: string; sessionId: string }): string {
  return claudeLocalSessionFilePath(input);
}

async function persistSessionHealth(
  db: Db,
  agentId: string,
  currentStateJson: Record<string, unknown>,
  patch: SessionHealthState,
): Promise<void> {
  const merged = withSessionHealth(currentStateJson, patch);
  await db
    .update(agentRuntimeState)
    .set({ stateJson: merged, updatedAt: new Date() })
    .where(eq(agentRuntimeState.agentId, agentId));
}

function withSessionHealth(
  stateJson: Record<string, unknown>,
  patch: SessionHealthState,
): Record<string, unknown> {
  const existing = readSessionHealth(stateJson);
  return {
    ...stateJson,
    [AGENT_SESSION_HEALTH_KEY]: { ...existing, ...patch },
  };
}