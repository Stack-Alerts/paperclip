import express from "express";
import request from "supertest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.unmock("http");
vi.unmock("node:http");

const agentId = "11111111-1111-4111-8111-111111111111";
const otherAgentId = "22222222-2222-4222-8222-222222222222";
const companyId = "33333333-3333-4333-8333-333333333333";

const adapterConfigWithEnv = {
  env: {
    OPENAI_API_KEY: { type: "plain", value: "sk-live-secret-value" },
    OPENAI_BASE_URL: { type: "plain", value: "https://api.example.com" },
    LEGACY: "legacy-plain-string-value",
  },
  model: "gpt-4o",
};

const baseAgent = {
  id: agentId,
  companyId,
  name: "Builder",
  urlKey: "builder",
  role: "engineer",
  title: "Builder",
  icon: null,
  status: "idle",
  reportsTo: null,
  capabilities: null,
  adapterType: "opencode_local",
  adapterConfig: adapterConfigWithEnv,
  runtimeConfig: {},
  budgetMonthlyCents: 0,
  spentMonthlyCents: 0,
  pauseReason: null,
  pausedAt: null,
  permissions: { canCreateAgents: false },
  lastHeartbeatAt: null,
  metadata: null,
  createdAt: new Date("2026-04-11T00:00:00.000Z"),
  updatedAt: new Date("2026-04-11T00:00:00.000Z"),
};

const mockAgentService = vi.hoisted(() => ({
  getById: vi.fn(),
  list: vi.fn(),
  listConfigRevisions: vi.fn(),
  getConfigRevision: vi.fn(),
  getChainOfCommand: vi.fn(),
}));

const mockAccessService = vi.hoisted(() => ({
  canUser: vi.fn(),
  hasPermission: vi.fn(),
  getMembership: vi.fn(),
  ensureMembership: vi.fn(),
  listPrincipalGrants: vi.fn(),
  setPrincipalPermission: vi.fn(),
}));

const mockApprovalService = vi.hoisted(() => ({
  create: vi.fn(),
  getById: vi.fn(),
}));

const mockBudgetService = vi.hoisted(() => ({
  upsertPolicy: vi.fn(),
}));

const mockHeartbeatService = vi.hoisted(() => ({
  cancelActiveForAgent: vi.fn(),
  getRun: vi.fn(),
  getRunLogAccess: vi.fn(),
}));

const mockIssueApprovalService = vi.hoisted(() => ({
  linkManyForApproval: vi.fn(),
}));

const mockIssueService = vi.hoisted(() => ({
  list: vi.fn(),
  listDependencyReadiness: vi.fn(),
}));

const mockSecretService = vi.hoisted(() => ({
  normalizeAdapterConfigForPersistence: vi.fn(),
  resolveAdapterConfigForRuntime: vi.fn(),
  syncEnvBindingsForTarget: vi.fn(),
}));

const mockAgentInstructionsService = vi.hoisted(() => ({
  materializeManagedBundle: vi.fn(),
}));

const mockCompanySkillService = vi.hoisted(() => ({
  listRuntimeSkillEntries: vi.fn(),
  resolveRequestedSkillKeys: vi.fn(),
}));

const mockWorkspaceOperationService = vi.hoisted(() => ({}));
const mockLogActivity = vi.hoisted(() => vi.fn());
const mockGetTelemetryClient = vi.hoisted(() => vi.fn());

let canReadConfigs = false;
let canReadSecrets = false;
let canCreateAgents = false;

vi.mock("@paperclipai/shared/telemetry", () => ({
  trackAgentCreated: vi.fn(),
  trackErrorHandlerCrash: vi.fn(),
}));

vi.mock("../telemetry.js", () => ({
  getTelemetryClient: mockGetTelemetryClient,
}));

vi.mock("../routes/authz.js", async () => {
  const { forbidden, unauthorized } = await vi.importActual<typeof import("../errors.js")>("../errors.js");
  function assertAuthenticated(req: Express.Request) {
    if (req.actor.type === "none") {
      throw unauthorized();
    }
  }
  function assertBoard(req: Express.Request) {
    if (req.actor.type !== "board") {
      throw forbidden("Board access required");
    }
  }
  function assertCompanyAccess(req: Express.Request, expectedCompanyId: string) {
    assertAuthenticated(req);
    if (req.actor.type === "agent" && req.actor.companyId !== expectedCompanyId) {
      throw forbidden("Agent key cannot access another company");
    }
    if (req.actor.type === "board" && req.actor.source !== "local_implicit") {
      const allowedCompanies = req.actor.companyIds ?? [];
      if (!allowedCompanies.includes(expectedCompanyId)) {
        throw forbidden("User does not have access to this company");
      }
    }
  }
  function assertInstanceAdmin(req: Express.Request) {
    assertBoard(req);
    if (req.actor.source === "local_implicit" || req.actor.isInstanceAdmin) return;
    throw forbidden("Instance admin access required");
  }
  function getActorInfo(req: Express.Request) {
    assertAuthenticated(req);
    if (req.actor.type === "agent") {
      return {
        actorType: "agent" as const,
        actorId: req.actor.agentId ?? "unknown-agent",
        agentId: req.actor.agentId ?? null,
        runId: req.actor.runId ?? null,
      };
    }
    return {
      actorType: "user" as const,
      actorId: req.actor.userId ?? "board",
      agentId: null,
      runId: req.actor.runId ?? null,
    };
  }
  return {
    assertAuthenticated,
    assertBoard,
    assertCompanyAccess,
    assertInstanceAdmin,
    getActorInfo,
  };
});

vi.mock("../services/index.js", () => ({
  agentService: () => mockAgentService,
  agentInstructionsService: () => mockAgentInstructionsService,
  accessService: () => mockAccessService,
  approvalService: () => mockApprovalService,
  companySkillService: () => mockCompanySkillService,
  budgetService: () => mockBudgetService,
  heartbeatService: () => mockHeartbeatService,
  issueApprovalService: () => mockIssueApprovalService,
  issueService: () => mockIssueService,
  logActivity: mockLogActivity,
  secretService: () => mockSecretService,
  syncInstructionsBundleConfigFromFilePath: vi.fn((_agent, config) => config),
  workspaceOperationService: () => mockWorkspaceOperationService,
}));

vi.mock("../services/instance-settings.js", () => ({
  instanceSettingsService: () => ({
    getGeneral: vi.fn(async () => ({ censorUsernameInLogs: false })),
  }),
}));

let routeModules:
  | Promise<[
    typeof import("../middleware/index.js"),
    typeof import("../routes/agents.js"),
  ]>
  | null = null;

async function loadRouteModules() {
  routeModules ??= Promise.all([
    import("../middleware/index.js"),
    import("../routes/agents.js"),
  ]);
  return routeModules;
}

async function createApp(actor: Record<string, unknown>) {
  const [{ errorHandler }, { agentRoutes }] = await loadRouteModules();
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as any).actor = {
      ...actor,
      companyIds: Array.isArray(actor.companyIds) ? [...actor.companyIds] : actor.companyIds,
    };
    next();
  });
  app.use("/api", agentRoutes({} as any));
  app.use(errorHandler);
  return app;
}

async function requestApp(
  app: express.Express,
  buildRequest: (baseUrl: string) => request.Test,
) {
  const { createServer } = await vi.importActual<typeof import("node:http")>("node:http");
  const server = createServer(app);
  try {
    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", resolve);
    });
    const address = server.address();
    if (!address || typeof address === "string") {
      throw new Error("Expected HTTP server to listen on a TCP port");
    }
    return await buildRequest(`http://127.0.0.1:${address.port}`);
  } finally {
    if (server.listening) {
      await new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    }
  }
}

function resetMockDefaults() {
  vi.clearAllMocks();
  for (const mock of Object.values(mockAgentService)) mock.mockReset();
  for (const mock of Object.values(mockAccessService)) mock.mockReset();
  for (const mock of Object.values(mockApprovalService)) mock.mockReset();
  for (const mock of Object.values(mockBudgetService)) mock.mockReset();
  for (const mock of Object.values(mockHeartbeatService)) mock.mockReset();
  for (const mock of Object.values(mockIssueApprovalService)) mock.mockReset();
  for (const mock of Object.values(mockIssueService)) mock.mockReset();
  for (const mock of Object.values(mockSecretService)) mock.mockReset();
  for (const mock of Object.values(mockAgentInstructionsService)) mock.mockReset();
  for (const mock of Object.values(mockCompanySkillService)) mock.mockReset();
  mockLogActivity.mockReset();
  mockGetTelemetryClient.mockReset();
  mockGetTelemetryClient.mockReturnValue({ track: vi.fn() });
  canReadConfigs = false;
  canReadSecrets = false;
  canCreateAgents = false;
  mockAgentService.getById.mockImplementation(async (id: string) => ({
    ...baseAgent,
    id,
  }));
  mockAgentService.list.mockImplementation(async () => [{ ...baseAgent }]);
  mockAgentService.listConfigRevisions.mockImplementation(async () => []);
  mockAgentService.getConfigRevision.mockImplementation(async () => null);
  mockAgentService.getChainOfCommand.mockImplementation(async () => []);
  mockAccessService.canUser.mockImplementation(async (_companyId, _userId, permissionKey) => {
    if (permissionKey === "agents:create") return canCreateAgents;
    if (permissionKey === "secrets:read") return canReadSecrets;
    return false;
  });
  mockAccessService.hasPermission.mockImplementation(async () => canReadSecrets);
  mockAccessService.getMembership.mockImplementation(async () => null);
  mockAccessService.listPrincipalGrants.mockImplementation(async () => []);
  mockAccessService.ensureMembership.mockImplementation(async () => undefined);
  mockSecretService.normalizeAdapterConfigForPersistence.mockImplementation(
    async (_companyId: string, config: Record<string, unknown>) => config,
  );
  mockSecretService.resolveAdapterConfigForRuntime.mockImplementation(
    async (_companyId: string, config: Record<string, unknown>) => ({ config }),
  );
  mockSecretService.syncEnvBindingsForTarget.mockImplementation(async () => undefined);
  mockCompanySkillService.listRuntimeSkillEntries.mockImplementation(async () => []);
  mockCompanySkillService.resolveRequestedSkillKeys.mockImplementation(
    async (_companyId: string, keys: string[]) => keys,
  );
}

beforeEach(() => {
  resetMockDefaults();
});

describe("agent env redaction", () => {
  it("redacts adapterConfig.env plain values for board callers without secrets:read", async () => {
    canReadConfigs = true;
    canCreateAgents = true;
    canReadSecrets = false;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/agents/${agentId}`),
    );

    expect(res.status).toBe(200);
    const env = (res.body.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "***REDACTED***" });
    expect(env.OPENAI_BASE_URL).toEqual({ type: "plain", value: "***REDACTED***" });
    expect(env.LEGACY).toEqual({ type: "plain", value: "***REDACTED***" });
    expect(res.body.adapterConfig).not.toHaveProperty("value");
    const serialized = JSON.stringify(res.body);
    expect(serialized).not.toContain("sk-live-secret-value");
    expect(serialized).not.toContain("legacy-plain-string-value");
  });

  it("returns the full env to board callers with secrets:read and logs an activity event", async () => {
    canReadConfigs = true;
    canCreateAgents = true;
    canReadSecrets = true;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/agents/${agentId}`),
    );

    expect(res.status).toBe(200);
    const env = (res.body.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "sk-live-secret-value" });
    expect(env.OPENAI_BASE_URL).toEqual({ type: "plain", value: "https://api.example.com" });

    const envReadEvents = mockLogActivity.mock.calls
      .map((call) => call[1] as { action: string })
      .filter((event) => event.action === "agent.env.read");
    expect(envReadEvents.length).toBeGreaterThan(0);
  });

  it("returns the full env to the agent reading its own /agents/me record and does not log a self read", async () => {
    canReadConfigs = false;
    canReadSecrets = false;

    const app = await createApp({
      type: "agent",
      agentId,
      companyId,
      keyId: "agent-key",
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get("/api/agents/me"),
    );

    expect(res.status).toBe(200);
    const env = (res.body.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "sk-live-secret-value" });

    const envReadEvents = mockLogActivity.mock.calls
      .map((call) => call[1] as { action: string })
      .filter((event) => event.action === "agent.env.read");
    expect(envReadEvents).toHaveLength(0);
  });

  it("redacts env values on the list endpoint for board callers without secrets:read", async () => {
    canReadConfigs = true;
    canCreateAgents = true;
    canReadSecrets = false;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/companies/${companyId}/agents`),
    );

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    const item = res.body[0];
    const env = (item.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "***REDACTED***" });
    const serialized = JSON.stringify(res.body);
    expect(serialized).not.toContain("sk-live-secret-value");
  });

  it("returns a redacted empty config for board callers without agents:create", async () => {
    canReadConfigs = false;
    canCreateAgents = false;
    canReadSecrets = false;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/agents/${agentId}`),
    );

    expect(res.status).toBe(200);
    expect(res.body.adapterConfig).toEqual({});
  });

  it("redacts env values on /configuration when the caller lacks secrets:read", async () => {
    canReadConfigs = true;
    canCreateAgents = true;
    canReadSecrets = false;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/agents/${agentId}/configuration`),
    );

    expect(res.status).toBe(200);
    const env = (res.body.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "***REDACTED***" });
  });

  it("returns the full env on /configuration when the caller has secrets:read", async () => {
    canReadConfigs = true;
    canCreateAgents = true;
    canReadSecrets = true;

    const app = await createApp({
      type: "board",
      source: "session",
      userId: "user-board",
      companyIds: [companyId],
    });

    const res = await requestApp(app, (baseUrl) =>
      request(baseUrl).get(`/api/agents/${agentId}/configuration`),
    );

    expect(res.status).toBe(200);
    const env = (res.body.adapterConfig as Record<string, unknown>).env as Record<string, unknown>;
    expect(env.OPENAI_API_KEY).toEqual({ type: "plain", value: "sk-live-secret-value" });
  });
});
