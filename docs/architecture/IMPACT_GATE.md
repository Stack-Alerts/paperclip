# Impact Gate — Architecture

**Last updated:** 2026-05-12
**Owner:** DocWriter / CTO

---

## 1. Overview

The Impact Gate validates fix/bug issues before they transition `in_review → done`. It runs FR acceptance tests and bug regression tests to ensure changes are safe and complete.

### 1.1 Gate Flow

```
fix/bug issue transitions to in_review
    ↓
Impact Gate Worker triggered
    ↓
1. Check for CEO bypass label ("impact-gate-bypass")
   ── bypass? → skip gate, post notice
    ↓
2. Read touchedFiles from issue description
    ↓
3. Query Blast Radius Touch Index for:
   - fr_impact_set (FRs that touch overlapping files)
   - regression_set (bugs that touched overlapping files)
    ↓
4. Run Impact Gate test suite:
   - FR acceptance tests for each impacted FR
   - Bug regression tests for each related bug
    ↓
5. Evaluate results:
   PASS (≥10 tests, all pass)   → transition to done
   FAIL (any failure)           → revert to in_progress, create blocking sub-issues
   ERROR (runner error)         → post escalation comment, do NOT revert
```

---

## 2. Components

### 2.1 Worker (`worker.py`)

The central orchestrator called by:
- **Scheduled:** Every 5 minutes via `impact-gate-worker.yml`
- **Webhook:** `repository_dispatch` with `issue_status_changed`
- **Manual:** `workflow_dispatch` with `issue_id` and `old_status`

#### Key Constants

```python
BYPASS_LABEL = "impact-gate-bypass"    # CEO override label
MIN_TESTS_BAR = 10                      # minimum tests to declare PASS
COMPANY_PREFIX = "BTCAAAAA"
```

#### Outcome Actions

| Result | Action |
|---|---|
| PASS | Transition issue to `done` |
| FAIL | Transition back to `in_progress`, create blocking sub-issues per failing FR/bug |
| ERROR (runner crash) | Post escalation comment with details, do NOT transition |
| Bypass | Post notice, skip gate, do NOT auto-transition |

### 2.2 Impact Gate Runner (`scripts/impact_gate_runner.py`)

CLI runner that executes the actual test suite. Called by the worker with:
- `fr_impact_set` — list of FR identifiers whose acceptance tests to run
- `regression_set` — list of bug identifiers whose regression tests to run

### 2.3 Scan-Done Worker (`scripts/scan_fix_issues_done.py`)

Retroactively gates fix/bug issues already in `done` that never passed through the gate.

**Purpose:** Backfill coverage for issues completed before the Impact Gate existed, or issues that slipped through without gating.

**Cadence:** Every 5 minutes via `impact-gate-scan-done.yml`

**Parameters:** `days_back` (default 7), `dry_run`, `retroactive`

### 2.4 Alerting (`scripts/scan_done_alert.py`)

Creates a Paperclip alert issue when ungated issues are detected during scan-done.

---

## 3. Data Flow

```
Paperclip Issue (in_review)
    │
    ├── has "impact-gate-bypass" label? → skip, post bypass notice
    │
    ▼
Worker reads touchedFiles from issue body
    │
    ▼
Worker queries Blast Radius Touch Index:
    fr_impact_set    = FR files overlapping touchedFiles
    regression_set   = Bug files overlapping touchedFiles
    │
    ▼
Runner executes tests:
    for fr in fr_impact_set:
        run FR acceptance tests
    for bug in regression_set:
        run bug regression tests
    │
    ▼
Evaluate:
    total_tests >= 10 AND all pass? → PASS → done
    any fail? → FAIL → in_progress + blocking issues
    runner error? → ERROR → escalation comment
```

---

## 4. Integration Points

| System | Direction | Purpose |
|---|---|---|
| Paperclip API | Read/Write | Read issue, transition status, post comments, create blocking issues |
| Blast Radius Touch Index | Read | Query `fr_impact_set` and `regression_set` |
| Impact Gate test suite | Execute | Run FR acceptance + bug regression tests |
| Test results | Read | Parse test output for PASS/FAIL/ERROR |

---

## 5. Worker Configuration

### Workflow: `impact-gate-worker.yml`

| Trigger | Cadence |
|---|---|
| `schedule` | Every 5 minutes |
| `repository_dispatch` | On `issue_status_changed` |
| `workflow_dispatch` | Manual with `issue_id`, `old_status`, `dry_run` |

**Secrets required:** `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `PAPERCLIP_COMPANY_ID`

### Workflow: `impact-gate-scan-done.yml`

| Trigger | Cadence |
|---|---|
| `schedule` | Every 5 minutes |
| `workflow_dispatch` | Manual with `days_back`, `dry_run`, `retroactive` |

---

## 6. Bypass Mechanism

Issues with label `impact-gate-bypass` (CEO-authorized) skip the gate entirely. The worker posts a notice and moves on without transitioning the issue.

---

## 7. Related Documents

- [runbook-ci-cd.md](../runbook-ci-cd.md) — CI/CD workflow documentation
- [runbook-impact-gate-scan-done.md](../runbook-impact-gate-scan-done.md) — scan-done operations
- [BLAST_RADIUS_WORKER.md](BLAST_RADIUS_WORKER.md) — Blast Radius touch index
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) — touch_index schema
- [src/impact_gate/worker.py](../../src/impact_gate/worker.py)

## 8. Done-Guard (BTCAAAAA-25832)

To prevent agent-comment-triggered reopen loops on done issues, the Impact Gate
includes a belt-and-suspenders done-guard at three layers:

1. **Client layer** (`paperclip_client.py`): `transition_issue_status_board()`
   refuses to transition a done issue to a non-done status. Transitioning TO done
   is always allowed.

2. **Worker layer** (`impact_gate/worker.py`): `_post_comment()` calls
   `is_issue_done()` before posting. `process_issue()` sets `mute=True` when the
   issue status is done (suppressing all comments, transitions, and blocking
   issue creation). Muted gate results are persisted via
   `save_muted_gate_result()`.

3. **Blast Radius layer** (`blast_radius/generator.py`): `_post_comment()` skips
   when the issue is done.

All guards are fail-safe: if the status check itself fails (network error), the
operation proceeds rather than being silently suppressed.
