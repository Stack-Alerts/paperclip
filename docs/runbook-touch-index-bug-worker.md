# Runbook: Touch Index Bug-Close Ingestion Worker

## Overview

The Touch Index Bug-Close Ingestion Worker maintains the `touch_index_bug_files`
table in PostgreSQL — a data catalog that tracks which source files were touched
by each closed bug issue (non-FDR issues with fix commits).

This data powers:
- **Blast Radius** — when a file is modified, the system queries
  `touch_index_bug_files` to identify past bugs that touched the same file
  (regression risk)
- **Impact Gate** — validates that fix issues don't reintroduce past bugs
- **Data Catalog** — provides clean file-reference APIs for backtesting and
  strategy analysis

## Architecture

```
                    Paperclip API
                         |
    +--------------------+--------------------+
    |                    |                    |
    v                    v                    v
  Bug Worker         FR Worker           Blast Radius
  (this worker)      (sibling)          (consumer)

  Bug Worker flow:
    1. Poll Paperclip for done non-FDR issues closed in last N minutes
       (or process a single issue via webhook)
    2. For each issue, extract file paths (priority order):
       a. Git history — commits referencing the issue identifier
       b. Comments — agent comments mentioning file paths
       c. Issue description — lower-signal text extraction
    3. Upsert rows into touch_index_bug_files
    4. Transition each processed issue to "done"
    5. Run data quality validation (optional)
```

### File extraction strategy

| Priority | Source | Signal | How it works |
|----------|--------|--------|--------------|
| 1 (best) | **Git history** | High | `git_extractor.get_files_for_issue()` — finds commits whose message contains the issue ID |
| 2 | **Comments** | Medium | `comment_extractor.fetch_and_extract()` — parses backtick-wrapped and bare paths from issue comments |
| 3 | **Description** | Low | `comment_extractor.extract_files_from_text()` — parses the issue body text |

Bug worker prioritises git over comments (opposite of FR worker) because bug
fixes have dedicated fix commits in git history, while FR issues rely on the
implementing agent's done-comment.

## CLI Usage

### Polling mode (default)

```bash
cd /path/to/repo
PYTHONPATH=src python -m touch_index bug
```

### Single issue (webhook trigger)

```bash
python -m touch_index bug --issue-id <uuid>
```

### Flags

| Flag | Description |
|------|-------------|
| `--issue-id <uuid>` | Process a single non-FDR issue by Paperclip UUID |
| `--lookback-minutes <N>` | Process issues closed within N minutes (default: 30) |
| `--dry-run` | Log what would be ingested without writing to DB or transitioning |
| `--validate` | Run bug data quality validation after ingestion (exits non-zero on failure) |
| `--stale-days <N>` | Validation alert threshold in days for stale rows (default: 30) |
| `--json-summary` | Output structured JSON summary to stdout |

### Through the runner script

```bash
python scripts/run_touch_index_bug_worker.py [--lookback-minutes N] [--dry-run] [--validate] [--json-summary]
python scripts/run_touch_index_bug_worker.py --issue-id <uuid> [--dry-run] [--validate] [--json-summary]
```

## Database Schema

### `touch_index_bug_files`

```sql
CREATE TABLE touch_index_bug_files (
    id             UUID        NOT NULL DEFAULT gen_random_uuid(),
    file_path      TEXT        NOT NULL,
    bug_issue_id   UUID        NOT NULL,
    bug_identifier TEXT        NOT NULL,
    source         TEXT        NOT NULL DEFAULT 'unknown',
    closed_at      TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_touch_bug_file_issue
    ON touch_index_bug_files (file_path, bug_issue_id);

CREATE INDEX idx_touch_bug_file_path
    ON touch_index_bug_files (file_path);
```

- `source` values: `'git'`, `'comments'`, `'description'`, `'none'`, `'unknown'`
- `closed_at` is nullable — rows may be inserted before the bug is closed;
  the ingestion job updates this field on close
- `updated_at` tracks when each row was last upserted by the ingestion worker (server default `now()`)
- `null_updated_at_rows` is monitored as part of bug consistency checks
- The unique constraint on `(file_path, bug_issue_id)` makes upserts idempotent

## Local Development

### Setup

```bash
cd /path/to/repo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your PAPERCLIP_API_KEY, POSTGRES_PASSWORD, etc.
```

### Run tests

```bash
# All touch index tests (327 tests)
python -m pytest tests/test_touch_index/ -v

# Bug worker-specific tests
python -m pytest tests/test_touch_index/test_bug_worker.py -v

# With coverage
python -m pytest tests/test_touch_index/ \
  --cov=src/touch_index --cov-report=term-missing
```

### Dry-run test

```bash
PYTHONPATH=src python -m touch_index bug --dry-run
```

### Process a known bug issue

```bash
PYTHONPATH=src python -m touch_index bug --issue-id <uuid> --dry-run
```

### Validate existing data

```bash
python scripts/validate_touch_index_bug.py --stale-days 30
```

Or via the quality module:

```bash
python -c "
from touch_index.db import get_engine
from touch_index.quality import run_bug_quality_checks
print(run_bug_quality_checks(get_engine()))
"
```

## Data Quality Monitoring

The `touch_index.quality` module provides bug-specific quality checks in
`run_bug_quality_checks()`:

### Bug Coverage

Compares done non-FDR issues in Paperclip vs `touch_index_bug_files`. Alerts
when coverage drops below 90%.

### Bug Freshness

Reports row age statistics using `closed_at` and flags stale rows (closed_at
older than the threshold, default 30 days).

### Bug Consistency

Detects:
- Null `closed_at` values
- Null `updated_at` values
- Duplicate `(file_path, bug_issue_id)` pairs
- Unknown `source` values (rows where source has not been set)
- Orphan `bug_issue_id` values (issue no longer exists in Paperclip)

### Quality report structure (JSON)

```json
{
  "passed": true,
  "coverage": {
    "total_bug_issues": 120,
    "indexed_bug_issues": 115,
    "coverage_pct": 95.8,
    "missing_issue_identifiers": ["BTCAAAAA-XYZ"]
  },
  "freshness": {
    "total_rows": 480,
    "max_age_hours": 72.3,
    "min_age_hours": 0.5,
    "stale_rows": 0,
    "stale_threshold_days": 30
  },
  "consistency": {
    "null_closed_at_rows": 0,
    "null_updated_at_rows": 0,
    "duplicate_pairs": 0,
    "unknown_source_rows": 0,
    "orphan_bug_issue_ids": []
  }
}
```

## Watermark Strategy

The worker uses a 30-minute look-back window (configurable via
`--lookback-minutes`) with idempotent upserts. This means:

- No watermark state file is needed
- Re-processing is safe (the `ON CONFLICT DO UPDATE` handles duplicates)
- Late-firing commits are covered by the overlap window
- Single-issue webhook events are processed immediately with no look-back

## Rollback Procedure

If the bug worker begins ingesting incorrect file references:

1. **Disable the workflow:** GitHub Actions -> Touch Index Bug Worker -> Disable
2. **Rollback the worker code:**
   ```bash
   git revert <bad-commit-hash> --no-edit
   git push origin main
   ```
3. **Clean corrupted data:**
   ```sql
   DELETE FROM touch_index_bug_files WHERE bug_issue_id = '<bad-uuid>';
   ```
4. **Re-enable workflow** after the fix is deployed

## Monitoring & Alerting

Key log lines at `INFO` level:

| Log pattern | Meaning |
|-------------|---------|
| `Fetching closed non-FDR issues completed after ...` | Poll cycle started |
| `Found N closed non-FDR issue(s) to process` | Issues to ingest this cycle |
| `Bug %s: indexed N file(s) via %s` | Successfully ingested issue |
| `Bug %s: no files found in git or comments` | No extractable files |
| `Marked %s as done` | Issue transitioned in Paperclip |
| `Failed to mark %s as done` | Transition API call failed |
| `VALIDATION PASSED` | All quality checks clean |
| `VALIDATION FAILED` | Quality check threshold breached |
| `BUG COVERAGE: N%` | Coverage metric |
| `BUG FRESHNESS: N stale rows` | Staleness metric |
| `BUG CONSISTENCY: ...` | Consistency issues detected |

## Troubleshooting

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| No issues processed | No done non-FDR issues in window | Check `--lookback-minutes` value |
| | API credentials missing | Verify `PAPERCLIP_API_*` env vars |
| | DB connection failure | Check `POSTGRES_*` env vars |
| 0 files indexed for all issues | No git commits referencing issue IDs | Check if fix commits have conventional commit format |
| | Git extraction failing on shallow clone | Verify repo has full history |
| | Comments/description also empty | Check issue has description with file paths |
| Validation fails | Coverage below 90% | Run backfill to catch missed issues |
| | Stale rows detected | Check worker cron is running every 15 min |
| | Orphan rows | Clean up deleted issues from DB |
| Worker exits non-zero | DB health check failed | Verify PostgreSQL is reachable |
| | Paperclip API timeout | Retry; check API status |

## Related Documents

- `src/touch_index/bug_worker.py` — Worker implementation
- `src/touch_index/__main__.py` — Unified CLI entry point
- `src/touch_index/quality.py` — Data quality monitoring
- `src/touch_index/comment_extractor.py` — File path extraction from text
- `src/touch_index/git_extractor.py` — File path extraction from git history
- `src/touch_index/paperclip_client.py` — Paperclip API client
- `src/touch_index/db.py` — PostgreSQL connection factory
- `alembic/versions/20260511_add_touch_index_tables.py` — Schema migration
- `alembic/versions/20260512_add_bug_files_source_col.py` — Source column migration
- `scripts/run_touch_index_bug_worker.py` — Runner script
- `scripts/validate_touch_index_bug.py` — Validation script
- `scripts/backfill_touch_index.py` — 90-day backfill script
- `docs/runbook-touch-index-fr-worker.md` — FR worker runbook (sibling)
