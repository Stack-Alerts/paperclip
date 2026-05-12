# Blast Radius Worker

Detects fix/bug issues transitioning to `in_review` and posts a **Blast Radius
Report** as a comment on the issue.

## Architecture

```
Paperclip Issue (fix→in_review)
       │
       ▼
Blast Radius Worker ──► 1. Fetch issue touchedFiles
  (poll/webhook)           2. Query Touch Index (PostgreSQL)
                           3. Generate markdown report
                           4. Post comment on issue
                           5. @-mention impacted FR owners
```

### Components

| Module | Path | Purpose |
|--------|------|---------|
| `worker` | `src/blast_radius/worker.py` | Poll loop, transition detection, state persistence |
| `generator` | `src/blast_radius/generator.py` | Generate report and post as Paperclip comment |
| `report` | `src/blast_radius/report.py` | Markdown renderer for the report |
| `query` | `src/blast_radius/query.py` | Touch Index DB queries (FR impact, regression risk) |
| `db` | `src/blast_radius/db.py` | PostgreSQL engine (delegates to `touch_index.db`) |
| `api_server` | `src/blast_radius/api_server.py` | HTTP API for queries + webhooks |
| Unified CLI | `src/blast_radius/__main__.py` (via `python -m blast_radius`) | Primary CLI with subcommands (worker, query, generate, serve) |
| CLI (legacy) | `scripts/blast_radius_cli.py` | Thin wrapper that delegates to the unified CLI |
| Runner | `scripts/run_blast_radius_worker.py` | Thin wrapper that sets up env and delegates to the unified CLI |

### Database Tables

- `touch_index_fr_files` — file→FR mapping (FR Impact Set)
- `touch_index_bug_files` — file→bug mapping (Regression Risk)
- `touch_index_file_deps` — dependency graph (Phase 2 downstream)

## Operation

### Trigger modes

1. **Schedule (polling):** GitHub Actions cron every 5 minutes via
   `.github/workflows/blast-radius-worker.yml`. Fetches all `in_review`
   issues, detects fix→in_review transitions, posts reports.

2. **Webhook (event-driven):** Paperclip
   `issue_status_changed` webhook → `repository_dispatch` → workflow
   processes single issue via `--issue-id` + `--old-status`.

3. **Manual:** `workflow_dispatch` via GitHub UI with optional
   `--dry-run` and `--force-reprocess` flags.

### Transition Detection

State is persisted in `data/blast_radius_worker_state.json` (cached across
workflow runs via `actions/cache`).

```json
{
  "processed_issue_ids": ["<uuid>", ...],
  "issue_statuses": {"<uuid>": "in_review", ...}
}
```

An issue is considered a **new transition** when its previous known status
(from `issue_statuses`) was *not* `in_review`. Never-seen-before issues
are treated as transitions.

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env with PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
# and POSTGRES_* credentials

# Run once (poll mode)
python -m blast_radius

# Process a single issue (webhook simulation)
python -m blast_radius --issue-id <uuid> --old-status in_progress

# Dry run (log report, don't post)
python -m blast_radius --dry-run

# Loop mode (poll every 60s)
python -m blast_radius --loop 60

# Using the standalone runner script
python scripts/run_blast_radius_worker.py

# Using the legacy CLI
python scripts/blast_radius_cli.py worker --dry-run
```

### Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Log reports but do not post comments or save state |
| `--force-reprocess` | Re-process already-seen issues (bypasses transition detection + dedup guard) |
| `--loop <sec>` | Run in a continuous loop with the given interval |
| `--issue-id <uuid>` | Process a single issue by Paperclip UUID |
| `--old-status <status>` | Previous issue status (from status-change webhook) |

## GitHub Actions Workflow

File: `.github/workflows/blast-radius-worker.yml`

- Runs every 5 minutes via cron
- Restores worker state from previous run cache
- Runs the worker (detect transitions → post reports)
- Saves updated state to cache

## Monitoring & Debugging

### Workflow logs

Check GitHub Actions → Blast Radius Worker → most recent run.
The worker logs:
- Number of `in_review` issues fetched
- Number of fix→in_review transitions detected
- Each report generation (issue identifier)
- Any errors (API failures, DB connection issues)

### Cache state

Worker state is cached at `data/blast_radius_worker_state.json`. To force
reprocessing all issues, use `workflow_dispatch` with `force_reprocess=true`.

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No touchedFiles found | Issue description missing touchedFiles | Add `touchedFiles` to issue description |
| Skipping — already processed | Issue was processed in prior run | Use `force_reprocess=true` |
| DB connection errors | PostgreSQL credentials missing | Check `POSTGRES_*` secrets |
| API auth errors | Paperclip API key invalid/expired | Rotate `PAPERCLIP_API_KEY` |

## Rollback

If a blast radius report is posted in error:
1. Delete the comment from the Paperclip issue manually
2. If the issue should be re-processed, trigger workflow with
   `force_reprocess=true`
3. No state changes are irreversible — state is just a cache
