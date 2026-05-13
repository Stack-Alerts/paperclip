# ADR-0003: Lock Gate Exception Scoping — Process Gap Analysis

**Issue:** BTCAAAAA-25639 (parent: BTCAAAAA-1476)
**Author:** Architect (73eaab54)
**Status:** In Review
**Date:** 2026-05-13
**Priority:** CRITICAL
**ADR-0001:** Zero-Trades Regression Audit
**ADR-0002:** Traceability Schema

---

## Context

BTCAAAAA-1476 ("Trades Not Working again") has recurred after a previous fix and QA sign-off. The lock gate system (designed per plan BTCAAAAA-1479) was supposed to prevent unauthorized changes to critical modules. However, a process gap allowed follow-up changes to `src/data_manager` to be made under an already-granted exception without new approval.

### Timeline

| Date | Event |
|------|-------|
| 2026-05-11 | Lock gate system deployed (13 modules locked) |
| 2026-05-12 02:00 | Exception granted for `src/data_manager` — BTCAAAAA-2182 (startTime pagination fix) |
| 2026-05-12 | QA sign-off on zero-trades fix (BTCAAAAA-1205) |
| 2026-05-12 18:25 | Board observes zero trades again (both modes) — BTCAAAAA-1476 re-opened |
| 2026-05-13 15:03 | `d04f210f` — second `data_manager` change committed under same exception (floor start_ms for coarse timeframes) |
| 2026-05-13 18:23 | `e40fbe1d` — fix single-core TP/SL guard (not in data_manager) |

### The Gap

The lock gate exception for `src/data_manager` was scoped to the **entire module path**, not specific lines or change descriptions. Once the exception was granted for BTCAAAAA-2182, any subsequent commit touching any file under `src/data_manager/` would pass the lock gate — even if it was a completely different change with different risk profile.

The `scope_description` describes specific lines (`unified_manager.py:526-531`), but the `module` key is the coarse path `src/data_manager`. The lock gate (`scripts/lock_gate.py`) matches on `module` (path prefix), not on specific line ranges.

---

## Decision: Harden the Lock Gate Exception Model

We will implement three changes to close this process gap:

### 1. Line-Scoped Exceptions (New Schema Field)

Add an optional `files` field to exception entries that restricts the exception to specific files and line ranges:

```json
{
  "module": "src/data_manager",
  "files": [
    {"path": "src/data_manager/unified_manager.py", "lines": "526-531"},
    {"path": "src/data_manager/binance/rest_client.py", "lines": "296-310"}
  ],
  "scope_description": "BTCAAAAA-2182: Add startTime pagination...",
  "state": "active"
}
```

When `files` is present, the lock gate verifies that **all** changed lines fall within the scoped file+line ranges. When `files` is absent (backward compat), the current path-prefix behavior applies with a warning.

### 2. Exception Lifecycle States

Add a `state` field:

| State | Meaning |
|-------|---------|
| `active` | Exception is in force; gate passes |
| `consumed` | Exception was used (commit merged); subsequent commits require new exception |
| `expired` | Exception timestamp expired |
| `revoked` | Manually revoked by board or CTO |

Transition on merge: `active → consumed`.

### 3. Post-Merge Exception Audit

After each merge to `main`:
1. The lock gate records which exceptions were consumed
2. A scheduled workflow scans for `active` exceptions >48h without a merged commit
3. The Impact Gate worker runs verification tests for changed locked modules

---

## Architecture Decision Diagram

### Current (Broken)

```
Commit → lock_gate.py → exception exists for module?
                         │
                    ┌────┴────┐
                    ▼         ▼
                   YES       NO → BLOCK
                    │
                    ▼
                  PASS
              (any line, any scope)
```

### Proposed (Hardened)

```
Commit → lock_gate.py → exception exists for module?
                              │
                         ┌────┴────┐
                         ▼         ▼
                        YES       NO → BLOCK
                         │
                         ▼
                   files field present?
                         │
                    ┌────┴────┐
                    ▼         ▼
                   YES        NO
                    │          │
                    ▼          ▼
              lines in      WARNING
              scope?        (legacy)
                 │            │
            ┌────┴────┐       ▼
            ▼         ▼     PASS
           YES        NO
            │          │
            ▼          ▼
          PASS       BLOCK
            │
            ▼
        exception
        consumed
```

---

## Trade-Offs

| Approach | Pros | Cons |
|----------|------|------|
| **Line-scoped exceptions** | Granular control; prevents exception reuse; backward-compatible | Requires lock_gate.py changes; CI runtime cost for diff parsing |
| **Consumed-state lifecycle** | Prevents exception from covering multiple commits; clear audit trail | Requires post-merge hook; adds complexity |
| **One-time tokens** | Simplest model — single-use | Requires new tokens for each commit; CI friction for multi-commit features |
| **CTO re-approval per commit** | Maximum control | CTO bottleneck; defeats purpose of planned changes |

---

## Migration Path

### Phase 1 (this heartbeat)
1. Add `"files": []` and `"state": "active"` fields to `lock_gate_exceptions.json` entry for `src/data_manager`
2. Update `scripts/lock_gate.py` to parse optional `files` field and perform line-range validation
3. Update `docs/architecture/lock_gate_exceptions.schema.md` with new fields

### Phase 2 (next heartbeat)
4. Wire `scripts/lock_module_verify.py` into CI as post-merge verification gate
5. Add scheduled exception-audit workflow

---

## Connected Issues

| Issue | Relationship |
|-------|-------------|
| BTCAAAAA-1476 | Parent — board observed zero trades, triggered this audit |
| BTCAAAAA-1479 | Lock gate plan — being hardened |
| BTCAAAAA-25639 | Requirements traceability parent |
| BTCAAAAA-25644 | ADR-0002 — traceability schema |
| BTCAAAAA-2182 | Original exception that was reused |
| (future) | Child — AutomationEngineer: lock_gate.py hardening |
| (future) | Child — DocWriter: update lock_gate_exceptions.schema.md |

---

## DoD

- [x] Process gap identified and documented
- [x] Three-part hardening proposal designed
- [x] Migration path defined (3-phase)
- [x] Trade-offs evaluated
- [ ] Implementation of Phase 1 (delegated to AutomationEngineer via child issue)
- [ ] Push to origin
