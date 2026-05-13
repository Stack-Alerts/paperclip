# ADR-0002: Test-Case-to-Requirements Traceability Schema

**Issue:** BTCAAAAA-25644 (child of BTCAAAAA-25639)  
**Author:** Architect (73eaab54)  
**Status:** Proposed  
**Date:** 2026-05-13  
**Priority:** HIGH  
**Parent:** BTCAAAAA-25639 — Requirements Management System

---

## Context

The board directive (BTCAAAAA-25639) requires a properly linked requirements management solution where every test case and issue is mapped to requirements. The current state provides:

1. **Process-level traceability** (`REQUIREMENTS_TRACEABILITY.md`) — issue lifecycle linking (goal → requirement → implementation → QA → done), but no code/test linkage.
2. **Informal test markers** — `@pytest.mark.fr("FDR-850")` and `@pytest.mark.bug("BTCAAAAA-736")` exist but are not canonically mapped to a requirements list.
3. **Blast Radius / Touch Index** — maps files to issues (FRs/bugs) via PostgreSQL, but the mapping is file→issue, not requirement→test.
4. **Module Lock Registry** — locked modules with approval tracking, but no requirement traceability for those modules.

The gap: when module X changes, we cannot deterministically answer "which requirements does this affect?" or "which tests verify those requirements?".

## Decision: Lightweight JSON Registry with pytest Marker Integration

We will implement a canonical **Requirements Registry** (`requirements_registry.json`) with bidirectional traceability:

```
Requirement ──→ Source Modules ──→ Dep Graph (blast radius)
     │
     ├──→ Test Files + Markers ──→ pytest collection (CI)
     │
     └──→ Source Issues ──→ Paperclip issue chain
```

### Schema Design

```json
{
  "version": 1,
  "requirements": [
    {
      "id": "REQ-DATA-001",
      "type": "FR",
      "title": "UnifiedDataManager single source of truth",
      "description": "The UnifiedDataManager provides a singleton interface for data ingestion, caching, and retrieval across all subsystems including backtesting, live trading, and dry-run pipelines.",
      "source_issues": ["BTCAAAAA-1479"],
      "source_modules": ["src/data_manager/unified_manager.py"],
      "test_files": ["tests/unit/test_data_manager_integrity.py"],
      "test_markers": [],
      "status": "active",
      "priority": "critical",
      "tags": ["data-manager", "singleton", "caching"],
      "owner_agent": "PlatformEngineer"
    }
  ]
}
```

### Requirement Types

| Type | Meaning | Example |
|------|---------|---------|
| `FR` | Functional Requirement | "System MUST validate strategies before backtest" |
| `NFR` | Non-Functional Requirement | "Backtest must complete in <30s for 90-day window" |
| `BR` | Business Rule | "No trade may exceed 5% capital allocation" |
| `AR` | Architectural Requirement | "All data access goes through UnifiedDataManager" |

### Integration Points

| System | Integration | Mechanism |
|--------|-------------|-----------|
| **CI Lock Gate** | When a locked module changes, find affected requirements | `lock_gate.py` loads registry, checks `source_modules` |
| **Impact Gate** | When an issue moves to `in_review`, find all impacted requirements | Worker queries registry by touched files |
| **pytest** | Run requirement-verification tests on module change | `requirements_registry.json` → test file list for pytest invocation |
| **Gap Detection** | CI job to detect untested requirements | Compare registry entries against test file existence |

### Naming Convention

Requirement IDs follow the pattern: `REQ-{DOMAIN}-{NNN}`

| Domain | Prefix | Scope |
|--------|--------|-------|
| `DATA` | `REQ-DATA-NNN` | Data ingestion, caching, integrity |
| `SIGNAL` | `REQ-SIGNAL-NNN` | Signal generation, building blocks |
| `TRADE` | `REQ-TRADE-NNN` | Trade execution, P&L, registry |
| `STRAT` | `REQ-STRAT-NNN` | Strategy config, validation, auto-fix |
| `ITM` | `REQ-ITM-NNN` | Institutional trade management |
| `CI` | `REQ-CI-NNN` | CI/CD pipeline, gating, quality |
| `UI` | `REQ-UI-NNN` | User interface, Qt components |
| `QA` | `REQ-QA-NNN` | QA process, verification, audits |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Requirements Registry                         │
│                   requirements_registry.json                    │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐     │
│  │   REQ    │───→│   Source     │───→│   Test Files      │     │
│  │  (id,    │    │   Modules    │    │   + Markers       │     │
│  │  type,   │    │   (paths)    │    │   (paths+tags)    │     │
│  │  desc)   │    └──────────────┘    └───────┬───────────┘     │
│  └────┬─────┘                               │                  │
│       │                                     │                  │
│       │  ┌──────────────┐                   │                  │
│       └─→│   Source     │                   │                  │
│          │   Issues     │                   │                  │
│          │ (BTCAAAAA-X) │                   │                  │
│          └──────────────┘                   │                  │
└─────────────────────────────────────────────┼──────────────────┘
                                              │
                    ┌─────────────────────────┼──────────────┐
                    │                         ▼              │
                    │  ┌──────────────────────────────────┐  │
                    │  │        CI / QA Pipeline          │  │
                    │  │                                  │  │
                    │  │  Lock Gate ──→ affected REQs     │  │
                    │  │  Impact Gate ──→ test execution  │  │
                    │  │  Gap Scanner ──→ coverage report │  │
                    │  │  pytest ──→ test collection      │  │
                    │  └──────────────────────────────────┘  │
                    │                    CI                    │
                    └─────────────────────────────────────────┘
```

### Data Flow: Module Change → Test Execution

```
1. git push triggers CI
2. Lock Gate identifies changed files
3. Lock Gate loads requirements_registry.json
4. For each changed file:
   a. Find requirements whose source_modules contains the file
   b. Find test_files for those requirements
   c. Collect test_markers for pytest -m filtering
5. Run pytest with collected test files + markers
6. Report: which requirements were verified, which tests failed
```

---

## Trade-Offs

| Approach | Pros | Cons |
|----------|------|------|
| **JSON registry (chosen)** | Zero infrastructure; human-readable; works in CI without DB; integrates with existing lock gate JSON patterns | Manual maintenance; no query language; scaling limit at ~500 requirements |
| **PostgreSQL (touch_index)** | Queryable; existing infra; auto-populated from issue ingestion | Tight coupling to touch_index schema; overengineered for a registry of ~100 requirements |
| **Markdown mapping** | Maximal readability; git-diff friendly | Not machine-parseable for CI; no schema validation |
| **in-code decorators** | Live with code; refactoring-safe | Doesn't capture cross-module requirements; harder to audit holistically |

**Decision:** JSON registry, mirroring the `lock_gate_exceptions.json` pattern already established in this codebase. Schema validation via JSON Schema in CI.

---

## Maintenance Process

### Adding a New Requirement

1. Assign the next available ID in the domain prefix
2. Add entry to `requirements_registry.json`
3. Add (or update) test files with `@pytest.mark.fr("REQ-DOMAIN-NNN")` markers
4. If the requirement affects locked modules, verify lock gate exceptions are in place
5. Commit with message: `req: add REQ-DOMAIN-NNN — {title} — BTCAAAAA-NNN`

### Deprecating a Requirement

1. Set `status: "deprecated"` in the registry entry
2. Add `superseded_by` field pointing to the replacement requirement ID
3. Do NOT delete the entry — traceability history is preserved

### Gap Detection (CI job)

A scheduled CI job (`requirements-gap-scan.yml`) will:
1. Load `requirements_registry.json`
2. For each `active` requirement:
   - Verify `test_files` exist on disk
   - Verify test markers are present in those files
   - Report gaps: requirements with zero tests, missing test files, missing markers

---

## Connected Issues

| Issue | Relationship |
|-------|-------------|
| BTCAAAAA-25639 | Parent — Requirements Management System |
| BTCAAAAA-25645 | Child — AutomationEngineer: CI lock-module detection with registry integration |
| BTCAAAAA-25646 | Child — DocWriter: traceability process documentation |
| BTCAAAAA-25641 | Child — QAEngineer: test coverage verification |
| BTCAAAAA-1479 | Related — Module lock system and escape hatch |
| BTCAAAAA-1476 | Related — Zero-trades canary test (archetypal FR-bug-test chain) |

---

## Verification Checklist

- [x] Schema design documented (this ADR)
- [ ] `requirements_registry.json` created with seed data from existing tests/docs
- [ ] JSON Schema validation file created
- [ ] CI lock gate integration spec delivered to AutomationEngineer
- [ ] DocWriter integration spec delivered
- [ ] QAEngineer gap detection process defined
- [ ] Push to origin

---

## References

- [REQUIREMENTS_TRACEABILITY.md](../REQUIREMENTS_TRACEABILITY.md) — Process traceability
- [IMPACT_GATE.md](../IMPACT_GATE.md) — Impact Gate architecture
- [BLAST_RADIUS_WORKER.md](../BLAST_RADIUS_WORKER.md) — Blast Radius touch index
- [lock_gate_exceptions.schema.md](../lock_gate_exceptions.schema.md) — Schema pattern to follow
- [ADR-0001](ADR-0001-zero-trades-regression-audit.md) — Prior ADR format
