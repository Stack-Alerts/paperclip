import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import {
  agents,
  companies,
  createDb,
  executionWorkspaces,
  issueComments,
  issueRecoveryActions,
  issues,
  projectWorkspaces,
  projects,
} from "@paperclipai/db";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "./helpers/embedded-postgres.js";

const mockTelemetryClient = vi.hoisted(() => ({ track: vi.fn() }));
vi.mock("../telemetry.ts", () => ({ getTelemetryClient: () => mockTelemetryClient }));

const mockFs = vi.hoisted(() => ({
  lstat: vi.fn(),
  stat: vi.fn(),
  mkdir: vi.fn(),
  rm: vi.fn(),
  readdir: vi.fn(),
}));
vi.mock("node:fs/promises", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:fs/promises")>();
  return { ...actual, default: { ...actual, ...mockFs } };
});

const mockExecFile = vi.hoisted(() => vi.fn());
vi.mock("node:child_process", () => ({ execFile: mockExecFile }));
vi.mock("node:util", () => ({ promisify: (fn: unknown) => fn }));

vi.mock("../home-paths.ts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../home-paths.ts")>();
  return {
    ...actual,
    resolveManagedProjectWorkspaceDir: (input: {
      companyId: string;
      projectId: string;
      repoName?: string | null;
    }) =>
      `/tmp/paperclip-test/projects/${input.companyId}/${input.projectId}/${input.repoName ?? "_default"}`,
  };
});

vi.mock("../middleware/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { heartbeatService } from "../services/heartbeat.ts";

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

if (!embeddedPostgresSupport.supported) {
  console.warn(
    `Skipping embedded Postgres workspace self-heal orchestration tests on this host: ${
      embeddedPostgresSupport.reason ?? "unsupported environment"
    }`,
  );
}

describeEmbeddedPostgres("heartbeat reconcileWorkspaceValidationFailures orchestration", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-workspace-self-heal-");
    db = createDb(tempDb.connectionString);
  }, 20_000);

  afterEach(async () => {
    await db.delete(issueComments);
    await db.delete(issueRecoveryActions);
    await db.delete(executionWorkspaces);
    await db.delete(projectWorkspaces);
    await db.delete(issues);
    await db.delete(projects);
    await db.delete(agents);
    await db.delete(companies);
    mockFs.lstat.mockReset();
    mockFs.stat.mockReset();
    mockExecFile.mockReset();
    mockFs.mkdir.mockReset();
    mockFs.rm.mockReset();
    mockFs.readdir.mockReset();
  });

  afterAll(async () => {
    await tempDb?.cleanup();
  });

  const dirStat = () =>
    Promise.resolve({
      isDirectory: () => true,
      isFile: () => false,
    }) as unknown as Promise<import("node:fs").Stats>;

  const enoent = () =>
    Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" }));

  const okStat = () =>
    Promise.resolve({
      isDirectory: () => true,
      isFile: () => false,
    }) as unknown as Promise<import("node:fs").Stats>;

  type SeedOptions = {
    companyIndex: number;
    assigneeAgentStatus?: "idle" | "error";
    previousOwnerAgentId?: string | null;
    projectCwd?: string;
    executionCwd?: string;
    repoUrl?: string | null;
  };

  async function seedCompanyAndIssue(opts: SeedOptions) {
    const companyId = randomUUID();
    const projectId = randomUUID();
    const projectWorkspaceId = randomUUID();
    const issueId = randomUUID();
    const assigneeAgentId = randomUUID();
    const previousOwnerAgentId = opts.previousOwnerAgentId ?? null;
    const projectCwd = opts.projectCwd ?? `/tmp/paperclip-test/cwds/${randomUUID()}`;
    const executionCwd = opts.executionCwd ?? `/tmp/paperclip-test/cwds/${randomUUID()}`;
    const repoUrl = opts.repoUrl ?? "https://example.com/repo.git";

    await db.insert(companies).values({
      id: companyId,
      name: `Paperclip-${opts.companyIndex}`,
      issuePrefix: `T${companyIndex(companyId)}`,
      requireBoardApprovalForNewAgents: false,
    });
    await db.insert(projects).values({
      id: projectId,
      companyId,
      name: `Project ${opts.companyIndex}`,
      status: "active",
    });
    await db.insert(projectWorkspaces).values({
      id: projectWorkspaceId,
      companyId,
      projectId,
      name: `pw-${opts.companyIndex}`,
      sourceType: "git_clone",
      cwd: projectCwd,
      repoUrl,
      repoRef: null,
      defaultRef: "main",
      isPrimary: true,
    });
    await db.insert(agents).values({
      id: assigneeAgentId,
      companyId,
      name: `Assignee ${opts.companyIndex}`,
      role: "engineer",
      status: opts.assigneeAgentStatus ?? "idle",
      adapterType: "codex_local",
      adapterConfig: {},
      runtimeConfig: {},
      permissions: {},
      errorReason: opts.assigneeAgentStatus === "error" ? "previous failure" : null,
    });
    if (previousOwnerAgentId) {
      await db.insert(agents).values({
        id: previousOwnerAgentId,
        companyId,
        name: `Previous ${opts.companyIndex}`,
        role: "engineer",
        status: "error",
        adapterType: "codex_local",
        adapterConfig: {},
        runtimeConfig: {},
        permissions: {},
        errorReason: "previous owner failure",
      });
    }
    await db.insert(issues).values({
      id: issueId,
      companyId,
      projectId,
      projectWorkspaceId,
      identifier: `T-${opts.companyIndex}`,
      title: `Workspace blocked ${opts.companyIndex}`,
      status: "blocked",
      priority: "high",
      assigneeAgentId,
    });
    await db.insert(executionWorkspaces).values({
      id: randomUUID(),
      companyId,
      projectId,
      projectWorkspaceId,
      sourceIssueId: issueId,
      mode: "worktree",
      strategyType: "project_primary",
      name: `exec-${opts.companyIndex}`,
      status: "active",
      cwd: executionCwd,
      repoUrl,
      metadata: {},
    });

    return {
      companyId,
      projectId,
      projectWorkspaceId,
      issueId,
      assigneeAgentId,
      previousOwnerAgentId,
      projectCwd,
      executionCwd,
      repoUrl,
    };
  }

  function companyIndex(id: string): string {
    return id.replace(/-/g, "").slice(0, 6).toUpperCase();
  }

  it("returns zeros when there are no workspace_validation_failed candidates", async () => {
    const heartbeat = heartbeatService(db);
    const result = await heartbeat.reconcileWorkspaceValidationFailures();
    expect(result).toEqual({
      scanned: 0,
      repaired: 0,
      skipped: 0,
      failed: 0,
      repairedIssueIds: [],
      skippedIssueIds: [],
      failedIssueIds: [],
    });
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.rm).not.toHaveBeenCalled();
  });

  it("skips issues whose cwd already has .git and writes nothing", async () => {
    const seeded = await seedCompanyAndIssue({ companyIndex: 1 });
    await db.insert(issueRecoveryActions).values({
      companyId: seeded.companyId,
      sourceIssueId: seeded.issueId,
      kind: "workspace_validation",
      status: "active",
      cause: "workspace_validation_failed",
      fingerprint: `fp-${seeded.issueId}`,
      evidence: {
        executionWorkspaceCwd: seeded.executionCwd,
        resolvedProjectWorkspaceId: seeded.projectWorkspaceId,
      },
      ownerAgentId: seeded.assigneeAgentId,
      nextAction: "restore cwd",
      attemptCount: 1,
    });

    mockFs.lstat.mockImplementation(() => dirStat());
    mockFs.stat.mockImplementation(() => okStat());

    const heartbeat = heartbeatService(db);
    const result = await heartbeat.reconcileWorkspaceValidationFailures();

    expect(result.scanned).toBe(1);
    expect(result.repaired).toBe(0);
    expect(result.skipped).toBe(1);
    expect(result.failed).toBe(0);
    expect(result.skippedIssueIds).toEqual([seeded.issueId]);
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.rm).not.toHaveBeenCalled();

    const recoveryRow = await db
      .select()
      .from(issueRecoveryActions)
      .where(eq(issueRecoveryActions.sourceIssueId, seeded.issueId))
      .then((rows) => rows[0]);
    expect(recoveryRow?.status).toBe("active");
    expect(recoveryRow?.outcome).toBeNull();

    const comments = await db
      .select()
      .from(issueComments)
      .where(eq(issueComments.issueId, seeded.issueId));
    expect(comments).toHaveLength(0);
  });

  it("repairs the cwd, persists workspaceRealization metadata, clears errors, and resolves the action", async () => {
    const previousOwnerAgentId = randomUUID();
    const seeded = await seedCompanyAndIssue({
      companyIndex: 2,
      assigneeAgentStatus: "error",
      previousOwnerAgentId,
    });
    await db.insert(issueRecoveryActions).values({
      companyId: seeded.companyId,
      sourceIssueId: seeded.issueId,
      kind: "workspace_validation",
      status: "active",
      cause: "workspace_validation_failed",
      fingerprint: `fp-${seeded.issueId}`,
      evidence: {
        executionWorkspaceCwd: seeded.executionCwd,
        resolvedProjectWorkspaceId: seeded.projectWorkspaceId,
        previousOwnerAgentId,
      },
      ownerAgentId: seeded.assigneeAgentId,
      nextAction: "restore cwd",
      attemptCount: 1,
    });

    const managed = `/tmp/paperclip-test/projects/${seeded.companyId}/${seeded.projectId}/repo`;
    const symlinkedCwds = new Set<string>();
    const resolveMockPath = (p: string) => {
      for (const symlinked of symlinkedCwds) {
        if (p === symlinked) return managed;
        if (p.startsWith(`${symlinked}/`)) return `${managed}${p.slice(symlinked.length)}`;
      }
      return p;
    };
    mockFs.stat.mockImplementation((p: string) => {
      if (resolveMockPath(p) === managed) return okStat();
      return enoent();
    });
    mockFs.lstat.mockImplementation((p: string) => {
      if (symlinkedCwds.has(p)) {
        return Promise.resolve({
          isSymbolicLink: () => true,
          isDirectory: () => false,
          isFile: () => false,
        } as unknown as import("node:fs").Stats);
      }
      if (resolveMockPath(p) === `${managed}/.git`) return dirStat();
      return enoent();
    });
    mockFs.readdir.mockImplementation((p: string) => {
      if (resolveMockPath(p) === managed) {
        return Promise.resolve([".git"] as unknown as string[]);
      }
      return Promise.resolve([] as unknown as string[]);
    });
    mockFs.mkdir.mockImplementation(() => Promise.resolve());
    mockExecFile.mockImplementation((_cmd: string, args: string[]) => {
      const target = args[args.length - 1];
      if (typeof target === "string") symlinkedCwds.add(target);
      return Promise.resolve({ stdout: "", stderr: "" });
    });

    const heartbeat = heartbeatService(db);
    const result = await heartbeat.reconcileWorkspaceValidationFailures();

    expect(result.scanned).toBe(1);
    expect(result.repaired).toBe(1);
    expect(result.failed).toBe(0);
    expect(result.repairedIssueIds).toEqual([seeded.issueId]);
    expect(mockFs.rm).not.toHaveBeenCalled();
    expect(mockExecFile).toHaveBeenCalledTimes(2);
    expect(mockExecFile.mock.calls[0]?.[0]).toBe("ln");
    expect(mockExecFile.mock.calls[0]?.[1]).toEqual(["-snf", managed, seeded.projectCwd]);
    expect(mockExecFile.mock.calls[1]?.[0]).toBe("ln");
    expect(mockExecFile.mock.calls[1]?.[1]).toEqual(["-snf", managed, seeded.executionCwd]);

    const projectRows = await db
      .select({ cwd: projectWorkspaces.cwd })
      .from(projectWorkspaces)
      .where(eq(projectWorkspaces.id, seeded.projectWorkspaceId));
    expect(projectRows[0]?.cwd).toBe(managed);

    const execRows = await db
      .select()
      .from(executionWorkspaces)
      .where(
        and(
          eq(executionWorkspaces.companyId, seeded.companyId),
          eq(executionWorkspaces.sourceIssueId, seeded.issueId),
        ),
      );
    expect(execRows).toHaveLength(1);
    const exec = execRows[0]!;
    expect(exec.cwd).toBe(managed);
    const metadata = exec.metadata as Record<string, unknown>;
    const realization = metadata.workspaceRealization as {
      local: Record<string, unknown>;
    };
    expect(realization.local.strategy).toBe("project_primary");
    expect(realization.local.projectId).toBe(seeded.projectId);
    expect(realization.local.projectWorkspaceId).toBe(seeded.projectWorkspaceId);
    expect(realization.local.repoUrl).toBe(seeded.repoUrl);
    expect(realization.local.restoredVia).toBe("symlink");
    expect(typeof realization.local.restoredAt).toBe("string");

    const recoveryRow = await db
      .select()
      .from(issueRecoveryActions)
      .where(eq(issueRecoveryActions.sourceIssueId, seeded.issueId))
      .then((rows) => rows[0]);
    expect(recoveryRow?.status).toBe("resolved");
    expect(recoveryRow?.outcome).toBe("restored");

    const assignee = await db
      .select({
        status: agents.status,
        errorReason: agents.errorReason,
      })
      .from(agents)
      .where(eq(agents.id, seeded.assigneeAgentId))
      .then((rows) => rows[0]);
    expect(assignee?.status).toBe("idle");
    expect(assignee?.errorReason).toBeNull();

    const previous = await db
      .select({
        status: agents.status,
        errorReason: agents.errorReason,
      })
      .from(agents)
      .where(eq(agents.id, previousOwnerAgentId))
      .then((rows) => rows[0]);
    expect(previous?.status).toBe("idle");
    expect(previous?.errorReason).toBeNull();

    const comments = await db
      .select()
      .from(issueComments)
      .where(eq(issueComments.issueId, seeded.issueId));
    expect(comments).toHaveLength(1);
    expect(comments[0]?.body).toContain("Workspace self-heal");
    expect(comments[0]?.body).toContain("symlink");
    expect(comments[0]?.body).toContain(managed);
  });

  it("posts a blocked comment and leaves the action active when repair fails", async () => {
    const seeded = await seedCompanyAndIssue({ companyIndex: 3 });
    await db.insert(issueRecoveryActions).values({
      companyId: seeded.companyId,
      sourceIssueId: seeded.issueId,
      kind: "workspace_validation",
      status: "active",
      cause: "workspace_validation_failed",
      fingerprint: `fp-${seeded.issueId}`,
      evidence: {
        executionWorkspaceCwd: seeded.executionCwd,
        resolvedProjectWorkspaceId: seeded.projectWorkspaceId,
      },
      ownerAgentId: seeded.assigneeAgentId,
      nextAction: "restore cwd",
      attemptCount: 1,
    });

    let statCalls = 0;
    mockFs.stat.mockImplementation(() => {
      statCalls += 1;
      return enoent();
    });
    mockFs.lstat.mockImplementation(() => enoent());
    mockFs.mkdir.mockImplementation(() => Promise.resolve());
    mockExecFile.mockImplementation(() =>
      Promise.reject(
        Object.assign(new Error("fatal: repository not found"), { code: 128 }),
      ),
    );

    const heartbeat = heartbeatService(db);
    const result = await heartbeat.reconcileWorkspaceValidationFailures();

    expect(result.scanned).toBe(1);
    expect(result.repaired).toBe(0);
    expect(result.failed).toBe(1);
    expect(result.failedIssueIds).toEqual([seeded.issueId]);
    expect(mockFs.rm).not.toHaveBeenCalled();

    const recoveryRow = await db
      .select()
      .from(issueRecoveryActions)
      .where(eq(issueRecoveryActions.sourceIssueId, seeded.issueId))
      .then((rows) => rows[0]);
    expect(recoveryRow?.status).toBe("active");
    expect(recoveryRow?.outcome).toBeNull();

    const projectRow = await db
      .select({ cwd: projectWorkspaces.cwd })
      .from(projectWorkspaces)
      .where(eq(projectWorkspaces.id, seeded.projectWorkspaceId))
      .then((rows) => rows[0]);
    expect(projectRow?.cwd).toBe(seeded.projectCwd);

    const execRows = await db
      .select({ cwd: executionWorkspaces.cwd })
      .from(executionWorkspaces)
      .where(eq(executionWorkspaces.sourceIssueId, seeded.issueId))
      .then((rows) => rows[0]);
    expect(execRows?.cwd).toBe(seeded.executionCwd);

    const comments = await db
      .select()
      .from(issueComments)
      .where(eq(issueComments.issueId, seeded.issueId));
    expect(comments).toHaveLength(1);
    expect(comments[0]?.body).toContain("could not restore the cwd");
    expect(comments[0]?.body).toContain("Manual intervention required");
  });

  it("repairs two companies independently and stamps each projectId in workspaceRealization", async () => {
    const a = await seedCompanyAndIssue({
      companyIndex: 4,
      assigneeAgentStatus: "error",
    });
    const b = await seedCompanyAndIssue({
      companyIndex: 5,
      assigneeAgentStatus: "error",
    });

    for (const seeded of [a, b]) {
      await db.insert(issueRecoveryActions).values({
        companyId: seeded.companyId,
        sourceIssueId: seeded.issueId,
        kind: "workspace_validation",
        status: "active",
        cause: "workspace_validation_failed",
        fingerprint: `fp-${seeded.issueId}`,
        evidence: {
          executionWorkspaceCwd: seeded.executionCwd,
          resolvedProjectWorkspaceId: seeded.projectWorkspaceId,
        },
        ownerAgentId: seeded.assigneeAgentId,
        nextAction: "restore cwd",
        attemptCount: 1,
      });
    }

    const symlinkedCwds = new Set<string>();
    const managedPrefix = "/tmp/paperclip-test/projects/";
    const resolveMockPath = (p: string) => {
      for (const symlinked of symlinkedCwds) {
        if (p === symlinked) {
          // the symlink target is the per-company managed folder, which is
          // determined by inferring from the source cwds path – but we just
          // need ANY managed folder for the mock to consider the path resolved
          return `${managedPrefix}_resolved/${symlinked}`;
        }
        if (p.startsWith(`${symlinked}/`)) {
          return `${managedPrefix}_resolved/${symlinked}${p.slice(symlinked.length)}`;
        }
      }
      return p;
    };
    mockFs.stat.mockImplementation((p: string) => {
      if (p.startsWith(managedPrefix)) return okStat();
      const resolved = resolveMockPath(p);
      if (resolved.startsWith(managedPrefix)) return okStat();
      return enoent();
    });
    mockFs.lstat.mockImplementation((p: string) => {
      if (symlinkedCwds.has(p)) {
        return Promise.resolve({
          isSymbolicLink: () => true,
          isDirectory: () => false,
          isFile: () => false,
        } as unknown as import("node:fs").Stats);
      }
      if (p.endsWith("/.git")) return dirStat();
      const resolved = resolveMockPath(p);
      if (resolved.endsWith("/.git")) return dirStat();
      return enoent();
    });
    mockFs.readdir.mockImplementation((p: string) => {
      if (p.startsWith(managedPrefix)) {
        return Promise.resolve([".git"] as unknown as string[]);
      }
      const resolved = resolveMockPath(p);
      if (resolved.startsWith(managedPrefix)) {
        return Promise.resolve([".git"] as unknown as string[]);
      }
      return Promise.resolve([] as unknown as string[]);
    });
    mockFs.mkdir.mockImplementation(() => Promise.resolve());
    mockExecFile.mockImplementation((_cmd: string, args: string[]) => {
      const target = args[args.length - 1];
      if (typeof target === "string") symlinkedCwds.add(target);
      return Promise.resolve({ stdout: "", stderr: "" });
    });

    const heartbeat = heartbeatService(db);
    const result = await heartbeat.reconcileWorkspaceValidationFailures();

    expect(result.scanned).toBe(2);
    expect(result.repaired).toBe(2);
    expect(result.failed).toBe(0);
    expect(result.repairedIssueIds.sort()).toEqual([a.issueId, b.issueId].sort());

    for (const seeded of [a, b]) {
      const execRows = await db
        .select()
        .from(executionWorkspaces)
        .where(
          and(
            eq(executionWorkspaces.companyId, seeded.companyId),
            eq(executionWorkspaces.sourceIssueId, seeded.issueId),
          ),
        );
      expect(execRows).toHaveLength(1);
      const exec = execRows[0]!;
      expect(exec.cwd).toBe(
        `/tmp/paperclip-test/projects/${seeded.companyId}/${seeded.projectId}/repo`,
      );
      const realization = (
        exec.metadata as Record<string, unknown>
      ).workspaceRealization as { local: Record<string, unknown> };
      expect(realization.local.projectId).toBe(seeded.projectId);
      expect(realization.local.projectWorkspaceId).toBe(seeded.projectWorkspaceId);

      const recoveryRow = await db
        .select()
        .from(issueRecoveryActions)
        .where(eq(issueRecoveryActions.sourceIssueId, seeded.issueId))
        .then((rows) => rows[0]);
      expect(recoveryRow?.status).toBe("resolved");

      const assignee = await db
        .select({ status: agents.status, errorReason: agents.errorReason })
        .from(agents)
        .where(eq(agents.id, seeded.assigneeAgentId))
        .then((rows) => rows[0]);
      expect(assignee?.status).toBe("idle");
      expect(assignee?.errorReason).toBeNull();

      const comments = await db
        .select()
        .from(issueComments)
        .where(eq(issueComments.issueId, seeded.issueId));
      expect(comments).toHaveLength(1);
      expect(comments[0]?.companyId).toBe(seeded.companyId);
    }
  });
});