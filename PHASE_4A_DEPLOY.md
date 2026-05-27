# Phase 4a: Merge-Dispatch Routine Deployment

**Issue:** [BTCAAAAA-30072](/BTCAAAAA/issues/BTCAAAAA-30072)  
**Script:** `scripts/merge_dispatch_routine.py`  
**Cadence:** Every 5 minutes  
**Owner:** AutomationEngineer

## Overview

The merge-dispatch routine automatically processes `in_review` issues with valid Fix-SHA tags and recent `merge_request` interactions, opens PRs via GitHub API, merges them with squash, and updates issue status to `done`. Failures escalate to [BTCAAAAA-30033](/BTCAAAAA/issues/BTCAAAAA-30033).

## Script Behavior

The routine:
1. Scans all `in_review` issues
2. Checks for `merge_request` interaction in the last hour
3. Extracts `Fix-SHA: <40-char-sha>` from closure comments
4. Verifies SHA exists locally, fetches from remote if needed
5. Finds the branch containing the SHA
6. Creates PR via GitHub API (uses CEO's `GH_TOKEN` — RepoSteward token doesn't work on BTC repo)
7. Merges PR with squash
8. Comments on source issue with merge result
9. Sets issue status to `done`
10. On failure at any step, escalates to [BTCAAAAA-30033](/BTCAAAAA/issues/BTCAAAAA-30033)

## Setup Instructions

### Prerequisites

Required environment variables (set on the Paperclip routine runner):
- `PAPERCLIP_API_URL`: Paperclip API endpoint
- `PAPERCLIP_API_KEY`: Bearer token for Paperclip API
- `PAPERCLIP_COMPANY_ID`: Company ID
- `GH_TOKEN`: CEO's GitHub token (has admin access to Stack-Alerts/BTC-Trade-Engine-PaperClip)

Required local environment:
- Git repository cloned at `/home/sirrus/projects/BTC-Trade-Engine-PaperClip`
- Python 3.9+
- `requests` library

### Creating the Routine

```bash
# Manual creation via API (requires PAPERCLIP_API_KEY set)
curl -X POST "https://stack-alerts.paperclipai.com/api/companies/{COMPANY_ID}/routines" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Phase 4a: Merge-Dispatch Routine",
    "description": "Automatically open and merge PRs for in_review issues with valid Fix-SHA and recent merge_request interactions. Runs every 5 minutes.",
    "assigneeAgentId": "2b9152a6-07f6-4ae9-87fa-c824012c9ff6",
    "projectId": "{PROJECT_ID}",
    "priority": "high",
    "status": "active",
    "concurrencyPolicy": "coalesce_if_active",
    "catchUpPolicy": "skip_missed"
  }'
```

### Adding the Cron Trigger

After creating the routine, add a schedule trigger:

```bash
curl -X POST "https://stack-alerts.paperclipai.com/api/routines/{ROUTINE_ID}/triggers" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "schedule",
    "cronExpression": "*/5 * * * *",
    "timezone": "UTC",
    "label": "Every 5 minutes"
  }'
```

### Configuring the Run Command

When the routine fires, it creates an execution issue. Configure that issue's workspace to run:

```bash
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && \
python3 scripts/merge_dispatch_routine.py
```

Ensure the runtime has:
- Access to the repo directory
- Environment variables: `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `PAPERCLIP_COMPANY_ID`, `GH_TOKEN`
- Git binary available

## Testing

### Local Test Run

```bash
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
python3 scripts/merge_dispatch_routine.py
```

Expected output: JSON summary with `merged`, `skipped`, `failed`, and `errors` counts.

### Test with Merge Request Interaction

To test the full flow:
1. Create an `in_review` issue with a valid `Fix-SHA` in a closure comment
2. Manually add a `merge_request` interaction to the issue (via Paperclip API or UI)
3. Run the routine
4. Verify the PR was created and merged

## Monitoring and Escalation

- **Success:** Routine logs JSON output showing `merged` count > 0
- **Failure:** Escalates to [BTCAAAAA-30033](/BTCAAAAA/issues/BTCAAAAA-30033) with issue details
- **Tracking:** Routine's own tracking issue is [BTCAAAAA-30048](/BTCAAAAA/issues/BTCAAAAA-30048)

## Key Constraints

1. **GitHub Token:** Uses CEO's `GH_TOKEN` because RepoSteward's token 404s on BTC-Trade-Engine-PaperClip (free private repo limitation)
2. **Concurrency:** Set to `coalesce_if_active` — multiple 5-min intervals collapse into one run if the previous one is still active
3. **Catch-up:** Set to `skip_missed` — if Paperclip is down, missed runs are dropped (not queued)
4. **Idempotency:** Each run checks for existing PRs before creating new ones

## Implementation Status

- ✅ Script implementation complete (`scripts/merge_dispatch_routine.py`)
- ✅ Local testing passes (33 in_review issues scanned, 0 processed, 0 errors)
- ⏳ Routine setup in Paperclip (requires board or CEO authorization)
- ⏳ Integration into deployment pipeline
- ⏳ Monitoring dashboard

## Related Issues

- **Phase 4c (Escalation):** [BTCAAAAA-30033](/BTCAAAAA/issues/BTCAAAAA-30033) — failure escalation routine
- **Phase 4b (Branch Protection):** [BTCAAAAA-30051](/BTCAAAAA/issues/BTCAAAAA-30051) — GitHub branch protection rules
- **Phase 3 (Closure-Gate):** [BTCAAAAA-30047](/BTCAAAAA/issues/BTCAAAAA-30047) — Fix-SHA validation sweep
- **Umbrella:** [BTCAAAAA-30038](/BTCAAAAA/issues/BTCAAAAA-30038) — Zero-tolerance merge governance

## References

- AGENTS.md: Section on merge-governance Fix-SHA contract and merge-dispatch flow
- Memory: `project_merge_governance_audit_30038.md` — Phase tracking and dependencies
- Script: `scripts/merge_dispatch_routine.py` — Full implementation with error handling
