import { and, eq, isNull } from "drizzle-orm";
import type { Db } from "@paperclipai/db";
import { issues, projectWorkspaces } from "@paperclipai/db";

export type RepairStaleIssueProjectIdentityOutcome =
  | {
      repaired: true;
      issueId: string;
      issueIdentifier: string | null;
      repairedProjectId: string;
      source: "project_workspace";
    }
  | {
      repaired: false;
      issueId: string;
      issueIdentifier: string | null;
      reason:
        | "no_project_workspace"
        | "missing_workspace_row"
        | "workspace_missing_project_id"
        | "concurrent_write";
    };

function readNonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export async function repairStaleIssueProjectIdentity(
  db: Db,
  issueRef: {
    id: string;
    identifier?: string | null;
    projectId: string | null;
    projectWorkspaceId: string | null;
  },
): Promise<RepairStaleIssueProjectIdentityOutcome> {
  const identifier = issueRef.identifier ?? null;
  if (issueRef.projectId || !issueRef.projectWorkspaceId) {
    return {
      repaired: false,
      issueId: issueRef.id,
      issueIdentifier: identifier,
      reason: "no_project_workspace",
    };
  }
  const [workspace] = await db
    .select({ projectId: projectWorkspaces.projectId })
    .from(projectWorkspaces)
    .where(eq(projectWorkspaces.id, issueRef.projectWorkspaceId))
    .limit(1);
  if (!workspace) {
    return {
      repaired: false,
      issueId: issueRef.id,
      issueIdentifier: identifier,
      reason: "missing_workspace_row",
    };
  }
  const repairedProjectId = readNonEmptyString(workspace.projectId);
  if (!repairedProjectId) {
    return {
      repaired: false,
      issueId: issueRef.id,
      issueIdentifier: identifier,
      reason: "workspace_missing_project_id",
    };
  }
  const updated = await db
    .update(issues)
    .set({ projectId: repairedProjectId, updatedAt: new Date() })
    .where(and(eq(issues.id, issueRef.id), isNull(issues.projectId)))
    .returning({ id: issues.id });
  if (updated.length === 0) {
    return {
      repaired: false,
      issueId: issueRef.id,
      issueIdentifier: identifier,
      reason: "concurrent_write",
    };
  }
  issueRef.projectId = repairedProjectId;
  return {
    repaired: true,
    issueId: issueRef.id,
    issueIdentifier: identifier,
    repairedProjectId,
    source: "project_workspace",
  };
}