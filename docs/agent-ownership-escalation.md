# Cross-Section Change Escalation (CTO-mediated)

**Issue:** BTCAAAAA-38996 (Workspace Confinement Phase 2) · **Parent plan:** BTCAAAAA-38991 (rev 6b53a14c)

This is the workflow for when an agent needs to change code **outside its owned
section**. It keeps every cross-section change surgical, ticketed, delegated,
verified, and gated — so the repo has an auditable trail instead of broad grants
or silent out-of-scope edits.

## Two complementary guardrails

| Mechanism | File | What it is |
|-----------|------|------------|
| **Agent-ownership guard** | `agent_ownership.json` + `scripts/agent_ownership_guard.py` | Per-agent **allow-list** of owned path globs. Soft, reversible pre-commit guard. |
| **Module-lock gate** | `.module_lock_registry.json` + `scripts/lock_gate.py` | Board-approval **deny-list** for a few critical files. |

The ownership guard decides *whether* a write is out of scope. The escalation
helper (`scripts/escalate_cross_section.py`) is what you run *when it blocks you*.

## The loop

```
requesting agent needs an out-of-scope change
  │
  ▼
agent-ownership guard blocks the commit  ──►  prints the one-command escalation
  │
  ▼
scripts/escalate_cross_section.py
  • resolves the owning section from agent_ownership.json
  • creates a CTO-assigned child issue (surgical, references the owner section)
  • sets the requesting issue status=blocked, blockedByIssueIds=[child]
  │
  ▼
CTO delegates  ──►  reassigns the child to the owning agent
  │
  ▼
owning agent implements + tests  (only within its owned scope)
  │
  ▼
CTO verifies (tests green, scope respected)  ──►  marks the child `done`
  │
  ▼
Paperclip auto-resolves the blocker  ──►  requesting issue auto-resumes
```

## One-command escalation

From inside the blocked agent's heartbeat:

```bash
python3 scripts/escalate_cross_section.py \
  --issue "$PAPERCLIP_TASK_ID" \
  --paths alembic/versions/0123_add_signal_col.py \
  --summary "WebUI signals form needs a new nullable column on the signals table" \
  --requesting-role UIEngineer
```

- Add `--dry-run` to preview the exact API payloads without creating anything.
- `--assign owner` skips the CTO hop and assigns the child straight to the owner
  (use only when the CTO has pre-authorized that section handoff).
- The script resolves the owner from `agent_ownership.json` and the owner's agent
  id from `agent_id_map`, so no ids need to be hand-copied.

## Worked example (the board's DBA example)

**Scenario:** the WebUI agent (`UIEngineer`) is editing a form and needs a DB
migration, which lives in `alembic/**` — owned by `DatabaseAdministrator`.

1. **Block.** UIEngineer stages `alembic/versions/xxxx_add_col.py`; the pre-commit
   guard refuses and prints the escalation command.
2. **Escalate.** UIEngineer runs `escalate_cross_section.py`. It creates child
   issue *"Cross-section change for DatabaseAdministrator: alembic/…"* assigned to
   the **CTO**, `parentId` = the WebUI issue, and sets the WebUI issue
   `status=blocked`, `blockedByIssueIds=[child]`.
3. **Delegate.** The CTO reassigns the child to `DatabaseAdministrator` with a
   one-line delegation comment (scope = just this migration).
4. **Implement + test.** The DBA writes the migration under `alembic/**` and runs
   the migration/tests. All edits stay inside the DBA's owned scope, so the guard
   does not block the DBA.
5. **Verify.** The CTO checks tests are green and scope was respected, then PATCHes
   the child to `done` with a verification note.
6. **Release.** With all `blockedBy` children `done`, Paperclip fires
   `issue_blockers_resolved` and wakes the WebUI agent — its work auto-resumes.

## Traceability & token-spend guardrails

- **Every cross-section change = one child issue** with `parentId` linkage and a
  `blockedBy` edge. `GET /api/issues/{id}` shows `blockedBy` / `blocks` for audit.
- **Surgical, not broad.** The child carries the *minimal* change the requesting
  work needs — never a blanket grant of the section. Relaxing an agent's whole
  section is a deliberate one-line edit to its `owns` list in `agent_ownership.json`
  by the CTO, not the default path.
- **Reversible bypass** (`AGENT_OWNERSHIP_BYPASS=1`) exists for a single justified
  out-of-scope commit; the reason must be noted in the commit/issue. It is an
  escape hatch, not the escalation path.

## Reference

- Guard: `scripts/agent_ownership_guard.py` (`--staged`, `--paths`, `--validate`)
- Escalation helper: `scripts/escalate_cross_section.py` (`--dry-run` to preview)
- Manifest: `agent_ownership.json` (`agents.<Role>.owns`, `agent_id_map`)
- Pre-commit installer: `scripts/hooks/pre-commit`
