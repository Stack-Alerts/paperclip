# Lock Gate — Module Change Protection

## Overview

The lock gate is a CI gate that blocks pull requests touching any path registered in
`.module_lock_registry.json` unless a valid exception exists in `lock_gate_exceptions.json`.

It runs on every PR and push to `main`/`master` via `.github/workflows/lock-gate.yml`.

## How It Works

1. The gate computes the diff against the PR merge-base (`origin/main...HEAD`).
2. For each changed file, it checks:
   - **Direct hit**: the path matches a locked entry (prefix match for directories, exact
     match for files).
   - **Indirect hit**: a locked module depends on the changed file (reverse dependency
     lookup in `dep_graph.json`).
3. If any hit is not covered by an exception in `lock_gate_exceptions.json`, the gate
   **blocks** the pipeline with exit code 1 and prints a failure report.

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

Each block shows:
- **File**: the file in your PR diff that triggered the gate
- **Locked**: the locked path from the registry that matches
- **Reason**: why this module is locked

The gate prints the remediation steps:
1. File an exception request using `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md`
2. Get CTO approval and document the `approval_id` in `lock_gate_exceptions.json`
3. Re-run the CI pipeline

## Exceptions

The `lock_gate_exceptions.json` file contains an `exceptions` array. Each entry:

```json
{
  "path": "src/data_manager",
  "reason": "Approved refactor per BTCAAAAA-XXXX",
  "approval_id": "<CTO-approved ID>",
  "expires_at": null
}
```

Only the PlatformEngineer or CTO may add entries. The exceptions file itself is locked.

## Local Testing

```bash
# Test against the last commit
python scripts/lock_gate.py --local

# Test against a diff fixture
python scripts/lock_gate.py --diff-file /tmp/test_diff.txt
```
