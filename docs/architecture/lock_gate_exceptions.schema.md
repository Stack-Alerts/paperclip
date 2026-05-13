# lock_gate_exceptions.json — Schema Documentation

**Version:** 2

## File Structure

```json
{
  "version": 2,
  "description": "Human-readable description of the file purpose.",
  "$schema": "docs/architecture/lock_gate_exceptions.schema.md",
  "exceptions": [
    { /* ExceptionEntry */ }
  ]
}
```

- `version` — integer. Must be `2`.
- `description` — string. Free-text.
- `$schema` — string. Must point to this document.
- `exceptions` — array of `ExceptionEntry` objects. May be empty (`[]`).

## ExceptionEntry

```json
{
  "module": "src/data_manager",
  "scope_description": "Refactor download pipeline — PR #456",
  "expires_iso": "2026-05-25T12:00:00Z",
  "approval_id": "COMMENT:https://github.com/org/repo/issues/123#issuecomment-456",
  "approved_by": "board"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `module` | string | **yes** | Path of the locked module being excepted. Must match a `path` entry in `.module_lock_registry.json`. |
| `scope_description` | string | **yes** | Human-readable description of the approved change scope. |
| `expires_iso` | string\|null | **yes** | ISO 8601 datetime in UTC (e.g., `"2026-05-25T12:00:00Z"`). `null` means never expires (board-plan-approved only). |
| `approval_id` | string | **yes** | Paperclip approval ID, or `COMMENT:<paperclip-comment-url>` linking to the approval comment. |
| `approved_by` | string | **yes** | Must be one of: `"board"` (planned path) or `"ceo-emergency"` (emergency path). `"cto-emergency"` is **not** valid per board directive 2026-05-11. |

### Validation Rules

1. `module` must be a non-empty string.
2. `scope_description` must be a non-empty string.
3. `expires_iso`:
   - If not `null`, must be valid ISO 8601 datetime with timezone (UTC).
   - If not `null` and `approved_by` is `"ceo-emergency"` (or `"board"` for Path B), the expiry must be **≤ 4 hours** from the time of entry creation.
   - If `expires_iso` is in the past, the entry is treated as **expired and ignored**.
4. `approval_id` must be a non-empty string.
5. `approved_by` must be exactly `"board"` or `"ceo-emergency"`. `"cto-emergency"` is rejected.

### Authority Model (Board Directive 2026-05-11)

| Path | Approver | `approved_by` | Max Duration | Gate Behavior |
|---|---|---|---|---|
| A (planned) | Board | `"board"` | Unlimited (`null`) | Full pass |
| B.1 (CEO emergency) | CEO | `"ceo-emergency"` | 4 hours | Expires after 4h |
| B.2 (board emergency) | Board | `"board"` | 4 hours | Expires after 4h |

**CTO no longer has unilateral emergency unlock authority.** Any entry with `approved_by: "cto-emergency"` is rejected.
