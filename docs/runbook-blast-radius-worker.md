# Runbook: Blast Radius Worker

## Overview

The Blast Radius Worker polls the Paperclip API for fix/bug issues that have
transitioned to `in_review`, generates a **Blast Radius Report** for each, and
posts the report as a comment on the issue.

The report lists:
- **Touched files** — the files modified by the fix
- **FR Impact Set** — feature requests whose touched files overlap with the fix
  (including the owning agent @-mention)
- **Regression Risk** — historical bugs whose files overlap with the fix
- **Downstream impact** — files that depend on touched files (Phase 2 / dep
  graph pending)

Transition detection is explicit: the worker tracks the last-known status of
each issue in a state file and only generates reports when the previous status
was *not* `in_review`. This avoids re-processing issues that were already
`in_review` during a prior poll cycle.

## Architecture

```
Paperclip API          Blast Radius Worker          Touch Index DB
    │                        │                            │
    │───in_review issues────>│                            │
    │                        ├───query touched files──────>│
    │                        │<──FR impact + regressions──│
    │                        │                            │
    │<──post report comment──│                            │
    │                        │                            │
    │────persist state───────│(data/blast_radius_worker_state.json)
```

### State file

Stored at `data/blast_radius_worker_state.json` (overridable via env var
`BLAST_RADIUS_STATE_FILE`). Shape:

```json
{
  "processed_issue_ids": ["uuid-1", "uuid-2"],
  "issue_statuses": {"uuid-1": "in_review", "uuid-2": "done"}
}
```

- `processed_issue_ids`: issues that have had a report successfully posted.
- `issue_statuses`: last-known status of every fetched `in_review` issue, used
  to detect transitions on the next poll.

**Stale entry cleanup**: when an issue that was `in_review` is no longer
returned by the API, its entry is removed so a future re-transition to
`in_review` is correctly detected.

**Failed/skipped cleanup**: issues that fail generation or are skipped (no
touchedFiles) have their status entries removed so they are re-detected on the
next poll.

**Self-close on single-issue processing**: when the worker processes an issue
via ``--issue-id`` (webhook or manual trigger), after successfully posting the
Blast Radius Report, it transitions the issue to **done** via
``transition_issue_status_board()``.  This prevents routine execution issues
from accumulating in ``in_review``.  The self-close is skipped when:
- ``--dry-run`` is set (no API calls are made)
- The report is skipped (e.g. no ``touchedFiles``)
- The issue was already processed (normal dedup)

## CLI Usage

### Poll once (default)

```bash
cd /path/to/repo
PYTHONPATH=src python -m blast_radius
```

### Single issue (webhook trigger)

```bash
python -m blast_radius --issue-id <uuid> [--old-status in_progress]
```

### Polling loop

```bash
python -m blast_radius --loop 120
```

### Flags

| Flag | Description |
|---|---|
| `--dry-run` | Log reports, do not post comments |
| `--force-reprocess` | Re-process already-seen issues (bypasses transition detection) |
| `--json-summary` | Output structured JSON summary to stdout |
| `--issue-id <uuid>` | Process a single issue |
| `--old-status <status>` | Previous status (from webhook) |
| `--loop <seconds>` | Run continuously with given interval |
| `-v / --verbose` | Enable debug logging |

### Subcommands

```bash
python -m blast_radius worker [--dry-run]          # poll worker (default)
python -m blast_radius query --files src/a.py       # query Touch Index
python -m blast_radius generate --issue-id <uuid>   # generate + post one report
python -m blast_radius serve --port 8765             # HTTP API server
```

Flat args (no subcommand) are treated as the `worker` subcommand:
```bash
python -m blast_radius --dry-run         # same as: worker --dry-run
```

## CI/CD Pipeline

Workflow: `.github/workflows/blast-radius-worker.yml`

### Triggers

| Trigger | Schedule / Event |
|---|---|
| `schedule` | Every 5 minutes (`*/5 * * * *`) |
| `repository_dispatch` | `issue_status_changed` webhook event |
| `workflow_dispatch` | Manual trigger with optional `issue_id`, `old_status`, `dry_run`, `loop_seconds`, `force_reprocess` |

### Concurrency

Group: `blast-radius-worker` — `cancel-in-progress: false` ensures runs queue
rather than cancel each other.

### Step sequence

1. **Checkout** the repository
2. **Set up Python** 3.12
3. **Install dependencies** from `requirements.txt`
4. **Create data directory** (`mkdir -p data`)
5. **Restore worker state cache** — loads previous
   `blast_radius_worker_state.json` from GitHub Actions cache (restore key
   prefix `blast-radius-state-`)
6. **Resolve issue ID and old_status** from event payload (supports both
   `workflow_dispatch` inputs and `repository_dispatch` client_payload)
7. **Run worker** with appropriate flags — output captured to
   `/tmp/br-output.json` via `--json-summary`
8. **Upload worker output artifact** (always, even on failure) — saved as
   `blast-radius-worker-output` with 30-day retention for diagnostic access
9. **Write step summary** — renders a structured Markdown table with mode,
   dry-run flag, issues processed/errors, and skipped/error result when present
10. **Save worker state cache** (always, even on failure) — saved under key
   `blast-radius-state-<run_id>` for consumption by the next scheduled run

### Environment Variables

| Variable | Source | Purpose |
|---|---|---|
| `PAPERCLIP_API_URL` | Secret | Paperclip API base URL |
| `PAPERCLIP_API_KEY` | Secret | API authentication |
| `PAPERCLIP_COMPANY_ID` | Secret | Company/org ID |
| `PAPERCLIP_RUN_ID` | `github.run_id` | Traceability (passed in `X-Paperclip-Run-Id` header) |
| `POSTGRES_*` | Secrets | Touch Index DB connection |
| `PYTHONPATH` | `src` | Python module resolution |

## Local Development

### Setup

```bash
cd /path/to/repo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Run tests

```bash
# All blast radius tests
python -m pytest tests/test_blast_radius/ -v

# Worker-specific tests (74 tests)
python -m pytest tests/test_blast_radius/test_worker.py -v

# With coverage
python -m pytest tests/test_blast_radius/ \
  --cov=src/blast_radius --cov-report=term-missing
```

### Dry-run test

```bash
PYTHONPATH=src python -m blast_radius --dry-run
```

### Process a known issue

```bash
PYTHONPATH=src python -m blast_radius --issue-id <uuid> --dry-run
```

## FIX_LABELS Configuration

Controls which labels mark an issue as a fix/bug. Set via `FIX_LABELS` env var
(comma-separated, case-insensitive):

```bash
export FIX_LABELS="fix,bug,regression,hotfix"
```

Default: `fix,bug,bugfix`

Title-based fallback: if no label matches, the issue title is scanned for
keywords `fix`, `bug`, `regression`, `hotfix`.

## Transition Detection Algorithm

1. Fetch all `in_review` issues from Paperclip API.
2. Filter to fix/bug issues (labels + title fallback).
3. Compare each issue's ID against `issue_statuses` state map:
   - Never seen before → transition (process it)
   - Last known status was NOT `in_review` → transition (process it)
   - Last known status was `in_review` → NOT a transition (skip it)
4. After processing, bulk-sync statuses for ALL fetched issues.
5. Remove stale `in_review` entries no longer in the fetched set.
6. Remove status entries for failed/skipped candidates so they re-detect.

## Rollback Procedure

If the worker begins posting incorrect or malformed reports:

1. **Disable the workflow:** Navigate to GitHub → Actions → Blast Radius
   Worker → ⋮ → Disable workflow.
2. **Remove state file:** Delete `data/blast_radius_worker_state.json` to reset
   transition tracking on re-enable.
3. **Revert worker code** to the last known-good commit:
   ```bash
   git revert <bad-commit-hash> --no-edit
   git push origin main
   ```
4. **Re-enable workflow** after the fix is deployed.

To manually clean up an incorrect report comment:
```bash
curl -X DELETE "$PAPERCLIP_API_URL/api/issues/$ISSUE_ID/comments/$COMMENT_ID" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY"
```

## Monitoring & Alerting

### Log Patterns

The worker logs at `INFO` level by default. Key log lines:

| Log pattern | Meaning |
|---|---|
| `Fetched N in_review issues` | Poll cycle started |
| `Detected N fix->in_review transition(s)` | New issues to process |
| `Generating Blast Radius Report for BTCAAAAA-NNN` | Report being generated |
| `Posted Blast Radius Report to BTCAAAAA-NNN` | Report successfully posted |
| `No touchedFiles found for issue` | Skipped — no touched files to analyze |
| `Marked N issues as processed` | State file updated |
| `Worker iteration failed` | Unhandled exception in loop |

The `--json-summary` flag outputs structured JSON for downstream automation.

### Automated Alerting

The **Blast Radius Monitor** (`scripts/blast_radius_monitor.py`) parses the
worker's JSON output and creates Paperclip alert issues when errors are
detected.  It runs in two contexts:

1. **Inline (every worker run):** The `blast-radius-worker.yml` workflow runs the
   monitor as a post-processing step after each poll cycle.  If the worker
   encountered errors processing any issues, a ``medium``- or ``critical``-priority
   Paperclip issue is created and assigned to the CTO.

2. **Scheduled health check (every 30 min):** The `blast-radius-monitor.yml`
   workflow downloads the latest worker output artifact and runs the monitor.  If
   no artifact is available (worker stale), it generates a staleness alert.

#### Alert severity rules

| Condition | Priority |
|---|---|
| Error rate > 50% of processed issues | `critical` |
| Any errors in a poll run | `medium` |
| Single-issue processing error | `medium` |
| Staleness (no recent artifact) | `medium` |
| Dry-run worker execution | _no alert_ |

#### Silencing alerts

To suppress alerts during maintenance:
1. Use `workflow_dispatch` on the worker with `dry_run: true`.
2. Or disable the monitor workflow: GitHub → Actions → Blast Radius Monitor → ⋮ → Disable workflow.

#### Deduplication

One alert issue is created per day.  Subsequent errors within the same day
append an update comment to the existing alert issue rather than creating
duplicates.  Alert issues carry the ``blast-radius-alert`` label for easy
filtering.

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| No reports posted | No fix/bug issues in `in_review` | Check Paperclip status filter |
| | Transition already detected | Check `issue_statuses` in state file |
| | State file corruption | Delete state file and restart |
| | API credentials missing | Verify `PAPERCLIP_API_*` env vars |
| | DB connection failure | Check `POSTGRES_*` env vars and DB reachability |
| Duplicate reports | State file lost (cache miss) | Expected on first run or after cache expiry |
| Reports for wrong issues | Labels misconfigured | Check `FIX_LABELS` env var |
| `generate_and_post` fails | API rate limit / timeout | Worker retries on next poll |
| `Skipped` result | No touchedFiles in issue | Use git fallback or add touchedFiles |

## Related Documents

- `src/blast_radius/worker.py` — Worker implementation
- `src/blast_radius/__main__.py` — CLI entry point
- `src/blast_radius/generator.py` — Report generation + posting
- `src/blast_radius/report.py` — Report markdown rendering
- `src/blast_radius/query.py` — Touch Index query helpers
- `src/blast_radius/api_server.py` — Optional HTTP API server
- `.github/workflows/blast-radius-worker.yml` — CI/CD workflow
- `.github/workflows/blast-radius-monitor.yml` — Monitoring & alerting workflow
- `scripts/blast_radius_monitor.py` — Worker health monitoring script
- `data/blast_radius_worker_state.json` — Persisted worker state

## Done-Guard (BTCAAAAA-25832)

The `_post_comment()` function in `generator.py` includes a done-guard that
checks `is_issue_done()` before posting a Blast Radius report. If the issue is
already in `done` status, the comment is silently skipped to prevent the
Paperclip platform from reopening the issue on comment (which would create an
infinite wake loop).

The guard is fail-safe: if the status check itself fails (network error, etc.),
the comment is still posted rather than being silently dropped.

See `docs/runbook-impact-gate-scan-done.md#done-guard-btcaaaaa-25832` for the
full multi-layer guard architecture.
