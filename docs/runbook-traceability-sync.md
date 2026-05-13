# Runbook: Traceability Sync Pipelines

## Overview

Three sync pipelines maintain the **traceability schema** (`trace_requirements`,
`trace_test_cases`, `trace_issues`, `trace_links`) in PostgreSQL — a
requirement→test→issue traceability layer that augments the file-based heuristics
of the Touch Index with explicit, queryable relationships.

This data powers:
- **Impact Gate** — resolves FR→test mappings when file-naming conventions fail
- **Coverage Gap Detection** — identifies requirements with no linked tests
- **Blast Radius cross-check** — compares file-level (Touch Index) vs
  requirement-level (Traceability) coverage
- **Trace Chain Queries** — full trace from issue → requirement → test case

### The Three Pipelines

| Pipeline | Script | Syncs | Frequency |
|----------|--------|-------|-----------|
| Requirement Sync | `scripts/sync_trace_requirements.py` | FDR-labelled Paperclip issues → `trace_requirements` | Every 15 min + webhook |
| Test Case Collection | `scripts/sync_trace_test_cases.py` | pytest test metadata → `trace_test_cases` + auto-links | On push to `main` + nightly |
| Issue Sync | `scripts/sync_trace_issues.py` | Paperclip issues → `trace_issues` with FR→req links | Every 15 min + webhook |

## Architecture

```
                    Paperclip API
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
 Requirement        Issue Sync           Test Case
   Sync                                  Sync
       |                 |                  |
       |                 |              pytest
       |                 |           --collect-only
       v                 v                  v
  trace_requirements  trace_issues    trace_test_cases
       |                 |                  |
       +-----------------+------------------+
                         |
                   trace_links (junction)
                         |
                         v
              +------------------+
              |  Downstream      |
              |  Consumers:      |
              |  Impact Gate     |
              |  Coverage Gap    |
              |  Blast Radius    |
              +------------------+
```

### Link Creation Strategy

| Source | Target | link_type | confidence | Condition |
|--------|--------|-----------|------------|-----------|
| `@pytest.mark.fr("FDR-NNN")` | TestCase → Requirement | `verifies` | 1.0 | Marker present in test file |
| `@pytest.mark.bug("BTCAAAAA-NNN")` | TestCase → Issue | `tests` | 1.0 | Marker present in test file |
| File-name heuristic (`test_fdr_NNN.py`) | TestCase → Requirement | `verifies` | 0.7 | Naming convention match |
| FDR label on Paperclip issue | Issue → Requirement | `implements` | 1.0 | Issue has FDR label |
| Touch Index FR overlap | Issue → Requirement | `implements` | 0.6 | Shared file paths via Touch Index |

## Pipeline 1: Requirement Sync

**Script:** `scripts/sync_trace_requirements.py`

Syncs FDR-labelled Paperclip issues (Feature Design Requirements) into the
`trace_requirements` table. Each FDR issue becomes one requirement record.

### CLI Usage

```bash
# Default: poll for recently updated FDR issues
PYTHONPATH=src python scripts/sync_trace_requirements.py

# Process a single FDR issue by Paperclip UUID
python scripts/sync_trace_requirements.py --issue-id <uuid>

# Dry-run (log only, no DB writes)
python scripts/sync_trace_requirements.py --dry-run

# Custom lookback window
python scripts/sync_trace_requirements.py --lookback-minutes 60
```

### Flags

| Flag | Description |
|------|-------------|
| `--issue-id <uuid>` | Process a single FDR issue by Paperclip UUID |
| `--lookback-minutes <N>` | Process issues updated within N minutes (default: 30) |
| `--dry-run` | Log what would be upserted without writing to DB |
| `--json-summary` | Output structured JSON summary to stdout |
| `-v / --verbose` | Enable debug logging |

### CI/CD Pipeline

Workflow: `.github/workflows/sync-trace-requirements.yml`

#### Triggers

| Trigger | Schedule / Event |
|---------|-----------------|
| `schedule` | Every 15 minutes (`*/15 * * * *`) |
| `repository_dispatch` | `issue_created`, `issue_updated`, `issue_status_changed` (FDR-labelled only) |
| `workflow_dispatch` | Manual trigger with optional `issue_id`, `lookback_minutes`, `dry_run` |

#### Concurrency

Group: `sync-trace-requirements` — `cancel-in-progress: false`

#### Step sequence

1. **Checkout** the repository
2. **Set up Python** 3.12
3. **Install dependencies** from `requirements.txt`
4. **Resolve issue ID** from event payload
5. **Run requirement sync** with appropriate flags
6. **Run coverage gap check** (post-sync validation)
7. **Write step summary** — issues processed, upserted, errors

### Status mapping

Paperclip → Traceability status:

| Paperclip Status | trace_requirements.status |
|-----------------|--------------------------|
| `todo` | `draft` |
| `in_progress` | `accepted` |
| `done` | `implemented` |
| `cancelled` / `blocked` | `deprecated` |

## Pipeline 2: Test Case Collection

**Script:** `scripts/sync_trace_test_cases.py`

Collects test case metadata from pytest and upserts into `trace_test_cases`.
For each test with `@pytest.mark.fr()` or `@pytest.mark.bug()` markers, it
auto-creates `trace_links` rows with `confidence = 1.0`.

### CLI Usage

```bash
# Standard collection: runs pytest --collect-only and syncs results
PYTHONPATH=src python scripts/sync_trace_test_cases.py

# Dry-run (log collected tests, no DB writes)
python scripts/sync_trace_test_cases.py --dry-run

# Specify test directory (default: tests/)
python scripts/sync_trace_test_cases.py --test-dir tests/fr_acceptance

# Regenerate all links (drop and recreate trace_links for tests)
python scripts/sync_trace_test_cases.py --regenerate-links
```

### Flags

| Flag | Description |
|------|-------------|
| `--test-dir <path>` | Test directory to scan (default: `tests/`) |
| `--dry-run` | Log collected tests without writing to DB |
| `--regenerate-links` | Drop and recreate all test→requirement/issue links |
| `--json-summary` | Output structured JSON summary to stdout |
| `-v / --verbose` | Enable debug logging |

### CI/CD Pipeline

Workflow: `.github/workflows/sync-trace-test-cases.yml`

#### Triggers

| Trigger | Schedule / Event |
|---------|-----------------|
| `push` | On `main` branch |
| `schedule` | Nightly at 04:00 UTC |
| `workflow_dispatch` | Manual trigger |

#### Concurrency

Group: `sync-trace-test-cases` — `cancel-in-progress: true` (latest push wins)

#### Step sequence

1. **Checkout** the repository
2. **Set up Python** 3.12
3. **Install dependencies** from `requirements.txt`
4. **Run test case collection** — runs `pytest --collect-only --quiet -q` and
   parses output, upserts test cases and links
5. **Run gap analysis** — compares collected tests against
   `requirements_registry.json` to find untested requirements
6. **Upload gap report** as workflow artifact

#### Marker parsing

The collector parses pytest collection output to extract markers:

```
tests/fr_acceptance/test_fdr_850.py::test_ac1_auto_pause
    [markers: fr('FDR-850'), acceptance, smoke]
    |                                              |
    link_type=verifies                             parsed marker value
    target=trace_requirements                      lookup by identifier='FDR-850'
```

## Pipeline 3: Issue Sync

**Script:** `scripts/sync_trace_issues.py`

Syncs Paperclip issues into `trace_issues`. Issues tagged with the FDR label
auto-create `trace_links` entries to `trace_requirements` with
`link_type = implements`.

### CLI Usage

```bash
# Default: poll for recently updated issues
PYTHONPATH=src python scripts/sync_trace_issues.py

# Process a single issue by Paperclip UUID
python scripts/sync_trace_issues.py --issue-id <uuid>

# Filter by label (comma-separated)
python scripts/sync_trace_issues.py --labels FDR,fix,bug

# Filter by status
python scripts/sync_trace_issues.py --status done,in_review

# Dry-run
python scripts/sync_trace_issues.py --dry-run
```

### Flags

| Flag | Description |
|------|-------------|
| `--issue-id <uuid>` | Process a single issue by Paperclip UUID |
| `--lookback-minutes <N>` | Process issues updated within N minutes (default: 30) |
| `--labels <list>` | Comma-separated label filter (default: all) |
| `--status <list>` | Comma-separated status filter (default: all) |
| `--dry-run` | Log what would be upserted without writing to DB |
| `--json-summary` | Output structured JSON summary to stdout |
| `-v / --verbose` | Enable debug logging |

### CI/CD Pipeline

Workflow: `.github/workflows/sync-trace-issues.yml`

#### Triggers

| Trigger | Schedule / Event |
|---------|-----------------|
| `schedule` | Every 15 minutes (`*/15 * * * *`) |
| `repository_dispatch` | `issue_created`, `issue_updated`, `issue_status_changed` |
| `workflow_dispatch` | Manual trigger with optional params |

#### Concurrency

Group: `sync-trace-issues` — `cancel-in-progress: false`

#### Step sequence

1. **Checkout** the repository
2. **Set up Python** 3.12
3. **Install dependencies** from `requirements.txt`
4. **Resolve issue ID / filters** from event payload
5. **Run issue sync** — fetches issues, upserts into `trace_issues`,
   auto-creates `implements` links for FDR-labelled issues
6. **Run orphan check** — detects `trace_issues` rows with no Paperclip match
7. **Write step summary**

## Database Schema

### `trace_requirements`

```sql
CREATE TABLE trace_requirements (
    id            UUID         NOT NULL DEFAULT gen_random_uuid(),
    identifier    VARCHAR(50)  NOT NULL,
    title         VARCHAR(500) NOT NULL,
    description   TEXT,
    status        VARCHAR(30)  NOT NULL DEFAULT 'draft',
    priority      VARCHAR(20),
    labels        JSONB,
    source        VARCHAR(30)  NOT NULL DEFAULT 'paperclip',
    paperclip_id  UUID,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    metadata      JSONB,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_trace_requirements_identifier
    ON trace_requirements (identifier);
CREATE INDEX idx_trace_requirements_status
    ON trace_requirements (status);
CREATE INDEX idx_trace_requirements_paperclip_id
    ON trace_requirements (paperclip_id);
```

- `source` values: `'paperclip'`, `'manual'`, `'derived'`
- `status` values: `'draft'`, `'accepted'`, `'implemented'`, `'deprecated'`, `'superseded'`
- Upsert merge key: `identifier` (e.g., `FDR-850`)

### `trace_test_cases`

```sql
CREATE TABLE trace_test_cases (
    id             UUID         NOT NULL DEFAULT gen_random_uuid(),
    identifier     VARCHAR(300) NOT NULL,
    test_file      VARCHAR(500) NOT NULL,
    test_function  VARCHAR(300) NOT NULL,
    test_class     VARCHAR(300),
    markers        JSONB,
    source         VARCHAR(30)  NOT NULL DEFAULT 'pytest_collection',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    tags           JSONB,
    language       VARCHAR(20)  NOT NULL DEFAULT 'python',
    component      VARCHAR(200),
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_trace_test_cases_identifier
    ON trace_test_cases (identifier);
CREATE INDEX idx_trace_test_cases_file
    ON trace_test_cases (test_file);
CREATE INDEX idx_trace_test_cases_component
    ON trace_test_cases (component);
```

- `identifier` format: `<test_file>::<test_function>` (e.g.,
  `tests/fr_acceptance/test_fdr_850.py::test_ac1_auto_pause_on_drawdown_breach`)
- `source` values: `'pytest_collection'`, `'manual'`, `'qa_verdict'`
- Upsert merge key: `identifier`

### `trace_issues`

```sql
CREATE TABLE trace_issues (
    id            UUID         NOT NULL DEFAULT gen_random_uuid(),
    identifier    VARCHAR(50)  NOT NULL,
    title         VARCHAR(500) NOT NULL,
    issue_type    VARCHAR(30)  NOT NULL,
    status        VARCHAR(30)  NOT NULL,
    paperclip_id  UUID,
    labels        JSONB,
    parent_id     UUID         REFERENCES trace_issues(id),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_trace_issues_identifier
    ON trace_issues (identifier);
CREATE INDEX idx_trace_issues_paperclip_id
    ON trace_issues (paperclip_id);
CREATE INDEX idx_trace_issues_type
    ON trace_issues (issue_type);
CREATE INDEX idx_trace_issues_status
    ON trace_issues (status);
```

- `issue_type` values: `'bug'`, `'fix'`, `'enhancement'`, `'task'`, `'fr'`
- Upsert merge key: `identifier` (e.g., `BTCAAAAA-736`)

### `trace_links` (junction table)

```sql
CREATE TABLE trace_links (
    id               UUID         NOT NULL DEFAULT gen_random_uuid(),
    requirement_id   UUID         REFERENCES trace_requirements(id),
    test_case_id     UUID         REFERENCES trace_test_cases(id),
    issue_id         UUID         REFERENCES trace_issues(id),
    link_type        VARCHAR(30)  NOT NULL,
    direction        VARCHAR(10)  NOT NULL,
    confidence       FLOAT        NOT NULL DEFAULT 1.0,
    metadata         JSONB,
    is_active        BOOLEAN      NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by       VARCHAR(100),
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_trace_links_req_test_issue_type
    ON trace_links (requirement_id, test_case_id, issue_id, link_type);
CREATE INDEX idx_trace_links_requirement
    ON trace_links (requirement_id);
CREATE INDEX idx_trace_links_test_case
    ON trace_links (test_case_id);
CREATE INDEX idx_trace_links_issue
    ON trace_links (issue_id);
CREATE INDEX idx_trace_links_type
    ON trace_links (link_type);
```

- `link_type` values: `'verifies'`, `'implements'`, `'tests'`, `'relates_to'`
- `direction` values: `'forward'`, `'reverse'`
- At least two of `(requirement_id, test_case_id, issue_id)` must be non-NULL
  (enforced at application layer)
- Upsert merge key: `(requirement_id, test_case_id, issue_id, link_type)`

## Environment Variables

| Variable | Pipelines | Source | Purpose |
|----------|-----------|--------|---------|
| `PAPERCLIP_API_URL` | Requirement, Issue | Secret | Paperclip API base URL |
| `PAPERCLIP_API_KEY` | Requirement, Issue | Secret | API authentication |
| `PAPERCLIP_COMPANY_ID` | Requirement, Issue | Secret | Company/org ID |
| `FDR_LABEL_ID` | Requirement | Secret | Paperclip label UUID for FDR filter |
| `POSTGRES_HOST` | All | Secret | PostgreSQL host |
| `POSTGRES_PORT` | All | Secret | PostgreSQL port (default: 5432) |
| `POSTGRES_DB` | All | Secret | Database name (default: optimizer_v3) |
| `POSTGRES_USER` | All | Secret | Database user (default: optimizer_admin) |
| `POSTGRES_PASSWORD` | All | Secret | Database password |
| `PYTHONPATH` | All | `src` | Python module resolution |

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
# All traceability tests
python -m pytest tests/test_traceability/ -v

# Pipeline-specific tests
python -m pytest tests/test_traceability/test_sync_requirements.py -v
python -m pytest tests/test_traceability/test_sync_test_cases.py -v
python -m pytest tests/test_traceability/test_sync_issues.py -v
python -m pytest tests/test_traceability/test_trace_links.py -v

# With coverage
python -m pytest tests/test_traceability/ \
  --cov=scripts --cov-report=term-missing
```

### Dry-run tests

```bash
# Requirement sync
PYTHONPATH=src python scripts/sync_trace_requirements.py --dry-run

# Test case collection
PYTHONPATH=src python scripts/sync_trace_test_cases.py --dry-run

# Issue sync
PYTHONPATH=src python scripts/sync_trace_issues.py --dry-run
```

### Utility queries

```bash
# Coverage gap: requirements with no linked tests
psql "$POSTGRES_CONNECTION_STRING" -c "
SELECT r.identifier, r.title, r.status
FROM trace_requirements r
WHERE r.status IN ('accepted', 'implemented')
  AND r.id NOT IN (
    SELECT DISTINCT requirement_id
    FROM trace_links
    WHERE link_type = 'verifies' AND is_active = true
  );
"

# Full trace chain for an issue
psql "$POSTGRES_CONNECTION_STRING" -c "
SELECT r.identifier AS requirement, tc.identifier AS test,
       i2.identifier AS related_issue, tl.link_type, tl.confidence
FROM trace_links tl
LEFT JOIN trace_requirements r ON r.id = tl.requirement_id
LEFT JOIN trace_test_cases tc ON tc.id = tl.test_case_id
LEFT JOIN trace_issues i2 ON i2.id = tl.issue_id
WHERE tl.issue_id = (SELECT id FROM trace_issues WHERE identifier = 'BTCAAAAA-736');
"
```

## Rollback Procedure

### Disable sync workflows

If any sync pipeline begins ingesting incorrect data:

1. **Disable the workflow(s):** GitHub Actions → select workflow → ⋮ → Disable workflow
2. **Identify affected rows:**
   ```sql
   -- Find rows synced after the bad deploy
   SELECT * FROM trace_requirements WHERE updated_at > '<deploy-timestamp>';
   SELECT * FROM trace_test_cases WHERE updated_at > '<deploy-timestamp>';
   SELECT * FROM trace_issues WHERE updated_at > '<deploy-timestamp>';
   SELECT * FROM trace_links WHERE created_at > '<deploy-timestamp>';
   ```
3. **Rollback pipeline code:**
   ```bash
   git revert <bad-commit-hash> --no-edit
   git push origin main
   ```
4. **Clean corrupted data:**
   ```sql
   -- Delete bad links first (they reference other tables)
   DELETE FROM trace_links WHERE created_at > '<deploy-timestamp>';
   -- Then delete bad records
   DELETE FROM trace_requirements WHERE updated_at > '<deploy-timestamp>';
   DELETE FROM trace_test_cases WHERE updated_at > '<deploy-timestamp>';
   DELETE FROM trace_issues WHERE updated_at > '<deploy-timestamp>';
   ```
5. **Re-enable workflows** after the fix is deployed
6. **Trigger a manual re-sync** via `workflow_dispatch` for each pipeline

### Schema rollback

```bash
alembic downgrade -1
```

Tables are additive — no existing data is modified by the migration.

## Monitoring & Alerting

### Key Log Patterns (all pipelines)

| Log pattern | Pipeline | Meaning |
|-------------|----------|---------|
| `Fetched N FDR issue(s)` | Requirement | Poll cycle started |
| `Upserted N requirement(s)` | Requirement | Sync completed |
| `Auto-linked N implements edge(s)` | Issue | FDR→requirement links created |
| `Collected N test case(s)` | Test Case | Pytest collection completed |
| `Created N link(s) from markers` | Test Case | Marker-based links created |
| `Gap: N requirement(s) with zero tests` | Test Case | Coverage gap detected |
| `Orphan: N issue(s) not found in Paperclip` | Issue | Stale trace_issues rows |
| `Sync failed: PAPERCLIP_API_* not configured` | Requirement, Issue | Missing credentials |
| `Sync failed: database unreachable` | All | DB connection error |

### Automated Alerting

The **Traceability Monitor** (`scripts/traceability_monitor.py`) runs after each
sync cycle and on a scheduled health check (every 30 minutes):

- Creates a `medium`-priority Paperclip alert if any pipeline fails
- Escalates to `critical` if error rate > 50% across pipelines
- Generates a gap report when coverage drops below 90%
- Deduplicates: one alert per pipeline per day

### Silencing alerts

1. Use `workflow_dispatch` with `dry_run: true` on the failing pipeline
2. Or disable the monitor workflow: GitHub Actions → Traceability Monitor → ⋮ → Disable

## Troubleshooting

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| No requirements synced | No FDR issues updated in window | Check `--lookback-minutes` value |
| | FDR_LABEL_ID misconfigured | Verify `FDR_LABEL_ID` env var |
| | API credentials missing | Verify `PAPERCLIP_API_*` env vars |
| No test cases collected | Pytest collection output empty | Run `pytest --collect-only` manually |
| | Test directory path wrong | Check `--test-dir` default or override |
| | DB connection failure | Check `POSTGRES_*` env vars |
| Links not auto-created | Markers not parsed | Check pytest marker format in test file |
| | FDR identifier not found in trace_requirements | Run requirement sync first |
| Orphan issues count high | Paperclip issues deleted | Clean up orphan rows or ignore |
| | API pagination issue | Check `PAPERCLIP_API_URL` returns all pages |
| Coverage gap > 10% | New requirements added without tests | Add test files and markers |
| | Test files renamed but registry not updated | Update `requirements_registry.json` |

## Related Documents

- `scripts/sync_trace_requirements.py` — Requirement sync implementation
- `scripts/sync_trace_test_cases.py` — Test case collection implementation
- `scripts/sync_trace_issues.py` — Issue sync implementation
- `scripts/traceability_monitor.py` — Health monitoring script
- `.github/workflows/sync-trace-requirements.yml` — Requirement sync workflow
- `.github/workflows/sync-trace-test-cases.yml` — Test case sync workflow
- `.github/workflows/sync-trace-issues.yml` — Issue sync workflow
- `.github/workflows/traceability-monitor.yml` — Monitor workflow
- `alembic/versions/20260513_add_traceability_schema.py` — Schema migration
- `src/optimizer_v3/database/models.py` — SQLAlchemy models (traceability tables)
- `docs/architecture/adr/ADR-0002-traceability-schema-requirement-test-issue.md` — Architecture design
- `docs/architecture/adr/ADR-0002-test-to-requirements-traceability.md` — JSON registry ADR
- `requirements_registry.json` — Canonical requirements registry
