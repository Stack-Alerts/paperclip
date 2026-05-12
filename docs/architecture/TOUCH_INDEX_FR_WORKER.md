# Touch Index FR Ingestion Worker

Ingests **Feature Design Requirement (FDR/FR)** issue file references into the
`touch_index_fr_files` table.  This tracks which source files were
created/modified for each FR, enabling blast radius analysis, file→FR
lookups, and impact assessment.

## Architecture

```
Paperclip FDR Issue (created/updated→done)
       │
       ▼
FR Ingestion Worker ──► 1. Fetch comments (highest-signal file paths)
  (poll/webhook)           2. Fall back to git commit messages
                           3. Fall back to issue description
                           4. Upsert (file_path, fr_issue_id) rows
                           5. Transition issue to done
                           6. Validate data quality (optional)
```

### Components

| Module | Path | Purpose |
|--------|------|---------|
| `fr_worker` | `src/touch_index/fr_worker.py` | Core ingestion: file extraction, upsert, batch processing |
| `comment_extractor` | `src/touch_index/comment_extractor.py` | Extract file paths from Paperclip issue comments/description text |
| `git_extractor` | `src/touch_index/git_extractor.py` | Find commits referencing an issue identifier and collect changed files |
| `db` | `src/touch_index/db.py` | PostgreSQL engine factory and health check |
| `paperclip_client` | `src/touch_index/paperclip_client.py` | Thin Paperclip API client for issue CRUD and pagination |
| `quality` | `src/touch_index/quality.py` | Coverage, freshness, and consistency checks for `touch_index_fr_files` |
| CLI | `src/touch_index/__main__.py` | Unified CLI dispatcher: `python -m touch_index [fr\|bug]` |
| Runner | `scripts/run_touch_index_fr_worker.py` | Standalone runner with env setup (load_dotenv, sys.path) |
| Validate | `scripts/validate_touch_index_fr.py` | Standalone validation script with `--stale-hours` flag |
| Migration | `alembic/versions/20260511_add_touch_index_tables.py` | Schema creation for all touch_index tables |

### File Extraction Strategy (Priority Order)

The worker tries three sources in order, stopping when files are found:

1. **Comments (highest signal):** The implementing agent typically posts a
   done-comment naming the files they changed (e.g.
   ``src/optimizer_v3/database/strategy_manager.py``). Extracted via
   regex on backtick-wrapped paths and bare path patterns.

2. **Git commits:** Runs `git log --all --grep=<identifier>` to find
   commits referencing the FR identifier (e.g. `BTCAAAAA-1085`), then
   collects files from `git show --name-only --diff-filter=ACMRT`.
   Skips generated files (`.sql`, `.json`, `.lock`, `.md`, etc.).

3. **Description text (lowest signal):** Falls back to regex
   extraction on the issue description body if comments and git
   both return nothing. Catches spec-level file references.

## Database

### Table: `touch_index_fr_files`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key, auto-generated via `gen_random_uuid()` |
| `file_path` | TEXT | NO | Repo-relative path to the affected source file |
| `fr_issue_id` | UUID | NO | Paperclip issue UUID for the FR |
| `fr_identifier` | TEXT | NO | Human-readable issue identifier (e.g. `BTCAAAAA-1085`) |
| `fr_owner_agent_id` | UUID | NO | Agent UUID of the FR owner/assignee |
| `source` | TEXT | NO | Origin of the file reference: `comments`, `git`, or `description` |
| `updated_at` | TIMESTAMPTZ | NO | Last upsert timestamp (server default `now()`) |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE on `(file_path, fr_issue_id)` — idempotent upsert
- INDEX on `file_path` — fast file-to-FR lookups

**Ingestion:** Idempotent `INSERT ... ON CONFLICT DO UPDATE` — safe to
re-run the same issue multiple times without creating duplicates.

## Operation

### Trigger modes

1. **Schedule (polling):** GitHub Actions cron every 15 minutes via
   `.github/workflows/touch-index-fr-worker.yml`. Fetches all FDR issues
   updated in the last 30 minutes (overlap window avoids gaps), processes
   them, transitions to `done`, and runs optional validation.

2. **Webhook (event-driven):** Paperclip `issue_created`/`issue_updated`
   webhooks → `repository_dispatch` → workflow processes single issue
   via `--issue-id`.

3. **Manual:** `workflow_dispatch` via GitHub UI with optional
   `--lookback-minutes`, `--dry-run`, and `--validate` flags.

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env with PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
# and POSTGRES_* credentials

# Poll mode (process FDR issues updated in last 30 min)
python scripts/run_touch_index_fr_worker.py

# Process a single issue (webhook simulation)
python scripts/run_touch_index_fr_worker.py --issue-id <uuid>

# Dry run (log what would be ingested, don't write to DB)
python scripts/run_touch_index_fr_worker.py --dry-run

# Custom lookback window
python scripts/run_touch_index_fr_worker.py --lookback-minutes 60

# Run with validation
python scripts/run_touch_index_fr_worker.py --validate

# Via the package CLI
python -m touch_index fr
python -m touch_index fr --issue-id <uuid> --dry-run

# JSON summary output
python -m touch_index fr --json-summary
python -m touch_index fr --issue-id <uuid> --json-summary
```

### Flags

| Flag | Description |
|------|-------------|
| `--issue-id <uuid>` | Process a single FDR issue by Paperclip UUID |
| `--lookback-minutes <N>` | Process FDR issues updated within N minutes (default: 30) |
| `--dry-run` | Log what would be ingested without writing to DB or transitioning issues |
| `--validate` | Run FR data quality validation after ingestion (exits non-zero on failure) |
| `--json-summary` | Output structured JSON summary to stdout (includes per-issue result, quality report, and run metadata) |

## Data Quality & SLAs

Validated by `scripts/validate_touch_index_fr.py` and
`src/touch_index/quality.py`.  The following checks run after every
ingestion:

| Check | SLA | Action |
|-------|-----|--------|
| Coverage >= 90% | FDR issues in `touch_index_fr_files` / total FDR issues | Missing issues must be backfilled |
| Freshness < 168h | All rows updated within 7 days | Stale rows indicate pipeline stall |
| Consistency | No duplicate `(file_path, fr_issue_id)` pairs | Duplicates break blast radius queries |
| No NULL `updated_at` | Every row has a valid timestamp | Schema violation |
| No orphans | Every `fr_issue_id` resolves in Paperclip | Deleted issues must be purged |

## GitHub Actions Workflow

File: `.github/workflows/touch-index-fr-worker.yml`

- Runs every 15 minutes via cron (`*/15 * * * *`)
- Accepts `repository_dispatch` for webhook triggers
- Supports `workflow_dispatch` with `issue_id` and `lookback_minutes` inputs
- Validates data quality after ingestion (`if: always()`)
- Concurrency group `touch-index-fr-worker` prevents overlapping runs

## Testing

All tests mock external I/O (DB engine, Paperclip API, git subprocess)
so they run fully offline:

```bash
# Run FR worker unit tests
python -m pytest tests/test_touch_index/test_fr_worker.py -v

# Run runner tests
python -m pytest tests/test_touch_index/test_fr_runner.py -v

# Run validation tests
python -m pytest tests/test_touch_index/test_validate_fr.py -v

# Run all touch index tests
python -m pytest tests/test_touch_index/ -v
```

## Monitoring & Debugging

### Workflow logs

Check GitHub Actions → Touch Index FR Worker → most recent run.
The worker logs:
- Number of FDR issues fetched
- File extraction source (comments/git/description/none)
- Files indexed per issue
- Database health check status
- Any API failures or DB errors

### Validation failures

If `--validate` flags fail:
1. Check the validation output in the workflow logs
2. Run validation locally: `python scripts/validate_touch_index_fr.py`
3. Investigate missing issues, stale rows, or consistency problems
4. Backfill using `python scripts/run_touch_index_fr_worker.py --lookback-minutes 1440`

### Common issues

| Symptom | Cause | Fix |
|---------|-------|------|
| No files indexed for issue | No comments, git commits, or description mentioning the issue | Check issue has proper done-comment or conventional commit messages |
| DB connection errors | PostgreSQL credentials missing | Check `POSTGRES_*` environment variables |
| API auth errors | Paperclip API key invalid/expired | Rotate `PAPERCLIP_API_KEY` |
| Validation: low coverage | New FDR issues not yet ingested | Run worker with larger lookback window |
| Duplicate pairs | Race condition on concurrent runs | Check concurrency group in workflow config |

## Related

- [Database Guide §8 touch_index_fr_files](DATABASE_GUIDE.md#8-touch_index_fr_files)
- [Touch Index Bug Worker](TOUCH_INDEX_BUG_WORKER.md) — bug-close ingestion counterpart
- [Blast Radius Worker](BLAST_RADIUS_WORKER.md) — consumes touch_index_fr_files for impact reports
- [FR Worker CI/CD](../.github/workflows/touch-index-fr-worker.yml)
