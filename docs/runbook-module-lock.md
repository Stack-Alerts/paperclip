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

## Automated Exception Sign-Off (Webhook)

When an exception request is approved on a Paperclip issue, the **RepoSteward
CTO sign-off webhook** automates steps 3–5 of the Path A/B procedures:

1. RepoSteward sends a `repository_dispatch` event with type
   `lock_exception_signed_off` containing the approval payload.
2. `.github/workflows/lock-exception-signoff.yml` catches the event and runs
   `scripts/lock_exception_signoff.py`.
3. The script validates the payload, appends the entry to
   `lock_gate_exceptions.json`, commits, and pushes.
4. A confirmation comment is posted on the Paperclip issue.
5. The issue is transitioned to `done`.

The webhook payload must include:

| Field | Description |
|---|---|
| `issue_id` | Paperclip issue UUID |
| `module` | Locked module path from `.module_lock_registry.json` |
| `scope` | Scope description of the approved change |
| `approved_by` | `"board"` or `"ceo-emergency"` |
| `approval_id` | Board-approved plan ID or `COMMENT:<url>` |
| `expires_iso` | ISO 8601 UTC expiry, or omit for permanent (Path A only) |

## Nightly Alert

`.github/workflows/lock-gate-nightly-alert.yml` runs nightly at 03:00 UTC and
creates a Paperclip alert issue if any exceptions have expired, are expiring
within 24h, or have schema validation errors. The alert is posted as a `todo`
issue with the `lock-gate` and `nightly-alert` labels.

## Related Workflows

- `.github/workflows/lock-exception-signoff.yml` — Automated exception entry
- `.github/workflows/lock-gate-nightly-alert.yml` — Nightly status alert
- `.github/workflows/lock-gate.yml` — CI gate
- `.github/workflows/dep-graph-refresh.yml` — Nightly dependency graph refresh
