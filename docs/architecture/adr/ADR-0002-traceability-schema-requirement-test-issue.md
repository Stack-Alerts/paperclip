# ADR-0002: Traceability Schema — Requirement → Test Case → Issue

**Issue:** BTCAAAAA-25644  
**Author:** Architect (73eaab54)  
**Status:** In Review  
**Date:** 2026-05-13  
**Priority:** HIGH  

---

## Context

The project currently links requirements, test cases, and issues through **implicit, file-path-based heuristics**:

1. **Requirements (FRs)** are Paperclip issues with the FDR label. The Touch Index table `touch_index_fr_files` records FR → file_path mappings, derived from done-comments, git commits, or issue descriptions.
2. **Test cases** follow file-naming conventions (`tests/fr_acceptance/test_fdr_NNN.py`, `tests/bug_regression/test_btcaaaaa_NNN_regression.py`) and pytest markers (`@pytest.mark.fr("FDR-850")`, `@pytest.mark.bug("BTCAAAAA-736")`).
3. **Issues** (bugs, fixes) are linked to files via `touch_index_bug_files`.

The Impact Gate runner resolves Requirement → Test by **convention**: it assumes `FDR-850` maps to `tests/fr_acceptance/test_fdr_850.py`. This breaks when:
- A requirement is tested across multiple test files
- A test file covers multiple requirements
- Test files use non-standard naming (e.g., `test_btcaaaaa_850.py`)
- Requirements evolve and old tests are superseded

Without explicit traceability, the system cannot answer:
- "Which tests verify requirement X?"
- "Is requirement Y covered by any test?"
- "What requirements does test file Z cover?"
- "Show the full trace chain for issue A"
- "What is the test coverage gap for FRs in the current sprint?"

---

## Decision: Add an explicit traceability layer in PostgreSQL alongside the existing Touch Index

We will persist Requirement → TestCase → Issue relationships as first-class entities in the database, augmenting (not replacing) the file-based heuristics that the Touch Index and Impact Gate use for blast-radius calculations. The Touch Index continues to answer "what files did this FR touch?" while the traceability schema answers "what tests verify this FR?"

### Schema Design

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│     Requirement      │     │ TraceabilityLink     │     │      TestCase        │
│  (trace_requirements)│     │ (trace_links)        │     │ (trace_test_cases)   │
├──────────────────────┤     ├──────────────────────┤     ├──────────────────────┤
│ id (UUID PK)         │◄────│ requirement_id (FK)  │     │ id (UUID PK)         │
│ identifier (str)     │     │ test_case_id (FK) ───│────►│ identifier (str)     │
│ title (str)          │     │ issue_id (FK, null)─ │──┐  │ test_file (str)      │
│ description (str)    │     │ link_type (enum)     │  │  │ test_function (str)  │
│ status (str)         │     │ direction (enum)     │  │  │ test_class (str, null)│
│ priority (str)       │     │ confidence (float)   │  │  │ markers (JSONB)      │
│ labels (JSONB)       │     │ created_at           │  │  │ source (enum)        │
│ source (enum)        │     │ created_by (str)     │  │  │ created_at           │
│ paperclip_id (UUID)  │     │ metadata (JSONB)     │  │  │ updated_at           │
│ created_at           │     │ is_active (bool)     │  │  │ tags (JSONB)         │
│ updated_at           │     └──────────────────────┘  │  │ language (str)       │
│ metadata (JSONB)     │                               │  │ component (str)      │
└──────────────────────┘                               │  └──────────────────────┘
        │                                              │
        │                    ┌──────────────────────┐  │
        └────────────────────│      Issue           │◄─┘
                             │  (trace_issues)      │
                             ├──────────────────────┤
                             │ id (UUID PK)         │
                             │ identifier (str)     │
                             │ title (str)          │
                             │ issue_type (enum)    │
                             │ status (str)         │
                             │ paperclip_id (UUID)  │
                             │ labels (JSONB)       │
                             │ parent_id (FK, null) │
                             │ created_at           │
                             │ updated_at           │
                             └──────────────────────┘
```

### Core Tables

#### 1. `trace_requirements`
Stores Feature Design Requirements synced from Paperclip FDR-labelled issues.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| identifier | VARCHAR(50) | NO | Human-readable ID, e.g. `FDR-850` |
| title | VARCHAR(500) | NO | Requirement title from Paperclip |
| description | TEXT | YES | Full requirement body |
| status | VARCHAR(30) | NO | `draft`, `accepted`, `implemented`, `deprecated`, `superseded` |
| priority | VARCHAR(20) | YES | `critical`, `high`, `medium`, `low` |
| labels | JSONB | YES | Paperclip labels snapshot |
| source | VARCHAR(30) | NO | `paperclip`, `manual`, `derived` |
| paperclip_id | UUID | YES | Paperclip issue UUID for bi-directional sync |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last sync/update |
| metadata | JSONB | YES | Acceptance criteria, related FDRs, etc. |

Indexes: UNIQUE on `identifier`, INDEX on `status`, INDEX on `paperclip_id`.

#### 2. `trace_test_cases`
Stores test cases discovered from pytest collection and QA verdict files.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| identifier | VARCHAR(300) | NO | Stable identifier, e.g. `test_fdr_850.py::test_ac1_auto_pause_on_drawdown_breach` |
| test_file | VARCHAR(500) | NO | Repo-relative path, e.g. `tests/fr_acceptance/test_fdr_850.py` |
| test_function | VARCHAR(300) | NO | Function name |
| test_class | VARCHAR(300) | YES | Class name for class-based tests |
| markers | JSONB | YES | Pytest markers snapshot (`fr`, `bug`, `acceptance`, `regression`) |
| source | VARCHAR(30) | NO | `pytest_collection`, `manual`, `qa_verdict` |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last update |
| tags | JSONB | YES | Arbitrary tags |
| language | VARCHAR(20) | NO | `python` default |
| component | VARCHAR(200) | YES | System component (e.g. `itm/engine`, `optimizer_v3`) |

Indexes: UNIQUE on `identifier`, INDEX on `test_file`, INDEX on `component`.

#### 3. `trace_issues`
Stores Paperclip issues that implement or fix requirements.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| identifier | VARCHAR(50) | NO | e.g. `BTCAAAAA-736` |
| title | VARCHAR(500) | NO | Issue title |
| issue_type | VARCHAR(30) | NO | `bug`, `fix`, `enhancement`, `task`, `fr` |
| status | VARCHAR(30) | NO | Paperclip status |
| paperclip_id | UUID | YES | Paperclip issue UUID |
| labels | JSONB | YES | Paperclip labels |
| parent_id | UUID | YES | FK to `trace_issues.id` for parent-child linking |
| created_at | TIMESTAMPTZ | NO | Record creation |
| updated_at | TIMESTAMPTZ | NO | Last sync |

Indexes: UNIQUE on `identifier`, INDEX on `paperclip_id`, INDEX on `issue_type`, INDEX on `status`.

#### 4. `trace_links` (junction table)
The core traceability edge set. Each row is a directed link between two entities.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID | NO | Primary key |
| requirement_id | UUID | YES | FK to `trace_requirements.id` |
| test_case_id | UUID | YES | FK to `trace_test_cases.id` |
| issue_id | UUID | YES | FK to `trace_issues.id` |
| link_type | VARCHAR(30) | NO | `verifies`, `implements`, `tests`, `relates_to` |
| direction | VARCHAR(10) | NO | `forward` or `reverse` |
| confidence | FLOAT | NO | 0.0–1.0; 1.0 = explicit marker, <1.0 = heuristic-derived |
| metadata | JSONB | YES | Derivation source, sync timestamps, agent who created |
| is_active | BOOLEAN | NO | True until link is deprecated/removed |
| created_at | TIMESTAMPTZ | NO | Record creation |
| created_by | VARCHAR(100) | YES | Agent or pipeline that created the link |

Indexes: UNIQUE on `(requirement_id, test_case_id, issue_id, link_type)`, INDEX on `requirement_id`, `test_case_id`, `issue_id`, `link_type`.

Constraints: At least two of `(requirement_id, test_case_id, issue_id)` must be non-NULL (enforced at application layer).

### Link Types and Semantics

| link_type | Source | Target | Meaning | Confidence Source |
|-----------|--------|--------|---------|-------------------|
| `verifies` | TestCase | Requirement | Test case verifies acceptance criteria of the requirement | `@pytest.mark.fr()` marker → 1.0; file-name heuristic → 0.7 |
| `implements` | Issue | Requirement | Issue implements or fixes the requirement | FDR label on issue → 1.0; Touch Index FR overlap → 0.6 |
| `tests` | TestCase | Issue | Test case specifically tests the bug/fix in the issue | `@pytest.mark.bug()` marker → 1.0; regression test naming → 0.7 |
| `relates_to` | * | * | General bidirectional relationship | Manual or cross-reference in descriptions → 0.5 |

### Ingestion Strategy

Three pipelines populate the traceability schema, all following the existing cron + webhook pattern:

#### Pipeline 1: Requirement Sync (`scripts/sync_trace_requirements.py`)
- **Trigger:** GitHub Actions cron every 15 min + webhook on FDR issue events
- **Source:** Paperclip API — issues with FDR label (`FDR_LABEL_ID`)
- **Upsert logic:** `identifier` is the merge key; `paperclip_id` enables bi-directional lookup
- **Status mapping:** Paperclip status → traceability status (`todo` → `draft`, `in_progress` → `accepted`, `done` → `implemented`)

#### Pipeline 2: Test Case Collection (`scripts/sync_trace_test_cases.py`)
- **Trigger:** GitHub Actions on push to `main` + nightly cron
- **Source:** `pytest --collect-only --quiet` with JSON output
- **Upsert logic:** `identifier` = `<test_file>::<test_function>` is the merge key
- **Marker extraction:** Parse `@pytest.mark.fr()`, `@pytest.mark.bug()` from test source or collection output
- **Link creation:** For each marker, auto-create a `trace_links` row with `confidence=1.0`

#### Pipeline 3: Issue Sync (`scripts/sync_trace_issues.py`)
- **Source:** Paperclip API — all issues (or filtered subset by label/status)
- **Upsert logic:** `identifier` is the merge key
- **Link creation:** Issues tagged as FDR → auto-link to `trace_requirements` via `link_type=implements`

### Integration with Existing Systems

| System | Integration Point | Change Required |
|--------|-------------------|-----------------|
| Touch Index (FR) | `touch_index_fr_files` | None — continues as file-level index; traceability adds requirement-level view |
| Touch Index (Bug) | `touch_index_bug_files` | None — continues as file-level index |
| Impact Gate Worker | `scripts/impact_gate_runner.py` | Consult `trace_links` for test→FR resolution when file-name convention fails; fall back to convention |
| Blast Radius Worker | `src/blast_radius/query.py` | Add optional cross-check: `trace_requirements` ↔ `touch_index_fr_files` for coverage gap detection |
| Impact Gate Runner | `scripts/impact_gate_runner.py` | Resolve `FR_ID → test_files` via `trace_links` as primary, naming convention as fallback |
| QA Verdict pipeline | `tests/**/QA_VERDICT_*.md` | Optional: auto-ingest verdicts into `trace_links` as `confidence=0.8` edges |

### Query Patterns (Post-Ingestion)

```sql
-- What tests verify a given requirement?
SELECT tc.identifier, tc.test_file, tc.test_function, tl.confidence
FROM trace_links tl
JOIN trace_test_cases tc ON tc.id = tl.test_case_id
WHERE tl.requirement_id = :req_id
  AND tl.link_type = 'verifies'
  AND tl.is_active = true
ORDER BY tl.confidence DESC;

-- What requirements does test file X cover?
SELECT r.identifier, r.title, tl.confidence
FROM trace_links tl
JOIN trace_requirements r ON r.id = tl.requirement_id
WHERE tl.test_case_id IN (
    SELECT id FROM trace_test_cases WHERE test_file = :file_path
)
  AND tl.is_active = true;

-- Coverage gap: requirements with NO linked tests
SELECT r.identifier, r.title, r.status
FROM trace_requirements r
WHERE r.status IN ('accepted', 'implemented')
  AND r.id NOT IN (
      SELECT DISTINCT requirement_id
      FROM trace_links
      WHERE link_type = 'verifies' AND is_active = true
  );

-- Full trace chain for an issue
SELECT r.identifier AS requirement, tc.identifier AS test,
       i2.identifier AS related_issue, tl.link_type
FROM trace_links tl
LEFT JOIN trace_requirements r ON r.id = tl.requirement_id
LEFT JOIN trace_test_cases tc ON tc.id = tl.test_case_id
LEFT JOIN trace_issues i2 ON i2.id = tl.issue_id
WHERE tl.issue_id = (SELECT id FROM trace_issues WHERE identifier = :issue_id)
   OR tl.requirement_id IN (
       SELECT id FROM trace_requirements WHERE identifier LIKE :pattern
   );
```

---

## Trade-Offs

| Approach | Pros | Cons |
|----------|------|------|
| **Dedicated DB tables (chosen)** | Queryable in SQL; integrates with Impact Gate and Blast Radius pipelines; persistent; supports coverage gap detection | Ingest pipeline complexity; data consistency across Paperclip ↔ DB requires careful sync |
| **File-only markers (current)** | No infrastructure; pytest markers already exist | No query capability; fragile naming conventions; no coverage gap detection |
| **External tool (e.g. TestRail, Xray)** | Rich UI; integrations out of the box | Vendor lock-in; cost; another system to maintain; doesn't integrate with existing DB pipelines |
| **Custom YAML/JSON mapping file** | Simple to version-control; no DB changes | No query capability at scale; edit conflicts; stale without sync automation |

---

## Limitations

1. **Confidence scoring is heuristic.** Auto-created links from naming conventions carry `confidence < 1.0`. Human-curated links (from pytest markers) carry `confidence = 1.0`. Downstream consumers must decide whether to filter by confidence threshold.
2. **Paperclip API dependency.** Requirement and Issue sync depends on Paperclip API availability. Short outages are tolerable (cron retries); extended outages cause stale data.
3. **Test case collection requires pytest.** Non-pytest test frameworks (none currently in use) would need a separate collector.
4. **Link rot.** When test functions are renamed or requirements are superseded, links become stale. The `is_active` flag and periodic reconciliation task address this.

---

## Migration Path

### Phase 1: Schema + Ingest (this heartbeat)
1. Create Alembic migration with the 4 tables above
2. Add SQLAlchemy models to `src/optimizer_v3/database/models.py` (next to existing touch_index models)
3. Create ingestion scripts: `scripts/sync_trace_requirements.py`, `scripts/sync_trace_test_cases.py`, `scripts/sync_trace_issues.py`
4. Add GitHub Actions workflows for each sync (15-min cron + webhook triggers)

### Phase 2: Integration (next heartbeat)
5. Update Impact Gate runner to consult `trace_links` as fallback when file-naming convention fails
6. Add coverage gap report to nightly CI
7. Wire pytest collection output into test case sync

### Phase 3: Enrichment (future)
8. QA verdict auto-ingestion from `QA_VERDICT_*.md` files
9. Blast Radius cross-check: Touch Index (file-level) vs Traceability (requirement-level) coverage comparison
10. Dashboard (optional): query traceability via AI Consultant tool

---

## Migration

### Alembic migration

```bash
alembic revision -m "add_traceability_schema"
```

Expected migration file: `alembic/versions/20260513_add_traceability_schema.py`

### Rollback

```bash
alembic downgrade -1
```

Tables are additive — no existing data is modified.

---

## Connected Issues

| Issue | Relationship |
|-------|-------------|
| BTCAAAAA-25644 | This ADR |
| BTCAAAAA-1477 | ADR-0001 — zero-trades audit; shares observability pattern |
| BTCAAAAA-7381 | Predecessor — docs audit and coverage plan |
| BTCAAAAA-22893 | Related — factual accuracy audit, test documentation |
| (future) | Child — DatabaseAdministrator: Alembic migration implementation |
| (future) | Child — AutomationEngineer: sync pipeline implementation |
| (future) | Child — DocWriter: runbook for traceability sync pipelines |

---

## Verification Checklist

> **Implementation state (2026-05-14):** Phase 1 (schema, models, scripts, CI) is complete. Phase 2 (Impact Gate integration, coverage gap report) and Phase 3 (QA verdict ingestion, dashboard) remain as defined in the migration plan below.

- [x] Alembic migration creates 4 tables with correct indexes and constraints (`alembic/versions/20260513_add_traceability_schema.py`)
- [x] SQLAlchemy models declared in `models.py` with `__tablename__` matching migration (`src/optimizer_v3/database/models.py:792-908`)
- [x] `sync_trace_requirements.py` upserts from Paperclip API (`scripts/sync_trace_requirements.py`)
- [x] `sync_trace_test_cases.py` collects from pytest and upserts with correct identifiers (`scripts/sync_trace_test_cases.py`)
- [x] `sync_trace_issues.py` upserts from Paperclip API (`scripts/sync_trace_issues.py`)
- [x] CI workflows for each sync pipeline deployed (`.github/workflows/sync-trace-*.yml`)
- [ ] `trace_links` auto-created from pytest markers (`@pytest.mark.fr()`, `@pytest.mark.bug()`)
- [ ] Coverage gap query returns correct results against real data
- [ ] Impact Gate runner falls back to `trace_links` resolution when convention fails
- [ ] Manual link create/update/delete via API or CLI

---

## DoD

- [x] Architecture analysis and schema design complete
- [x] Integration points with existing systems documented
- [x] Migration strategy defined (3-phase)
- [x] Query patterns documented
- [x] Trade-offs and limitations evaluated
- [x] Implementation of Phase 1 — schema, models, sync scripts, CI workflows deployed
- [ ] Push to origin
