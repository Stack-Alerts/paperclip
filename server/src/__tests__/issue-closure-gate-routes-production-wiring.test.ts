import express from "express";
import request from "supertest";
import { execFile, execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const issueId = "11111111-1111-4111-8111-111111111111";
const companyId = "22222222-2222-4222-8222-222222222222";
const ownerAgentId = "33333333-3333-4333-8333-333333333333";
const ownerRunId = "55555555-5555-4555-8555-555555555555";

const mockIssueService = vi.hoisted(() => ({
  addComment: vi.fn(),
  assertCheckoutOwner: vi.fn(),
  getAttachmentById: vi.fn(),
  getByIdentifier: vi.fn(),
  getById: vi.fn(),
  getRelationSummaries: vi.fn(),
  getWakeableParentAfterChildCompletion: vi.fn(),
  listAttachments: vi.fn(),
  listComments: vi.fn(),
  listWakeableBlockedDependents: vi.fn(),
  remove: vi.fn(),
  removeAttachment: vi.fn(),
  update: vi.fn(),
  findMentionedAgents: vi.fn(),
}));

const mockAccessService = vi.hoisted(() => ({
  canUser: vi.fn(),
  decide: vi.fn(),
  hasPermission: vi.fn(),
}));

const mockAgentService = vi.hoisted(() => ({
  getById: vi.fn(),
  list: vi.fn(),
  resolveByReference: vi.fn(),
}));

const mockCompanyService = vi.hoisted(() => ({
  getById: vi.fn(),
}));

const mockDocumentService = vi.hoisted(() => ({
  upsertIssueDocument: vi.fn(),
}));

const mockWorkProductService = vi.hoisted(() => ({
  getById: vi.fn(),
  update: vi.fn(),
}));

const mockStorageService = vi.hoisted(() => ({
  provider: "local_disk",
  putFile: vi.fn(),
  getObject: vi.fn(),
  headObject: vi.fn(),
  deleteObject: vi.fn(),
}));

const mockExecutionWorkspaceService = vi.hoisted(() => ({
  getById: vi.fn(),
}));

const mockIssueThreadInteractionService = vi.hoisted(() => ({
  expireRequestConfirmationsSupersededByComment: vi.fn(async () => []),
  expireStaleRequestConfirmationsForIssueDocument: vi.fn(async () => []),
}));

const mockIssueRecoveryActionService = vi.hoisted(() => ({
  getActiveForIssue: vi.fn(async () => null),
}));

const mockIssueApprovalService = vi.hoisted(() => ({
  listApprovalsForIssue: vi.fn(async () => []),
}));

function registerRouteMocks() {
  // Keep the real closure gate to exercise production wiring.
  vi.doMock("@paperclipai/shared/telemetry", () => ({
    trackAgentTaskCompleted: vi.fn(),
    trackErrorHandlerCrash: vi.fn(),
  }));

  vi.doMock("../telemetry.js", () => ({
    getTelemetryClient: vi.fn(() => ({ track: vi.fn() })),
  }));

  vi.doMock("../services/access.js", () => ({
    accessService: () => mockAccessService,
  }));

  vi.doMock("../services/agents.js", () => ({
    agentService: () => mockAgentService,
  }));

  vi.doMock("../services/documents.js", () => ({
    documentService: () => mockDocumentService,
  }));

  vi.doMock("../services/execution-workspaces.js", () => ({
    executionWorkspaceService: () => mockExecutionWorkspaceService,
  }));

  vi.doMock("../services/issues.js", () => ({
    issueService: () => mockIssueService,
  }));

  vi.doMock("../services/task-watchdog-scope.js", () => ({
    TASK_WATCHDOG_ORIGIN_KIND: "task_watchdog",
    resolveTaskWatchdogMutationScope: vi.fn(async () => ({ kind: "none" })),
    taskWatchdogScopeAllowsIssueMutation: vi.fn(async () => true),
  }));

  vi.doMock("../services/source-trust.js", () => ({
    buildPromotedSourceTrust: vi.fn(),
    isLowTrustQuarantined: vi.fn(() => false),
    redactQuarantinedBodyForHigherTrust: vi.fn((body: string) => body),
    resolveActorSourceTrustForIssue: vi.fn(async () => ({
      trustLevel: "trusted",
      decision: "allow",
      source: "test",
    })),
    sanitizeQuarantinedCommentForHigherTrust: vi.fn((body: string) => body),
  }));

  vi.doMock("../services/work-products.js", () => ({
    workProductService: () => mockWorkProductService,
  }));

  vi.doMock("../services/issue-approvals.js", () => ({
    issueApprovalService: () => mockIssueApprovalService,
  }));

  vi.doMock("../services/activity-log.js", () => ({
    logActivity: vi.fn(async () => undefined),
  }));

  vi.doMock("../services/index.js", () => ({
    accessService: () => mockAccessService,
    agentService: () => mockAgentService,
    companyService: () => mockCompanyService,
    documentAnnotationService: () => ({}),
    documentService: () => mockDocumentService,
    executionWorkspaceService: () => mockExecutionWorkspaceService,
    feedbackService: () => ({
      listIssueVotesForUser: vi.fn(async () => []),
      saveIssueVote: vi.fn(async () => ({ vote: null, consentEnabledNow: false, sharingEnabled: false })),
    }),
    goalService: () => ({}),
    heartbeatService: () => ({
      wakeup: vi.fn(async () => undefined),
      reportRunActivity: vi.fn(async () => undefined),
      getRun: vi.fn(async () => null),
      getActiveRunForAgent: vi.fn(async () => null),
      cancelRun: vi.fn(async () => null),
    }),
    instanceSettingsService: () => ({
      get: vi.fn(async () => ({
        id: "instance-settings-1",
        general: {
          censorUsernameInLogs: false,
          feedbackDataSharingPreference: "prompt",
        },
      })),
      listCompanyIds: vi.fn(async () => [companyId]),
    }),
    issueApprovalService: () => mockIssueApprovalService,
    issueRecoveryActionService: () => mockIssueRecoveryActionService,
    issueReferenceService: () => ({
      deleteDocumentSource: async () => undefined,
      diffIssueReferenceSummary: () => ({
        addedReferencedIssues: [],
        removedReferencedIssues: [],
        currentReferencedIssues: [],
      }),
      emptySummary: () => ({ outbound: [], inbound: [] }),
      listIssueReferenceSummary: async () => ({ outbound: [], inbound: [] }),
      syncComment: async () => undefined,
      syncDocument: async () => undefined,
      syncIssue: async () => undefined,
    }),
    issueService: () => mockIssueService,
    issueThreadInteractionService: () => mockIssueThreadInteractionService,
    logActivity: vi.fn(async () => undefined),
    projectService: () => ({}),
    routineService: () => ({
      syncRunStatusForIssue: vi.fn(async () => undefined),
    }),
    workProductService: () => mockWorkProductService,
  }));
}

function makeIssue(overrides: Record<string, unknown> = {}) {
  return {
    id: issueId,
    companyId,
    status: "in_progress",
    priority: "high",
    projectId: null,
    goalId: null,
    parentId: null,
    assigneeAgentId: ownerAgentId,
    assigneeUserId: null,
    createdByUserId: "board-user",
    identifier: "PAP-1649",
    title: "Owned active issue",
    originKind: "manual",
    originId: null,
    executionPolicy: null,
    executionState: null,
    hiddenAt: null,
    executionWorkspaceId: "ws-1",
    ...overrides,
  };
}

function makeAgent(id: string) {
  return {
    id,
    companyId,
    role: "engineer",
    reportsTo: null,
    permissions: { canCreateAgents: false },
  };
}

async function createApp(actor: Record<string, unknown>) {
  const [{ errorHandler }, { issueRoutes }] = await Promise.all([
    vi.importActual<typeof import("../middleware/index.js")>("../middleware/index.js"),
    vi.importActual<typeof import("../routes/issues.js")>("../routes/issues.js"),
  ]);
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = actor;
    next();
  });
  app.use("/api", issueRoutes({} as any, mockStorageService as any));
  app.use(errorHandler);
  return app;
}

function ownerActor() {
  return {
    type: "agent",
    agentId: ownerAgentId,
    companyId,
    source: "agent_key",
    runId: ownerRunId,
  };
}

async function initRealGitWorkspace(): Promise<{ cwd: string; sha: string; cleanup: () => void }> {
  const cwd = mkdtempSync(join(tmpdir(), "paperclip-closure-gate-wiring-"));
  execFileSync("git", ["init", "--quiet", "--initial-branch=main"], { cwd });
  execFileSync("git", ["config", "user.email", "test@example.com"], { cwd });
  execFileSync("git", ["config", "user.name", "Test"], { cwd });
  execFileSync("git", ["config", "commit.gpgsign", "false"], { cwd });
  execFileSync("git", ["config", "tag.gpgsign", "false"], { cwd });
  execFileSync("git", ["commit", "--allow-empty", "--quiet", "-m", "initial commit"], { cwd });
  const { stdout } = await new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
    execFile("git", ["rev-parse", "HEAD"], { cwd }, (err, stdout, stderr) => {
      if (err) reject(err);
      else resolve({ stdout, stderr });
    });
  });
  const sha = stdout.trim();
  return {
    cwd,
    sha,
    cleanup: () => {
      try {
        rmSync(cwd, { recursive: true, force: true });
      } catch {}
    },
  };
}

describe("issue closure-gate route — production wiring of local verifier", () => {
  let realWorkspace: { cwd: string; sha: string; cleanup: () => void } | null = null;

  beforeEach(async () => {
    vi.resetModules();
    vi.doUnmock("@paperclipai/shared/telemetry");
    vi.doUnmock("../telemetry.js");
    vi.doUnmock("../services/access.js");
    vi.doUnmock("../services/activity-log.js");
    vi.doUnmock("../services/agents.js");
    vi.doUnmock("../services/documents.js");
    vi.doUnmock("../services/execution-workspaces.js");
    vi.doUnmock("../services/index.js");
    vi.doUnmock("../services/issue-approvals.js");
    vi.doUnmock("../services/issues.js");
    vi.doUnmock("../services/work-products.js");
    vi.doUnmock("../routes/issues.js");
    vi.doUnmock("../routes/authz.js");
    vi.doUnmock("../middleware/index.js");
    registerRouteMocks();
    vi.clearAllMocks();

    mockAccessService.canUser.mockResolvedValue(true);
    mockAccessService.decide.mockResolvedValue({ allowed: true, reason: "test" });
    mockAccessService.hasPermission.mockResolvedValue(false);
    mockAgentService.getById.mockImplementation(async (id: string) =>
      id === ownerAgentId ? makeAgent(ownerAgentId) : null,
    );
    mockAgentService.list.mockResolvedValue([makeAgent(ownerAgentId)]);
    mockAgentService.resolveByReference.mockResolvedValue({ ambiguous: false, agent: null });
    mockIssueService.getById.mockResolvedValue(makeIssue());
    mockIssueService.getByIdentifier.mockResolvedValue(null);
    mockIssueService.assertCheckoutOwner.mockResolvedValue({ adoptedFromRunId: null });
    mockIssueService.getRelationSummaries.mockResolvedValue({ blockedBy: [], blocks: [] });
    mockIssueService.listWakeableBlockedDependents.mockResolvedValue([]);
    mockIssueService.getWakeableParentAfterChildCompletion.mockResolvedValue(null);
    mockIssueService.findMentionedAgents.mockResolvedValue([]);
    mockIssueService.listComments.mockResolvedValue([]);
    mockIssueService.update.mockImplementation(async (id: string, patch: Record<string, unknown>) => ({
      ...makeIssue({ id }),
      ...patch,
    }));
    mockIssueService.addComment.mockResolvedValue({
      id: "77777777-7777-4777-8777-777777777777",
      issueId,
      companyId,
      body: "comment",
    });
    mockIssueService.listAttachments.mockResolvedValue([]);
    mockIssueService.remove.mockResolvedValue(makeIssue({ status: "cancelled" }));
    mockDocumentService.upsertIssueDocument.mockResolvedValue({
      created: false,
      document: { id: "doc-1", key: "plan", title: "Plan", format: "markdown", latestRevisionNumber: 1 },
    });
    mockWorkProductService.getById.mockResolvedValue({
      id: "wp-1",
      issueId,
      companyId,
      type: "artifact",
    });
    mockWorkProductService.update.mockResolvedValue({
      id: "wp-1",
      issueId,
      companyId,
      type: "artifact",
      title: "Updated",
    });

    if (realWorkspace) {
      realWorkspace.cleanup();
      realWorkspace = null;
    }
  });

  afterEach(() => {
    if (realWorkspace) {
      realWorkspace.cleanup();
      realWorkspace = null;
    }
  });

  it("accepts a Fix-SHA present in the resolved source workspace via the real production verifier", async () => {
    realWorkspace = await initRealGitWorkspace();
    mockExecutionWorkspaceService.getById.mockResolvedValue({
      id: "ws-1",
      companyId,
      repoUrl: "https://example.com/repo.git",
      providerRef: realWorkspace.cwd,
    });
    mockCompanyService.getById.mockResolvedValue({ id: companyId, closureGateFixSha: "enforce" });

    const res = await request(await createApp(ownerActor()))
      .patch(`/api/issues/${issueId}`)
      .send({
        status: "done",
        comment: `Fix-SHA: ${realWorkspace.sha}\nFix-Target: main`,
      });

    expect(res.status, JSON.stringify(res.body)).toBe(200);
    expect(res.body).toMatchObject({ id: issueId, status: "done" });
    expect(mockIssueService.update).toHaveBeenCalledWith(
      issueId,
      expect.objectContaining({ status: "done" }),
    );
  });

  it("rejects a Fix-SHA that is not present in the resolved source workspace via the real production verifier", async () => {
    realWorkspace = await initRealGitWorkspace();
    mockExecutionWorkspaceService.getById.mockResolvedValue({
      id: "ws-1",
      companyId,
      repoUrl: "https://example.com/repo.git",
      providerRef: realWorkspace.cwd,
    });
    mockCompanyService.getById.mockResolvedValue({ id: companyId, closureGateFixSha: "enforce" });

    const fabricatedSha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef";

    const res = await request(await createApp(ownerActor()))
      .patch(`/api/issues/${issueId}`)
      .send({
        status: "done",
        comment: `Fix-SHA: ${fabricatedSha}\nFix-Target: main`,
      });

    expect(res.status, JSON.stringify(res.body)).toBe(422);
    expect(res.body).toMatchObject({
      details: expect.objectContaining({ reason: "unreachable_sha" }),
    });
    expect(mockIssueService.update).not.toHaveBeenCalled();
  });

  it("rejects a Fix-SHA that resolves to a non-commit object in the source workspace", async () => {
    realWorkspace = await initRealGitWorkspace();
    mockExecutionWorkspaceService.getById.mockResolvedValue({
      id: "ws-1",
      companyId,
      repoUrl: "https://example.com/repo.git",
      providerRef: realWorkspace.cwd,
    });
    mockCompanyService.getById.mockResolvedValue({ id: companyId, closureGateFixSha: "enforce" });

    const blobSha = execFileSync("git", ["hash-object", "-w", "--stdin"], {
      cwd: realWorkspace.cwd,
      input: "not a commit",
    })
      .toString()
      .trim();

    const res = await request(await createApp(ownerActor()))
      .patch(`/api/issues/${issueId}`)
      .send({
        status: "done",
        comment: `Fix-SHA: ${blobSha}\nFix-Target: main`,
      });

    expect(res.status, JSON.stringify(res.body)).toBe(422);
    expect(res.body).toMatchObject({
      details: expect.objectContaining({ reason: "unreachable_sha" }),
    });
    expect(mockIssueService.update).not.toHaveBeenCalled();
  });
});
