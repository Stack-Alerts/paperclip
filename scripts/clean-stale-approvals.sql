-- =============================================================================
-- clean-stale-approvals.sql
--
-- Cleans up `request_confirmation` interactions whose underlying work was
-- completed by other means. These are 'ghost' approvals that accumulate
-- when the merge-dispatch routine closes an issue but the original
-- approval request was never explicitly resolved.
--
-- The original investigation (2026-07-01) found 178 stale + 3 actionable
-- approvals. After the user confirmed BTCAAAAA-38590 in the Paperclip UI,
-- 177 stale + 3 actionable remain.
--
-- ACTIONS TAKEN BY THIS SCRIPT (when run with --execute):
--   1. Resolve 177 stale approvals on issues with status='done'/'cancelled'
--      as status='cancelled', result.outcome='superseded_by_completed_work'.
--   2. Resolve 1 duplicate approval on BTCAAAAA-38474 (the older
--      `pr271-approval-v2` from 14:00) as status='cancelled',
--      result.outcome='superseded_by_newer_request'.
--   3. Resolve 1 stale approval on BTCAAAAA-34618 (the backtest plan
--      approval — children BTCAAAAA-34619/34620 already done) as
--      status='cancelled', result.outcome='superseded_by_completed_children'.
--   4. LEAVE the newer BTCAAAAA-38474 approval (16:34, PR #271) UNTOUCHED.
--      This is the one asking the board to click 'Approve' on PR #271.
--
-- NO WORK IS LOST. This script only updates the `request_confirmation`
-- interactions table. It does NOT touch:
--   - The Paperclip issues themselves
--   - The merged/closed GitHub PRs
--   - Any branches or commits
--   - Any of the work performed by the merge-dispatch routine
--
-- USAGE:
--   psql ... -f scripts/clean-stale-approvals.sql --variable mode=dry_run
--   # review the output
--   psql ... -f scripts/clean-stale-approvals.sql --variable mode=execute
-- =============================================================================

\set ON_ERROR_STOP on
\set ECHO none

-- mode is passed in via --variable mode=... (default 'dry_run')
-- :mode is the psql variable substitution syntax.

-- -----------------------------------------------------------------------------
-- Step 0: Safety guard — refuse to run if mode != 'execute'
-- -----------------------------------------------------------------------------
SELECT
  CASE
    WHEN :'mode' = 'execute' THEN '⚠️  EXECUTE MODE — updates will be applied'
    WHEN :'mode' = 'dry_run'  THEN '🔍 DRY-RUN MODE — no updates will be applied'
    ELSE 'ERROR: :mode must be "execute" or "dry_run" (got: ' || :'mode' || ')'
  END AS run_mode;
\echo

-- -----------------------------------------------------------------------------
-- Step 1: Build the candidate set
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS _candidates;
CREATE TEMP TABLE _candidates AS
WITH candidates AS (
  SELECT
    iti.id,
    i.identifier,
    i.status AS issue_status,
    iti.status AS int_status,
    iti.idempotency_key,
    iti.payload->>'prompt' AS prompt,
    (iti.payload->>'prompt') ~ 'https://github.com/[^/]+/[^/]+/pull/([0-9]+)' AS has_pr,
    (iti.payload->>'prompt') ~ 'Fix-SHA: ([0-9a-f]{40})' AS has_sha,
    substring(iti.payload->>'prompt' from 'Fix-SHA: ([0-9a-f]{40})') AS fix_sha,
    substring(iti.payload->>'prompt' from 'https://github.com/[^/]+/[^/]+/pull/([0-9]+)') AS pr_number
  FROM issue_thread_interactions iti
  JOIN issues i ON i.id = iti.issue_id
  WHERE iti.company_id = '73419cf3-bd37-4a7c-8782-311ccb47fced'
    AND iti.kind = 'request_confirmation'
    AND iti.status = 'pending'
    AND i.hidden_at IS NULL
)
SELECT
  c.*,
  -- Categorize the reason for resolution
  CASE
    -- BTCAAAAA-38474 has TWO pending approvals; the older one
    -- (`pr271-approval-v2` from 14:00) is superseded by the newer
    -- one (`pr271:157302bf` from 16:34) which mentions CI is now
    -- green. The older one is a stale retry.
    WHEN identifier = 'BTCAAAAA-38474'
         AND idempotency_key = 'confirmation:BTCAAAAA-38474:pr271-approval-v2'
    THEN 'duplicate_older_approval'

    -- BTCAAAAA-34618 — plan approval whose children (BTCAAAAA-34619,
    -- BTCAAAAA-34620) are already resolved, so the parent approval is
    -- moot.
    WHEN identifier = 'BTCAAAAA-34618'
    THEN 'children_already_completed'

    -- Generic stale: issue is done/cancelled but the approval was
    -- never explicitly resolved. The work was done via merge-dispatch,
    -- a different PR/SHA, or the issue was marked done by the operator.
    WHEN issue_status IN ('done', 'cancelled')
    THEN 'superseded_by_completed_work'

    -- Safety net: anything else is left untouched. We log it so the
    -- operator can investigate.
    ELSE 'leave_untouched'
  END AS reason
FROM candidates c;

-- -----------------------------------------------------------------------------
-- Step 2: Show the categorization (always, in both modes)
-- -----------------------------------------------------------------------------
\echo 'Categorization of pending request_confirmation approvals:'
SELECT
  reason,
  count(*) AS n,
  count(*) FILTER (WHERE has_pr)  AS with_pr_ref,
  count(*) FILTER (WHERE has_sha) AS with_sha_ref
FROM _candidates
GROUP BY reason
ORDER BY n DESC;

\echo
\echo 'Detail of candidates that would be resolved (excludes leave_untouched):'
SELECT
  cand.identifier,
  cand.issue_status,
  cand.pr_number,
  substring(cand.fix_sha, 1, 12) AS sha_prefix,
  cand.reason,
  substring(iti.idempotency_key, 1, 60) AS idem_key,
  to_char(iti.created_at, 'YYYY-MM-DD HH24:MI') AS created
FROM _candidates cand
JOIN issue_thread_interactions iti ON iti.id = cand.id
WHERE cand.reason != 'leave_untouched'
ORDER BY cand.reason, cand.identifier
LIMIT 200;

\echo
\echo 'Detail of approvals we will NOT touch (safety check):'
SELECT
  identifier,
  issue_status,
  reason,
  idem_key
FROM (
  SELECT
    cand.identifier,
    cand.issue_status,
    cand.reason,
    iti.idempotency_key AS idem_key
  FROM _candidates cand
  JOIN issue_thread_interactions iti ON iti.id = cand.id
) sub
WHERE reason = 'leave_untouched';

-- -----------------------------------------------------------------------------
-- Step 3: Apply updates — only when mode = 'execute'
-- -----------------------------------------------------------------------------
\echo
SELECT
  CASE
    WHEN :'mode' = 'execute' THEN '>>> applying updates <<<'
    ELSE '>>> dry run, no updates applied <<<'
  END AS update_phase;

UPDATE issue_thread_interactions iti
SET
  status = 'cancelled',
  result = jsonb_build_object(
    'outcome',          reason,
    'version',          1,
    'resolved_at_iso',  to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    'resolved_by',      'local-board',
    'resolved_via',     'clean-stale-approvals.sql',
    'note',             'Work was completed via a different path (merge-dispatch, ' ||
                          'different PR/SHA, or operator action). The original approval ' ||
                          'request is no longer needed.'
  ),
  resolved_at = now(),
  resolved_by_user_id = 'local-board',
  resolved_by_agent_id = NULL
FROM _candidates c
WHERE iti.id = c.id
  AND c.reason != 'leave_untouched'
  AND :'mode' = 'execute';

\echo
SELECT 'Updated rows: ' ||
  CASE WHEN :'mode' = 'execute'
    THEN (SELECT count(*)::text FROM _candidates WHERE reason != 'leave_untouched')
    ELSE '0 (dry run)'
  END AS result;

-- -----------------------------------------------------------------------------
-- Step 4: Post-update verification
-- -----------------------------------------------------------------------------
\echo
\echo 'POST-UPDATE STATE:'
SELECT
  CASE
    WHEN iti.result IS NOT NULL THEN 'resolved'
    WHEN i.status IN ('done','cancelled') THEN 'stale_still_pending'
    ELSE 'actionable_still_pending'
  END AS bucket,
  count(*) AS n
FROM issue_thread_interactions iti
JOIN issues i ON i.id = iti.issue_id
WHERE iti.company_id = '73419cf3-bd37-4a7c-8782-311ccb47fced'
  AND iti.kind = 'request_confirmation'
GROUP BY bucket
ORDER BY n DESC;

\echo
\echo 'REMAINING ACTIONABLE APPROVALS (should be 1 — the newer BTCAAAAA-38474 PR #271):'
SELECT
  i.identifier,
  i.status,
  substring(iti.payload->>'prompt', 1, 100) AS prompt_head,
  iti.created_at::date
FROM issue_thread_interactions iti
JOIN issues i ON i.id = iti.issue_id
WHERE iti.company_id = '73419cf3-bd37-4a7c-8782-311ccb47fced'
  AND iti.kind = 'request_confirmation'
  AND iti.status = 'pending'
  AND i.hidden_at IS NULL
  AND i.status NOT IN ('done','cancelled');
