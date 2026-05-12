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
- `lock_gate_exceptions.schema.md` — Exception entry schema documentation
- `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md` — Exception request template
- `.github/CODEOWNERS` — CEO + board approval requirement for exceptions file
