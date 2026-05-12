# Runbook: Module Lock System

## Overview

The module lock system prevents uncoordinated changes to high-blast-radius modules.
Locked modules are registered in `.module_lock_registry.json`. The lock gate
(`scripts/lock_gate.py`) runs in CI on every PR and push to `main`/`master`.

To modify a locked module, you must obtain an **exception** — a time-limited or
permanent approval recorded in `lock_gate_exceptions.json`.

---

## Path A — Planned, Board-Approved (Unlimited Duration)

Use when: You have board-approved plan that includes changes to a locked module.

### Procedure

1. **File an issue** using `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md`
2. **Attach the board-approved plan** (paperclip issue link or board decision record)
3. **Board approves** the exception request
4. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "<locked-path>",
     "scope_description": "<scope of approved change>",
     "expires_iso": null,
     "approval_id": "<board-approved-plan-id>",
     "approved_by": "board"
   }
   ```
5. PR can merge with the exception active

### Required Phrasing

The board must approve using one of these exact statements:
- *"Approved as planned per [plan reference]. Exception is permanent (no expiry)."*
- *"Approved. This exception does not expire."*

---

## Path B.1 — CEO Emergency (4-Hour Window)

Use when: A critical production issue requires immediate changes to a locked module,
and the board cannot convene within the required timeframe.

### Authority

**CEO only.** CTO does not have unilateral emergency unlock authority per board
directive 2026-05-11.

### Procedure

1. **CEO declares emergency** via comment on the PR or a paperclip issue
2. **CEO approves** the exception with maximum 4-hour window
3. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "<locked-path>",
     "scope_description": "<emergency change description>",
     "expires_iso": "<now + 4h, ISO 8601 UTC>",
     "approval_id": "COMMENT:<url-to-ceo-approval-comment>",
     "approved_by": "ceo-emergency"
   }
   ```
4. PR merges with exception active
5. **Clock starts** — exception auto-expires after 4 hours
6. **Follow-up**: File a post-mortem issue and seek Path A approval if the change needs to persist

### Required Phrasing

The CEO must use one of these exact statements to approve:
- *"Emergency approved. Expires at YYYY-MM-DDTHH:MM:SSZ."*
- *"CEO emergency unlock granted for [scope]. Expiry: YYYY-MM-DDTHH:MM:SSZ."*

"Emergency approved" without an explicit expiry is **not valid**. The PlatformEngineer
must reject entries without a valid `expires_iso`.

---

## Path B.2 — Board Emergency (4-Hour Window)

Use when: An urgent change is needed and the board convenes but cannot approve it
via the full Path A planning process.

### Procedure

1. **Board declares emergency** via board decision record
2. **Board approves** the exception with maximum 4-hour window
3. **PlatformEngineer adds** an entry to `lock_gate_exceptions.json`:
   ```json
   {
     "module": "<locked-path>",
     "scope_description": "<emergency change description>",
     "expires_iso": "<now + 4h, ISO 8601 UTC>",
     "approval_id": "<board-emergency-decision-id>",
     "approved_by": "board"
   }
   ```
4. PR merges with exception active
5. **Clock starts** — exception auto-expires after 4 hours

---

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

## Validation Rules (Enforced by CI)

- `approved_by` must be `"board"` or `"ceo-emergency"` — `"cto-emergency"` is **rejected**
- Emergency entries (`approved_by: "ceo-emergency"` or Path B.2 `"board"`) must have
  `expires_iso` ≤ 4 hours from entry creation time
- Expired entries (`expires_iso` in the past) are treated as inactive and ignored
- `lock_gate_exceptions.json` requires CEO + board approval via CODEOWNERS

## CI Gate

The lock gate runs automatically:
- On every PR to `main`/`master`
- On every push to `main`/`master`
- Via `.github/workflows/lock-gate.yml`

To validate exceptions file locally:
```bash
python scripts/lock_gate.py --validate-exceptions
```

## Nightly dep_graph Refresh

A scheduled GitHub Actions workflow regenerates `dep_graph.json` nightly at 02:00 UTC
via `.github/workflows/dep-graph-refresh.yml`. This ensures the reverse-dependency
lookup used by the lock gate is up to date.

## Related Documents

- `docs/lock-gate.md` — Lock gate usage guide
- `lock_gate_exceptions.schema.md` — Exception entry schema documentation
- `.github/ISSUE_TEMPLATE/qa-locked-module-exception.md` — Exception request template
- `.github/CODEOWNERS` — CEO + board approval requirement for exceptions file

## Auto-Create CTO Sign-Off on Gate Block

`.github/workflows/lock-gate.yml` is extended to auto-create a CTO sign-off
Paperclip issue when the lock gate blocks a PR.  This happens in two steps:

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
its body.  Force-pushes with the same SHA are idempotent — only a comment is
added.  New commits on the same PR create new sign-off issues.

## Nightly CI Test Alert

`.github/workflows/test.yml` runs on a **nightly schedule** (04:00 UTC) in
addition to push/PR triggers.  When the scheduled run fails:

1. The test output is captured to `/tmp/test-output.txt`.
2. `scripts/nightly_test_alert.py` creates a `critical`-priority Paperclip
   issue assigned to the CTO with the CI run URL and test output.
3. On a successful nightly run, no Paperclip issue is created.

## Related Workflows

- `.github/workflows/lock-gate.yml` — CI gate with auto CTO sign-off on block
- `.github/workflows/test.yml` — Nightly tests with failure alerting
- `.github/workflows/lock-exception-signoff.yml` — Exception entry automation
- `.github/workflows/dep-graph-refresh.yml` — Nightly dependency graph refresh
