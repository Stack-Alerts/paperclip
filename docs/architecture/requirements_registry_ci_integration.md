# Requirements Registry — CI Integration Spec

**Owner:** Architect (73eaab54)
**Target agent:** AutomationEngineer (BTCAAAAA-25645)
**Issue:** BTCAAAAA-25644 → BTCAAAAA-25645

## 1. Purpose

This document specifies how `requirements_registry.json` integrates into the existing CI pipeline (lock gate, impact gate, test suite, and gap scanner).

## 2. Integration Points

### 2.1 Lock Gate (`scripts/lock_gate.py`)

**When:** Every git push — lock gate checks if any changed file matches a locked module path.

**New behavior:** When the lock gate detects a change to a locked module, it additionally:
1. Loads `requirements_registry.json`
2. Finds all requirements where `source_modules` intersects the set of changed files
3. Lists affected requirements and their test files in the CI output

**Example output:**
```
LOCK GATE: src/data_manager/unified_manager.py changed (locked module)
  Exception: BTCAAAAA-2182 (valid until 2026-05-26)
  Affected requirements (from registry):
    REQ-DATA-001: UnifiedDataManager serves as single source of truth
      → Tests: tests/unit/test_data_manager_integrity.py
    REQ-TRADE-001: TradeRegistry central ledger
      → Tests: tests/bug_regression/test_canary_trade_execution.py
    REQ-CI-006: Canary trade execution
      → Tests: tests/bug_regression/test_canary_trade_execution.py
  ACTION: Verify all 3 requirements pass their tests before merge.
```

**Implementation:**
```python
# In scripts/lock_gate.py, after detecting locked module changes:
REQ_REGISTRY = repo_root / "requirements_registry.json"
if REQ_REGISTRY.exists():
    registry = load_json(REQ_REGISTRY)
    changed_set = set(changed_files)
    for req in registry.get("requirements", []):
        if req.get("status") != "active":
            continue
        sources = set(req.get("source_modules", []))
        if changed_set & sources:
            affected_reqs.append(req)
    # Print affected requirements table
```

### 2.2 Impact Gate (`scripts/impact_gate_worker.py`)

**When:** An issue transitions to `in_review` — Impact Gate reads `touchedFiles` from the issue.

**New behavior:** In addition to the Touch Index query, the Impact Gate can cross-reference `touchedFiles` against `requirements_registry.json` to:
1. Identify FR acceptance tests to run beyond what the Touch Index returns
2. Show which requirements are directly impacted by the change
3. Add requirement IDs to the gate report for traceability

**Fallback:** If the registry query returns nothing (new file not yet registered), fall back to Touch Index only. The registry is supplemental, not a hard dependency.

### 2.3 CI Test Suite (`.github/workflows/test.yml`)

**When:** On push/PR — the test suite runs selected test directories.

**New behavior:** A new job `requirements-coverage` runs:
```yaml
requirements-coverage:
  name: Requirements registry validation
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Validate registry
      run: python scripts/validate_requirements_registry.py --ci
    - name: Check gap coverage
      run: python scripts/validate_requirements_registry.py --gaps --ci
      continue-on-error: true  # gaps are non-blocking, informational only
```

### 2.4 Gap Detection (scheduled: `requirements-gap-scan.yml`)

**New workflow:** Weekly scheduled scan that:
1. Runs `scripts/validate_requirements_registry.py --gaps`
2. If gaps found (exit code 2), posts a comment on BTCAAAAA-25639 with the gap report
3. Identifies:
   - Active requirements with no test files
   - Requirements where test files don't exist on disk
   - Stale `superseded_by` references
   - Rogue test files not referenced by any requirement

## 3. Data Flow

```
┌──────────────────────────┐
│ requirements_registry.json│
└──────────┬───────────────┘
           │
     ┌─────┼─────────────────┐
     │     │                 │
     ▼     ▼                 ▼
┌─────────┐ ┌──────────┐ ┌──────────┐
│Lock Gate│ │Impact Gate│ │Gap Scan  │
│(per push│ │(per issue │ │(weekly)  │
│ verify) │ │ transition)│ │          │
└────┬────┘ └─────┬─────┘ └────┬─────┘
     │            │            │
     ▼            ▼            ▼
┌─────────────────────────────────────┐
│         pytest test suite           │
│  Tests selected by registry lookup  │
└─────────────────────────────────────┘
```

## 4. Registry Query API (Python module)

Create `scripts/requirements_query.py` as a shared module:

```python
# scripts/requirements_query.py
"""Shared query functions for requirements_registry.json."""

def find_by_module(module_path: str) -> list[dict]:
    """Find all requirements that list the given source module."""
    ...

def find_by_issue(issue_id: str) -> list[dict]:
    """Find all requirements that reference the given issue."""
    ...

def find_by_tag(tag: str) -> list[dict]:
    """Find all requirements matching a tag."""
    ...

def get_affected_tests(changed_files: list[str]) -> set[str]:
    """Given changed files, return set of test file paths to run."""
    ...

def get_requirement(requirement_id: str) -> dict | None:
    """Get a single requirement by ID."""
    ...
```

This module is consumed by `lock_gate.py`, `impact_gate_worker.py`, and the gap scanner, avoiding duplicated registry-loading logic.

## 5. Acceptance Criteria

- [ ] `lock_gate.py` loads registry and reports affected requirements on locked-module change
- [ ] `validate_requirements_registry.py` passes in CI (structural check)
- [ ] Gap scan workflow scheduled (weekly) with output posted to BTCAAAAA-25639
- [ ] `requirements_query.py` shared module created with find_by_module, get_affected_tests
- [ ] Impact Gate cross-references registry for supplemental FR test discovery
- [ ] No regression: all existing CI workflows continue to pass

## 6. References

- [requirements_registry.json](../../requirements_registry.json)
- [ADR-0002](adr/ADR-0002-test-to-requirements-traceability.md)
- [validate_requirements_registry.py](../../scripts/validate_requirements_registry.py)
