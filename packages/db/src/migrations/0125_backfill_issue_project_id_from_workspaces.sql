-- Backfill issues.project_id from project_workspaces or execution_workspaces
-- where the row was set but project_id was dropped during inheritance or
-- workspace assignment. This unblocks issues that are linked to a project
-- workspace but have no project id, which the heartbeat workspace-validation
-- guard refuses to launch for git-sensitive adapters.
--
-- The migration is idempotent: it only writes rows where project_id IS NULL,
-- and the subqueries already filter to non-null project ids on the workspace
-- rows.

UPDATE "issues" AS i
SET
  "project_id" = pw."project_id",
  "updated_at" = now()
FROM "project_workspaces" AS pw
WHERE i."project_workspace_id" = pw."id"
  AND i."project_id" IS NULL
  AND pw."project_id" IS NOT NULL;

UPDATE "issues" AS i
SET
  "project_id" = ew."project_id",
  "updated_at" = now()
FROM "execution_workspaces" AS ew
WHERE i."execution_workspace_id" = ew."id"
  AND i."project_id" IS NULL
  AND ew."project_id" IS NOT NULL;