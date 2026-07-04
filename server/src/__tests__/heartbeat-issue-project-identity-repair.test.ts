import { randomUUID } from "node:crypto";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { and, eq, isNull } from "drizzle-orm";
import {
  companies,
  createDb,
  issues,
  projectWorkspaces,
  projects,
} from "@paperclipai/db";
import {
  getEmbeddedPostgresTestSupport,
  startEmbeddedPostgresTestDatabase,
} from "./helpers/embedded-postgres.js";
import { repairStaleIssueProjectIdentity } from "../services/issue-project-identity-repair.ts";

const embeddedPostgresSupport = await getEmbeddedPostgresTestSupport();
const describeEmbeddedPostgres = embeddedPostgresSupport.supported ? describe : describe.skip;

if (!embeddedPostgresSupport.supported) {
  console.warn(
    `Skipping embedded Postgres repair tests on this host: ${embeddedPostgresSupport.reason ?? "unsupported environment"}`,
  );
}

describeEmbeddedPostgres("repairStaleIssueProjectIdentity", () => {
  let db!: ReturnType<typeof createDb>;
  let tempDb: Awaited<ReturnType<typeof startEmbeddedPostgresTestDatabase>> | null = null;
  let companyId: string;
  let projectId: string;
  let otherProjectId: string;
  let workspaceId: string;
  let otherWorkspaceId: string;

  beforeAll(async () => {
    tempDb = await startEmbeddedPostgresTestDatabase("paperclip-repair-project-id-");
    db = createDb(tempDb.connectionString);
    companyId = randomUUID();
    projectId = randomUUID();
    otherProjectId = randomUUID();
    workspaceId = randomUUID();
    otherWorkspaceId = randomUUID();

    await db.insert(companies).values({
      id: companyId,
      name: "Repair Test Co",
      issuePrefix: `RPR${companyId.replace(/-/g, "").slice(0, 4).toUpperCase()}`,
    });
    await db.insert(projects).values([
      {
        id: projectId,
        companyId,
        name: "Repair Test Project",
        status: "active",
      },
      {
        id: otherProjectId,
        companyId,
        name: "Other Project",
        status: "active",
      },
    ]);
    await db.insert(projectWorkspaces).values([
      {
        id: workspaceId,
        companyId,
        projectId,
        name: "Primary",
        cwd: "/tmp/repair-test",
        isPrimary: true,
      },
      {
        id: otherWorkspaceId,
        companyId,
        projectId: otherProjectId,
        name: "Other Primary",
        cwd: "/tmp/other-workspace",
        isPrimary: true,
      },
    ]);
  }, 20_000);

  afterEach(async () => {
    await db.delete(issues).where(eq(issues.companyId, companyId));
  });

  afterAll(async () => {
    await db.delete(issues).where(eq(issues.companyId, companyId));
    await db.delete(projectWorkspaces).where(eq(projectWorkspaces.companyId, companyId));
    await db.delete(projects).where(eq(projects.companyId, companyId));
    await db.delete(companies).where(eq(companies.id, companyId));
    await tempDb?.cleanup();
  });

  it("repairs an issue whose project_id was lost by writing it back from the project workspace", async () => {
    const issueId = randomUUID();
    await db.insert(issues).values({
      id: issueId,
      companyId,
      title: "Stale project_id, has workspace",
      status: "todo",
      projectId: null,
      projectWorkspaceId: workspaceId,
    });

    const issueRef: { id: string; identifier: string | null; projectId: string | null; projectWorkspaceId: string | null } = {
      id: issueId,
      identifier: "RPR-1",
      projectId: null,
      projectWorkspaceId: workspaceId,
    };

    const outcome = await repairStaleIssueProjectIdentity(db, issueRef);

    expect(outcome).toEqual({
      repaired: true,
      issueId,
      issueIdentifier: "RPR-1",
      repairedProjectId: projectId,
      source: "project_workspace",
    });
    expect(issueRef.projectId).toBe(projectId);

    const [persisted] = await db
      .select({ projectId: issues.projectId })
      .from(issues)
      .where(eq(issues.id, issueId))
      .limit(1);
    expect(persisted?.projectId).toBe(projectId);
  });

  it("skips the repair when the issue already has a project_id", async () => {
    const issueId = randomUUID();
    await db.insert(issues).values({
      id: issueId,
      companyId,
      title: "Already populated",
      status: "todo",
      projectId: otherProjectId,
      projectWorkspaceId: workspaceId,
    });

    const issueRef = {
      id: issueId,
      identifier: "RPR-2",
      projectId: otherProjectId,
      projectWorkspaceId: workspaceId,
    };

    const outcome = await repairStaleIssueProjectIdentity(db, issueRef);

    expect(outcome).toMatchObject({
      repaired: false,
      issueId,
      reason: "no_project_workspace",
    });
    expect(issueRef.projectId).toBe(otherProjectId);
  });

  it("skips the repair when there is no project workspace link to derive from", async () => {
    const issueId = randomUUID();
    await db.insert(issues).values({
      id: issueId,
      companyId,
      title: "No workspace, no project",
      status: "todo",
      projectId: null,
      projectWorkspaceId: null,
    });

    const issueRef = {
      id: issueId,
      identifier: "RPR-3",
      projectId: null,
      projectWorkspaceId: null,
    };

    const outcome = await repairStaleIssueProjectIdentity(db, issueRef);

    expect(outcome).toMatchObject({
      repaired: false,
      issueId,
      reason: "no_project_workspace",
    });
  });

  it("reports missing_workspace_row when the linked project workspace does not exist", async () => {
    const issueId = randomUUID();
    const danglingWorkspaceId = randomUUID();
    await db.insert(projectWorkspaces).values({
      id: danglingWorkspaceId,
      companyId,
      projectId,
      name: "Soon deleted",
      cwd: "/tmp/soon-deleted",
      isPrimary: false,
    });
    await db.insert(issues).values({
      id: issueId,
      companyId,
      title: "Dangling workspace link",
      status: "todo",
      projectId: null,
      projectWorkspaceId: danglingWorkspaceId,
    });
    await db.delete(projectWorkspaces).where(eq(projectWorkspaces.id, danglingWorkspaceId));

    const issueRef = {
      id: issueId,
      identifier: "RPR-4",
      projectId: null,
      projectWorkspaceId: danglingWorkspaceId,
    };

    const outcome = await repairStaleIssueProjectIdentity(db, issueRef);

    expect(outcome).toMatchObject({
      repaired: false,
      issueId,
      reason: "missing_workspace_row",
    });
    expect(issueRef.projectId).toBeNull();

    const [persisted] = await db
      .select({ projectId: issues.projectId })
      .from(issues)
      .where(eq(issues.id, issueId))
      .limit(1);
    expect(persisted?.projectId).toBeNull();
  });

  it("reports concurrent_write when another writer set project_id before the repair's update landed", async () => {
    const issueId = randomUUID();
    await db.insert(issues).values({
      id: issueId,
      companyId,
      title: "Lost the race",
      status: "todo",
      projectId: null,
      projectWorkspaceId: workspaceId,
    });

    const issueRef = {
      id: issueId,
      identifier: "RPR-5",
      projectId: null,
      projectWorkspaceId: workspaceId,
    };

    await db
      .update(issues)
      .set({ projectId: otherProjectId })
      .where(and(eq(issues.id, issueId), isNull(issues.projectId)));

    const outcome = await repairStaleIssueProjectIdentity(db, issueRef);

    expect(outcome).toMatchObject({
      repaired: false,
      issueId,
      reason: "concurrent_write",
    });
    expect(issueRef.projectId).toBeNull();
  });
});