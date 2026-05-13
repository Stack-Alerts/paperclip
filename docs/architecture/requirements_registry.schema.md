# requirements_registry.json — Schema Documentation

**Version:** 1
**Owner:** Architect (73eaab54)
**ADRs:** ADR-0002

## File Structure

```json
{
  "version": 1,
  "$schema": "docs/architecture/requirements_registry.schema.md",
  "description": "Human-readable description of the file purpose.",
  "generated_at": "2026-05-13T16:30:00Z",
  "generated_by": "agent-name (uuid)",
  "parent_issue": "BTCAAAAA-NNNNN",
  "requirements": [
    { /* RequirementEntry */ }
  ]
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | **yes** | Schema version. Must be `1`. |
| `$schema` | string | **yes** | Path to this schema document. |
| `description` | string | **yes** | Human-readable purpose. |
| `generated_at` | string | no | ISO 8601 UTC timestamp of generation. |
| `generated_by` | string | no | Agent name/UUID that created the file. |
| `parent_issue` | string | no | Paperclip issue ID that spawned this registry. |
| `requirements` | array | **yes** | Array of `RequirementEntry` objects. May be empty `[]`. |

---

## RequirementEntry

```json
{
  "id": "REQ-DATA-001",
  "type": "FR",
  "title": "UnifiedDataManager serves as single source of truth",
  "description": "Detailed description of what the requirement mandates.",
  "source_issues": ["BTCAAAAA-1479"],
  "source_modules": ["src/data_manager/unified_manager.py"],
  "test_files": ["tests/unit/test_data_manager_integrity.py"],
  "test_markers": ["@pytest.mark.fr('FDR-850')"],
  "status": "active",
  "priority": "critical",
  "tags": ["data-manager", "singleton"],
  "owner_agent": "PlatformEngineer",
  "superseded_by": null
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | **yes** | Unique requirement identifier. Format: `REQ-{DOMAIN}-{NNN}` (e.g., `REQ-DATA-001`). |
| `type` | string | **yes** | One of: `FR`, `NFR`, `BR`, `AR`. See §Type Definitions. |
| `title` | string | **yes** | Human-readable summary (max 120 chars). |
| `description` | string | **yes** | Detailed description of the requirement. |
| `source_issues` | string[] | **yes** | Paperclip issue IDs that originated or modified this requirement. |
| `source_modules` | string[] | **yes** | Source file paths implementing this requirement. Relative to repo root. |
| `test_files` | string[] | **yes** | Test file paths that verify this requirement. May be empty if no tests exist. |
| `test_markers` | string[] | no | pytest marker strings used in test files (e.g., `@pytest.mark.fr('FDR-850')`). |
| `status` | string | **yes** | One of: `active`, `draft`, `deprecated`. |
| `priority` | string | **yes** | One of: `critical`, `high`, `medium`, `low`. |
| `tags` | string[] | no | Free-form tags for filtering and grouping. |
| `owner_agent` | string | **yes** | Agent name responsible for this requirement. |
| `superseded_by` | string\|null | no | ID of the requirement that replaces this one (when status=`deprecated`). |

### Type Definitions

| Type | Meaning | Use When |
|------|---------|----------|
| `FR` | Functional Requirement | What the system MUST do (feature, behavior) |
| `NFR` | Non-Functional Requirement | Quality attributes (performance, reliability, security) |
| `BR` | Business Rule | Domain constraint or policy (not a system behavior) |
| `AR` | Architectural Requirement | Design constraint (must use pattern X, must go through layer Y) |

### Status Lifecycle

```
draft → active → deprecated
          ↑         │
          └─────────┘ (reactivation — rare)
```

- `draft` — Proposed but not yet approved. Not enforced by CI.
- `active` — Approved and enforced. CI gates check this.
- `deprecated` — No longer required. Preserved for traceability history. Must set `superseded_by`.

### Priority Mapping to CI Behavior

| Priority | Lock Gate | Impact Gate | Gap Detection |
|----------|-----------|-------------|---------------|
| `critical` | Hard block — must have exception | Always runs | Alerts on gap |
| `high` | Hard block — must have exception | Always runs | Warns on gap |
| `medium` | Warns | Runs if related files changed | Logs on gap |
| `low` | No enforcement | Skipped unless explicit | No alert |

---

## ID Naming Convention

```
REQ-{DOMAIN}-{NNN}

DOMAIN:
  DATA   — Data ingestion, caching, integrity
  SIGNAL — Signal generation, building blocks
  TRADE  — Trade execution, P&L, registry
  STRAT  — Strategy config, validation, auto-fix
  ITM    — Institutional trade management
  CI     — CI/CD pipeline, gating, quality
  UI     — User interface, Qt components
  QA     — QA process, verification, audits

NNN: Zero-padded sequential number (001, 002, ...)
```

---

## Validation Rules

### Structural Validation (CI-enforced)

1. `version` must be a positive integer.
2. Every entry must have all required fields populated.
3. `id` must match `^REQ-[A-Z]+-\d{3}$`.
4. `type` must be one of: FR, NFR, BR, AR.
5. `status` must be one of: active, draft, deprecated.
6. `priority` must be one of: critical, high, medium, low.
7. `source_issues` and `source_modules` must be non-empty for `active` requirements.
8. `superseded_by` is required when `status` is `deprecated`.

### Semantic Validation (CI-enforced)

1. No duplicate `id` values.
2. `test_files` paths must exist on disk (checked at CI runtime).
3. `source_modules` paths must exist on disk (checked at CI runtime).
4. Active requirements without `test_files` are flagged as `needs-test`.

### Link Integrity Validation (Manual / Scheduled)

1. Each `source_issue` reference must resolve to a valid Paperclip issue.
2. Each `test_marker` must actually appear in the referenced `test_files`.
3. Deprecated requirements must have `superseded_by` pointing to an existing requirement.

---

## Integration with Existing Systems

### Lock Gate (`scripts/lock_gate.py`)

When the lock gate detects a changed locked module, it loads `requirements_registry.json` and finds all requirements where `source_modules` intersects the changed files. The CI output lists affected requirements:

```
LOCK GATE: src/data_manager/unified_manager.py changed
  → Affected requirements: REQ-DATA-001, REQ-TRADE-001, REQ-CI-006
  → Required tests: tests/unit/test_data_manager_integrity.py, ...
```

### Impact Gate (`scripts/impact_gate_worker.py`)

When an issue transitions to `in_review`, the Impact Gate can cross-reference `touchedFiles` against `requirements_registry.json` to identify which FR acceptance tests to run, supplementing the Touch Index query.

### Gap Detection (scheduled CI)

A scheduled workflow scans `requirements_registry.json` and reports:
- Requirements with no test files (gap)
- Requirements where test files don't exist on disk (stale reference)
- Test files not referenced by any requirement (orphan test)

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-13 | Architect (73eaab54) | Initial version — BTCAAAAA-25644 |
