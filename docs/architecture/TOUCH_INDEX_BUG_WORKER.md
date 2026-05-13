# Touch Index Bug-Close Ingestion Worker

Ingests **bug fix** file references into the `touch_index_bug_files` table.
For each closed non-FDR issue, it discovers touched source files via git
commits that reference the issue identifier (e.g. `fix(BTCAAAAA-1202)`),
with a fallback to Paperclip issue comments.  FDR-labelled issues are
excluded (handled by the FR worker).

This powers:
- **Blast radius analysis** — which files were affected by a bug fix
- **Regression risk assessment** — files changed by many bug fixes are higher risk
- **Cross-reference lookups** — given a file, find all bug fixes that touched it

## Architecture

```
Paperclip non-FDR Issue (status→done)
       │
       ▼
Bug Ingestion Worker ──► 1. Git commit scan (primary — conventional commits)
  (poll/webhook)            2. Fall back to Paperclip issue comments
                            3. Upsert (file_path, bug_issue_id) rows
                            4. Transition issue to done (if not already)
                            5. Validate data quality (optional --validate)
```

### Components

| Module | Path | Purpose |
|--------|------|---------|
| `bug_worker` | `src/touch_index/bug_worker.py` | Core ingestion: git-or-comments extraction, upsert, batch/ single-issue processing |
| `git_extractor` | `src/touch_index/git_extractor.py` | Find commits referencing an issue identifier via `git log --grep` and collect changed files |
| `comment_extractor` | `src/touch_index/comment_extractor.py` | Extract file paths from Paperclip issue comments/description text (fallback) |
| `paperclip_client` | `src/touch_index/paperclip_client.py` | Thin Paperclip API client for issue CRUD, pagination, and status transitions |
| `db` | `src/touch_index/db.py` | PostgreSQL engine factory and health check |
| `quality` | `src/touch_index/quality.py` | Coverage, freshness, and consistency checks for `touch_index_bug_files` |
| CLI | `src/touch_index/__main__.py` | Unified CLI dispatcher: `python -m touch_index bug [options]` |
| Runner | `scripts/run_touch_index_bug_worker.py` | Standalone runner with env setup (load_dotenv, sys.path) |
| Validate | `scripts/validate_touch_index_bug.py` | Standalone validation script with `--stale-days` flag |
| Migration | `alembic/versions/20260511_add_touch_index_tables.py` | Schema creation for all touch_index tables |

### File Extraction Strategy

The worker tries three sources in order, stopping when files are found:

1. **Git commits (primary — highest signal):** Runs
   `git log --all --grep=<identifier>` to find commits referencing the bug
   issue identifier (e.g. `BTCAAAAA-1202`), then collects files from
   `git show --name-only --diff-filter=ACMRT`.  Filters out generated files
   (`.sql`, `.json`, `.lock`, `.md`, etc.), alembic migrations, docs,
   and scripts/LakeAPI outputs.  This is the primary path because the
   project enforces conventional commits with issue IDs in the scope token
   (e.g. `fix(BTCAAAAA-1202): correct cache key`).

2. **Issue comments (fallback):** If git returns no results (e.g. the fix
   was deployed without a conventional commit), the worker fetches the
   issue's Paperclip comments and extracts file paths via regex on
   backtick-wrapped paths and bare path patterns.  Same source-file filter
   is applied for consistency.

3. **Issue description (lowest signal):** If both git and comments return
   no results, the worker parses the issue body text via the same
   `extract_files_from_text()` function used for comments.  This catches
   cases where the issue description explicitly lists touched files but no
   agent done-comment or fix commit exists.

If all three sources return nothing, the issue is skipped (logged with
`skipped_no_commits=True` and `source='none'`).

### Idempotent Upsert

The database upsert uses `INSERT ... ON CONFLICT (file_path, bug_issue_id)
DO UPDATE SET closed_at = COALESCE(EXCLUDED.closed_at, ...)`.  This means
re-running the same issue is safe — duplicates are never created, and
`closed_at` is preserved if a previous run already set it.

## Database

### Table: `touch_index_bug_files`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key, auto-generated via `gen_random_uuid()` |
| `file_path` | TEXT | NO | Repo-relative path to the affected source file |
| `bug_issue_id` | UUID | NO | Paperclip issue UUID for the bug fix |
| `bug_identifier` | TEXT | NO | Human-readable issue identifier (e.g. `BTCAAAAA-1202`) |
| `closed_at` | TIMESTAMPTZ | YES | When the bug was closed (nullable — some Paperclip issues lack `completedAt`) |
| `source` | TEXT | NO | Origin of file reference: `git`, `comments`, or `unknown` (default) |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE on `(file_path, bug_issue_id)` — idempotent upsert constraint
- INDEX on `file_path` — fast file-to-bug lookups

## Operation

### Trigger modes

1. **Schedule (polling):** GitHub Actions cron every 15 minutes via
   `.github/workflows/touch-index-bug-worker.yml`.  Queries Paperclip for
   all done non-FDR issues closed in the last 30 minutes (overlap window
   avoids gaps), processes them, transitions to `done`, and runs optional
   validation.

2. **Webhook (event-driven):** Paperclip `issue_created`/`issue_updated`/
   `issue_status_changed` webhooks → `repository_dispatch` → workflow
   processes single issue via `--issue-id`.

3. **Manual:** `workflow_dispatch` via GitHub UI with optional
   `--issue-id`, `--lookback-minutes`, `--dry-run`, and `--validate` flags.

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env with PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
# and POSTGRES_* credentials

# Poll mode (process bugs closed in last 30 min)
python scripts/run_touch_index_bug_worker.py

# Process a single issue (webhook simulation)
python scripts/run_touch_index_bug_worker.py --issue-id <uuid>

# Dry run (log what would be ingested, don't write to DB)
python scripts/run_touch_index_bug_worker.py --dry-run

# Custom lookback window
python scripts/run_touch_index_bug_worker.py --lookback-minutes 60

# Run with validation
python scripts/run_touch_index_bug_worker.py --validate

# Via the package CLI
python -m touch_index bug
python -m touch_index bug --issue-id <uuid> --dry-run
```

### Flags

| Flag | Description |
|------|-------------|
| `--issue-id <uuid>` | Process a single non-FDR issue by Paperclip UUID |
| `--lookback-minutes <N>` | Process bugs closed within N minutes (default: 30) |
| `--dry-run` | Log what would be ingested without writing to DB or transitioning issues |
| `--validate` | Run bug data quality validation after ingestion (exits non-zero on failure) |

## Data Quality & SLAs

Validated by `scripts/validate_touch_index_bug.py` and
`src/touch_index/quality.py`.  The following checks run after every
ingestion:

| Check | SLA | Action |
|-------|-----|--------|
| Coverage >= 90% | Done non-FDR issues in `touch_index_bug_files` / total done non-FDR issues | Missing issues must be backfilled |
| Freshness < 30d | All rows have `updated_at` within 30 days | Stale rows indicate pipeline stall |
| Consistency | No duplicate `(file_path, bug_issue_id)` pairs | Duplicates break blast radius queries |
| No orphan `bug_issue_id` | Every `bug_issue_id` resolves in Paperclip | Deleted issues must be purged |

**Coverage denominator:** The bug worker indexes *done non-FDR issues that
have git commits or comments referencing them*.  Issues without any
extractable file references are counted as "skipped" in the summary
but still count toward coverage targets.

## Backfill

For initial population or gap recovery, run the backfill script:

```bash
python scripts/backfill_touch_index.py --days 90
```

The backfill scans git log for all commits in the window that reference
`BTCAAAAA-NNN` identifiers, looks up each issue in Paperclip, and ingests
done non-FDR issues (the same logic as the polling worker but with a
longer window and no transition-to-done, since those issues are already
closed).

## GitHub Actions Workflow

File: `.github/workflows/touch-index-bug-worker.yml`

- Runs every 15 minutes via cron (`*/15 * * * *`)
- Accepts `repository_dispatch` for webhook triggers
- Supports `workflow_dispatch` with `issue_id` and `lookback_minutes` inputs
- Validates data quality after ingestion (`if: always()`)
- Concurrency group `touch-index-bug-worker` prevents overlapping runs

## Testing

All tests mock external I/O (DB engine, Paperclip API, git subprocess)
so they run fully offline:

```bash
# Run bug worker unit tests
python -m pytest tests/test_touch_index/test_bug_worker.py -v

# Run runner tests
python -m pytest tests/test_touch_index/test_bug_runner.py -v

# Run validation tests
python -m pytest tests/test_touch_index/test_validate_bug.py -v

# Run all touch index tests
python -m pytest tests/test_touch_index/ -v
```

## Monitoring & Debugging

### Workflow logs

Check GitHub Actions → Touch Index Bug Worker → most recent run.
The worker logs:
- Number of closed non-FDR issues fetched
- File extraction source (git/comments/none)
- Files indexed per issue
- Database health check status
- Any API failures or DB errors

### Validation failures

If `--validate` flags fail:
1. Check the validation output in the workflow logs
2. Run validation locally: `python scripts/validate_touch_index_bug.py`
3. Investigate missing issues, stale rows, or consistency problems
4. Backfill using `python scripts/backfill_touch_index.py --days N`

### Common issues

| Symptom | Cause | Fix |
|---------|-------|------|
| No files indexed for issue | No git commits or comments referencing the issue | Check issue has conventional commit messages or done-comment with file paths |
| DB connection errors | PostgreSQL credentials missing | Check `POSTGRES_*` environment variables |
| API auth errors | Paperclip API key invalid/expired | Rotate `PAPERCLIP_API_KEY` |
| Validation: low coverage | New bugs ingested but coverage threshold not met | Check for non-indexed issues; run backfill if needed |
| Duplicate pairs | Race condition on concurrent runs | Check concurrency group in workflow config |

## Related

- [Database Guide §9 touch_index_bug_files](DATABASE_GUIDE.md#9-touch_index_bug_files)
- [Touch Index FR Worker](TOUCH_INDEX_FR_WORKER.md) — FDR/FR ingestion counterpart
- [Blast Radius Worker](BLAST_RADIUS_WORKER.md) — consumes touch_index tables for impact reports
- [Bug Worker CI/CD](../.github/workflows/touch-index-bug-worker.yml)
