# Runbook: Module Lock System

## Overview

The module lock system prevents uncoordinated changes to high-blast-radius modules.
Locked modules are registered in `.module_lock_registry.json`. The lock gate
(`scripts/lock_gate.py`) runs in CI on every PR and push to `main`/`master`.

To modify a locked module, you must obtain an **exception** — a time-limited or
permanent approval recorded in `lock_gate_exceptions.json`. After approval, a
mandatory **QA sign-off checklist** must be completed before the PR can merge.

## Path A — Board-Approved Planned Exception (Unlimited Duration)

Use when: You have a board-approved plan that includes changes to a locked module.

### Procedure

1. **File an exception request** using `docs/runbook-module-lock.md` as a guide;
   the auto-created CTO sign-off issue (when the lock gate blocks) serves as the
   request record.
2. **Attach the board-approved plan** (Paperclip issue link or board decision record).
3. **Board approves** the exception request.
4. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "src/data_manager",
     "scope_description": "Refactor download pipeline — PR #456",
     "expires_iso": null,
     "approval_id": "plan:BTCAAAAA-1479",
     "approved_by": "board"
   }
   ```
5. **QA sign-off** is triggered (see §7 — QA Exception Checklist).
6. PR can merge only after QA checklist is fully verified.

### Required Phrasing

The board must approve using one of these exact statements:
- *"Approved as planned per [plan reference]. Exception is permanent (no expiry)."*
- *"Approved. This exception does not expire."*

### Concrete Example

**Real entry from bootstrap (plan BTCAAAAA-1479):**
```json
{
  "module": "scripts/lock_gate.py",
  "scope_description": "Bootstrap exception BTCAAAAA-1486: initial creation of the lock gate itself. The gate must be created before it can enforce itself. Approved per plan BTCAAAAA-1479 §1.",
  "expires_iso": null,
  "approval_id": "plan:BTCAAAAA-1479",
  "approved_by": "board"
}
```

## Path B.1 — CEO Emergency Exception (4-Hour Window)

Use when: A critical production issue requires immediate changes to a locked module,
and the board cannot convene within the required timeframe.

### Authority

**CEO only.** CTO does not have unilateral emergency unlock authority per board
directive 2026-05-11.

### Procedure

1. **CEO declares emergency** via comment on the PR or a Paperclip issue.
2. **CEO approves** the exception with maximum 4-hour window.
3. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "src/optimizer_v3/core/trade_registry.py",
     "scope_description": "Hotfix: trade registry schema migration failed in production — must roll back within 4h",
     "expires_iso": "2026-05-12T06:00:00Z",
     "approval_id": "COMMENT:https://github.com/anomalyco/BTC-Trade-Engine-PaperClip/issues/456#issuecomment-789",
     "approved_by": "ceo-emergency"
   }
   ```
4. PR merges with exception active.
5. **Clock starts** — exception auto-expires after 4 hours.
6. **Follow-up**: File a post-mortem issue and seek Path A approval if the change needs to persist.

### Required Phrasing

The CEO must use one of these exact statements to approve:
- *"Emergency approved. Expires at YYYY-MM-DDTHH:MM:SSZ."*
- *"CEO emergency unlock granted for [scope]. Expiry: YYYY-MM-DDTHH:MM:SSZ."*

"Emergency approved" without an explicit expiry is **not valid**. The PlatformEngineer
must reject entries without a valid `expires_iso`.

## Path B.2 — Board Emergency Exception (4-Hour Window)

Use when: An urgent change is needed and the board convenes but cannot approve it
via the full Path A planning process.

### Procedure

1. **Board declares emergency** via board decision record.
2. **Board approves** the exception with maximum 4-hour window.
3. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "src/detectors/building_blocks/registry.py",
     "scope_description": "Emergency: building block registry hotfix for production detector crash",
     "expires_iso": "2026-05-12T14:00:00Z",
     "approval_id": "board-emergency-decision-2026-05-12",
     "approved_by": "board"
   }
   ```
4. PR merges with exception active.
5. **Clock starts** — exception auto-expires after 4 hours.

## Exception Entry Reference

```json
{
  "module": "src/data_manager",
  "scope_description": "Refactor download pipeline — PR #456",
  "expires_iso": "2026-05-25T12:00:00Z",
  "approval_id": "COMMENT:https://github.com/org/repo/issues/123#issuecomment-456",
  "approved_by": "board"
}
```

| Field | Description |
|---|---|
| `module` | Locked module path from `.module_lock_registry.json` |
| `scope_description` | What change is approved and why |
| `expires_iso` | ISO 8601 UTC datetime, or `null` for permanent (Path A only) |
| `approval_id` | Paperclip plan/issue ID, or `COMMENT:<url>` |
| `approved_by` | `"board"` (Path A or B.2) or `"ceo-emergency"` (Path B.1) |

### Locked Modules Registry

`.module_lock_registry.json` currently locks these paths:

| Path | Reason |
|---|---|
| `src/data_manager` | UnifiedDataManager — shared data source of truth |
| `src/optimizer_v3/core/trade_registry.py` | Central trade ledger |
| `src/optimizer_v3/core/institutional_signal_evaluator.py` | Signal evaluation pipeline |
| `src/detectors/building_blocks/registry.py` | Building block discovery |
| `src/itm/state/manager.py` | ITM position persistence |
| `src/optimizer_v3/database/` | 9 ORM managers under database layer |
| `scripts/lock_gate.py` | Lock gate enforcement script |
| `.module_lock_registry.json` | Registry file itself |
| `lock_gate_exceptions.json` | Exceptions file itself |
| `.github/workflows/lock-gate.yml` | Lock gate CI workflow |
| `tests/bug_regression/test_canary_trade_execution.py` | Canary regression test |
| `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md` | Exception request template |

## Validation Rules (Enforced by CI)

- `approved_by` must be `"board"` or `"ceo-emergency"` — `"cto-emergency"` is **rejected**
- Emergency entries (`approved_by: "ceo-emergency"` or Path B.2 `"board"`) must have
  `expires_iso` ≤ 4 hours from entry creation time
- Expired entries (`expires_iso` in the past) are treated as inactive and ignored
- `lock_gate_exceptions.json` requires CEO + board approval via CODEOWNERS
- `module` must match a path in `.module_lock_registry.json`
- `scope_description` and `approval_id` must be non-empty strings

### CI Validation Example

When the lock gate runs with `--validate-exceptions`:
```bash
python scripts/lock_gate.py --validate-exceptions
```

Sample output on validation failure:
```
Validation error: entry for module 'src/unknown_module' is not in .module_lock_registry.json
Validation error: entry approved_by 'cto-emergency' is not a valid approver
Validation error: entry expires_iso '2026-05-12T01:00:00Z' exceeds 4-hour maximum for ceo-emergency
```

## QA Exception Checklist Process

When a PR receives a lock-gate exception (any path), the following QA sign-off
process is mandatory before the PR can merge:

### Trigger

After the exception entry is added to `lock_gate_exceptions.json` by the
`lock-exception-signoff` workflow, the **QAEngineer** is automatically assigned
to the sign-off issue (created from `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md`).

### Checklist

The QA sign-off issue contains four mandatory checks:

| # | Check | Evidence Required | Owner |
|---|---|---|---|
| 1 | pytest passed (all tests, not just smoke) | CI run URL showing full test suite green | QAEngineer |
| 2 | UI path verified end-to-end | Screenshot or log artifact | QAEngineer |
| 3 | Trade execution confirmed in dry-run (≥1 trade in known 24h window) | Dry-run log excerpt or trade ledger entry | QAEngineer |
| 4 | Canary smoke test passed | CI run URL for `tests/bug_regression/test_canary_trade_execution.py` | QAEngineer |

### Enforcement

**Automated enforcement** is preferred but not yet implemented. Until automation
is in place, the following **manual-policy alternative** applies (approved by CTO):

1. The QAEngineer verifies all four checklist items manually.
2. The QAEngineer checks all four boxes and adds their sign-off comment.
3. The PlatformEngineer **must not merge** any PR with an open, unchecked, or
   partially checked QA sign-off issue for the same exception.
4. Violations of this policy are escalated to the CEO as a process incident.

### Sign-Off Comment Template

```
## QA Sign-Off — Locked Module Exception

- [x] pytest passed — CI URL: https://github.com/.../actions/runs/12345
- [x] UI path verified — Screenshot: https://github.com/.../assets/67890
- [x] Trade execution confirmed — Trade ID: abc-def-ghi in dry-run ledger
- [x] Canary smoke test passed — CI URL: https://github.com/.../actions/runs/12346

**QAEngineer:** All four checks verified. Exception approved for merge.
```

### Concrete Workflow Example

1. Lock gate blocks PR #456 touching `src/data_manager`.
2. `lock_gate_create_signoff.py` auto-creates CTO sign-off issue `BTCAAAAA-1500`.
3. Board approves per Path A — `lock_exception_signoff.py` adds the exception
   entry and transitions issue `BTCAAAAA-1500` to `done`.
4. `lock-exception-signoff` workflow auto-creates QA sign-off issue
   `BTCAAAAA-1501` using the template with the 4-item checklist.
5. QAEngineer runs tests, captures evidence, checks all boxes, and signs off.
6. PR #456 merges.

## CI Gate

The lock gate runs automatically:
- On every PR to `main`/`master`
- On every push to `main`/`master`
- Via `.github/workflows/lock-gate.yml`

To validate exceptions file locally:
```bash
python scripts/lock_gate.py --validate-exceptions
```

### Gate Failure Report Example

```
================================================================================
LOCK GATE BLOCKED — locked modules touched without exception
================================================================================

  File:    src/data_manager/unified_manager.py
  Locked:  src/data_manager
  Reason:  UnifiedDataManager — shared single source of truth for data
           ingestion, caching, and retrieval.
  ---
  File:    src/optimizer_v3/core/trade_registry.py
  Locked:  src/optimizer_v3/core/trade_registry.py
  Reason:  TradeRegistry — central ledger for all optimizer-produced
           trade records.
```

### Auto-Create CTO Sign-Off on Gate Block

`.github/workflows/lock-gate.yml` is extended to auto-create a CTO sign-off
Paperclip issue when the lock gate blocks a PR. This happens in two steps:

1. `scripts/lock_gate.py --json-summary` emits a structured JSON report of
   the blocked modules, PR number, commit SHA, and PR URL.
2. On gate failure, `scripts/lock_gate_create_signoff.py` reads that JSON and:
   - Checks idempotency: if a sign-off issue already exists for the same
     PR + commit SHA, it comments on the existing issue instead of creating
     a duplicate.
   - Creates a `high`-priority Paperclip issue with the `cto-signoff-required`
     label, assigned to the CTO agent.
   - Includes the blocked module details, gate output, and PR link in the
     issue body.

The sign-off issue contains a deduplication marker (`<!-- dedup:... -->`) in
its body. Force-pushes with the same SHA are idempotent — only a comment is
added. New commits on the same PR create new sign-off issues.

**Example auto-created issue body:**
```
**Lock Gate blocked PR #456**

**PR:** https://github.com/anomalyco/BTC-Trade-Engine-PaperClip/pull/456
**Commit:** a1b2c3d4e5f6...

### Blocked Modules

- `src/data_manager` — file `src/data_manager/unified_manager.py` — UnifiedDataManager

### Action Required

To unblock, approve via one of the paths in docs/runbook-module-lock.md:
- Path A — Board-approved planned exception (permanent)
- Path B.1 — CEO emergency (4-hour window)
- Path B.2 — Board emergency (4-hour window)

<!-- dedup:a1b2c3d4e5f6... -->
```

### Nightly CI Test Alert

`.github/workflows/test.yml` runs on a **nightly schedule** (04:00 UTC) in
addition to push/PR triggers. When the scheduled run fails:

1. The test output is captured to `/tmp/test-output.txt`.
2. `scripts/nightly_test_alert.py` creates a `critical`-priority Paperclip
   issue assigned to the CTO with the CI run URL and test output.
3. On a successful nightly run, no Paperclip issue is created.

### Nightly dep_graph Refresh

A scheduled GitHub Actions workflow regenerates `dep_graph.json` nightly at 02:00 UTC
via `.github/workflows/dep-graph-refresh.yml`. This ensures the reverse-dependency
lookup used by the lock gate is up to date.

## Post-Rollout Retrospective

After the module lock system ships (issue BTCAAAAA-1491 closed), a retrospective
must be scheduled:

- **Follow-up issue:** Created and assigned to CEO
- **Date:** 2 weeks after BTCAAAAA-1491 closes
- **Agenda:**
  1. Review exception requests granted during the first 2 weeks
  2. Evaluate whether the QA checklist caught any issues
  3. Assess if the 4-hour emergency window is sufficient
  4. Decide on automation priority for QA checklist enforcement
  5. Propose any changes to the locked modules list

## Related Documents

- `docs/lock-gate.md` — Lock gate usage guide
- `docs/architecture/lock_gate_exceptions.schema.md` — Exception entry schema documentation
- `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md` — QA sign-off checklist template
- `.github/CODEOWNERS` — CEO + board approval requirement for exceptions file

## Related Workflows

- `.github/workflows/lock-gate.yml` — CI gate with auto CTO sign-off on block
- `.github/workflows/lock-gate-nightly-alert.yml` — Nightly lock gate alerting
- `.github/workflows/lock-exception-signoff.yml` — Exception entry automation
- `.github/workflows/test.yml` — Nightly tests with failure alerting
- `.github/workflows/dep-graph-refresh.yml` — Nightly dependency graph refresh
