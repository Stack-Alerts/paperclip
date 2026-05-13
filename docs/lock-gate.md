# Lock Gate — Module Change Protection

## Overview

The lock gate is a CI gate that blocks pull requests touching any path registered in
`.module_lock_registry.json` unless a valid, non-expired exception exists in
`lock_gate_exceptions.json`.

It runs on every PR and push to `main`/`master` via `.github/workflows/lock-gate.yml`.

## How It Works

1. The gate computes the diff against the PR merge-base (`origin/main...HEAD`).
2. For each changed file, it checks:
   - **Direct hit**: the path matches a locked entry (prefix match for directories, exact
     match for files).
   - **Indirect hit**: a locked module depends on the changed file (reverse dependency
     lookup in `dep_graph.json`).
3. If any hit is not covered by a valid, non-expired exception in `lock_gate_exceptions.json`,
   the gate **blocks** the pipeline with exit code 1 and prints a failure report.

## Reading a Gate Failure Report

```
========================================================================
LOCK GATE BLOCKED - locked modules touched without exception
========================================================================

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

## Unblocking

To unblock, follow the procedure in `docs/runbook-module-lock.md`:

- **Path A** — Board-approved planned exception (permanent)
- **Path B.1** — CEO emergency exception (4-hour window)
- **Path B.2** — Board emergency exception (4-hour window)

## Local Testing

```bash
# Test against the last commit
python scripts/lock_gate.py --local

# Test against a diff fixture
python scripts/lock_gate.py --diff-file /tmp/test_diff.txt

# Validate exceptions file schema
python scripts/lock_gate.py --validate-exceptions
```

## Related Documents

- `docs/runbook-module-lock.md` — Full runbook with unlock procedures
- `docs/architecture/lock_gate_exceptions.schema.md` — Exception entry schema documentation
- `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md` — Exception request template
- `.github/CODEOWNERS` — CEO + board approval requirement for exceptions file

## Auto-Create CTO Sign-Off on Gate Block

When the lock gate blocks a PR, the CI workflow (`.github/workflows/lock-gate.yml`)
automatically creates a `high`-priority Paperclip issue requesting CTO sign-off.
The issue includes the blocked module details, PR link, and a deduplication key
to prevent duplicates on force-push. See `docs/runbook-module-lock.md` for details.

## Nightly CI Test Alert

`.github/workflows/test.yml` runs nightly at 04:00 UTC. On failure, a
`critical`-priority Paperclip issue is created and assigned to the CTO with
the CI run URL and test output. On success, no issue is created.

## Freeze-Lift CI Evidence Package (BTCAAAAA-1879)

The freeze-lift evidence package is a comprehensive test suite at `tests/freeze_lift/` that
proves the module lock freeze-lift mechanism works correctly. It runs as a separate CI
workflow (`.github/workflows/freeze-lift-evidence.yml`) on every push and nightly.

### Evidence Pillars

| # | Pillar | What It Proves | Tests |
|---|--------|----------------|-------|
| 1 | **Canary on main** | Gate passes on clean branches, exceptions file is valid | `TestCanaryOnMain` |
| 2 | **Broken-branch block** | Branches touching locked modules without exceptions are blocked (exit 1) | `TestBrokenBranchBlock` |
| 3a | **Escape hatch Path A** | Board-approved permanent exceptions correctly unblock | `TestEscapeHatchPathA` |
| 3b | **Escape hatch Path B** | Emergency exceptions (CEO/board) with 4h windows work; expired/over-4h are rejected | `TestEscapeHatchPathB` |
| 4 | **Locked-itself** | Gate's own files (gate script, registry, exceptions, workflow) are registered and block without exception | `TestLockedItself` |
| 5 | **Freeze-lift cycle** | End-to-end: freeze -> detect block -> apply exception -> lift | `TestFreezeLiftCycle` |
| 6 | **Schema contracts** | Exceptions file (v2), registry (v1), approved_by validation, module-path consistency | `TestSchemaAndContracts` |

### Running Locally

```bash
pytest tests/freeze_lift/ -v
```

### CI Evidence Workflow

`.github/workflows/freeze-lift-evidence.yml`:
- Runs on every push to `main`/`master` and every PR
- Runs nightly at 05:00 UTC
- Uploads test output as a build artifact
- Fails the pipeline if any evidence test fails

### Adding New Evidence

When adding a new locked module or exception path, add a corresponding test to
`tests/freeze_lift/test_freeze_lift_evidence.py` that proves the new mechanism
works. The evidence package must always pass before marking a lock-gate issue as done.
