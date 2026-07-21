-- ${NEXT}_routine_run_no_op_suppression.sql
--
-- Add a `no_op` flag to `routine_runs` and a denormalized `last_no_op_at`
-- to `routines`. The heartbeat scheduler's `tickScheduledTriggers`
-- suppresses a new execution issue when the previous run of the same
-- routine was a no-op (the agent scanned and found nothing to do, then
-- closed the issue as `cancelled`).
--
-- Background: prior to this migration the scheduler minted a fresh
-- issue on every cron tick — even when the routine had nothing to do.
-- Two active routines in the BTC Trade Engine worktree ran every 5
-- and 15 minutes respectively, generating ~575 no-op issues in three
-- days and cluttering every project's "Issues" view. The agent code
-- already states "Silent no-op when nothing is broken/flagged" in the
-- routine guardrails; this migration makes the runtime honor it.
--
-- Strategy: when `syncRunStatusForIssue` sees an issue move to
-- `cancelled`, it sets `no_op=true` on the linked routine_run. The
-- scheduler then checks `routines.last_no_op_at`: if the previous
-- run's no-op timestamp is more recent than one cron interval, the
-- scheduler skips `dispatchRoutineRun`, advances `nextRunAt`, and
-- records a `skipped` routine_run with failure_reason
-- `'silent_no_op_recent'`. The next cron tick after one interval has
-- elapsed runs the routine normally.
--
-- Backfill: any routine_run whose linked issue is currently
-- `cancelled` (i.e. the routine's most recent run was a no-op when
-- this migration was applied) gets `no_op=true`. The corresponding
-- routine's `last_no_op_at` is set to the max(triggered_at) of those
-- runs, so the scheduler starts suppressing immediately.
--
-- Author: MiniMax-M3 (BTCAAAAA-40760 fix-no-op-routine-spam)
--> statement-breakpoint

ALTER TABLE "routine_runs"
  ADD COLUMN IF NOT EXISTS "no_op" boolean NOT NULL DEFAULT false;
--> statement-breakpoint

ALTER TABLE "routines"
  ADD COLUMN IF NOT EXISTS "last_no_op_at" timestamp with time zone;
--> statement-breakpoint

CREATE INDEX IF NOT EXISTS "routine_runs_routine_no_op_idx"
  ON "routine_runs" ("routine_id", "no_op", "triggered_at" DESC);
--> statement-breakpoint

CREATE INDEX IF NOT EXISTS "routines_company_last_no_op_idx"
  ON "routines" ("company_id", "last_no_op_at")
  WHERE "last_no_op_at" IS NOT NULL;
--> statement-breakpoint

-- Backfill: any routine_run whose linked issue is currently
-- `cancelled` is a no-op. (We could also include rows whose
-- failure_reason is `'silent_no_op'`, but cancelled with linked
-- issue covers the bulk of the cases we care about.)
UPDATE "routine_runs" AS rr
   SET "no_op" = true
  FROM "issues" AS i
 WHERE i."id" = rr."linked_issue_id"
   AND i."status" = 'cancelled'
   AND rr."status" IN ('completed', 'failed')
   AND rr."no_op" = false;
--> statement-breakpoint

-- Backfill: routines.last_no_op_at = max triggered_at of any no-op
-- run that ran in the last 7 days. We bound the window to 7 days
-- so a routine that hasn't fired as a no-op recently gets a fresh
-- chance on its next tick.
UPDATE "routines" AS r
   SET "last_no_op_at" = sub.last_no_op
  FROM (
    SELECT rr."routine_id" AS routine_id, max(rr."triggered_at") AS last_no_op
      FROM "routine_runs" AS rr
     WHERE rr."no_op" = true
       AND rr."triggered_at" > NOW() - INTERVAL '7 days'
     GROUP BY rr."routine_id"
  ) AS sub
 WHERE r."id" = sub."routine_id"
   AND r."last_no_op_at" IS NULL;
--> statement-breakpoint
