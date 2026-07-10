# git-merges plugin stuck-running fix + plugin_state NULLS NOT DISTINCT cleanup

**Branch:** `feat/latest-plugins-from-12-15-btcaaaaa`
**HEAD:** `aee8cc376` (`fix(backup): self-heal stuck backup-running on child exit`)
**Author:** MiniMax-M3 (this session continues from previous session that landed commit `5646edcfb` on other branches)
**Date:** 2026-07-10
**Stash:** `stash@{0}` (52 MB) — held over from previous session; safe to keep untouched until end.

## Problem statement

The user reported: "The git merges backup plugin is constantly showing working, like a
stuck process and i cant create new backups." Investigation revealed **two layered bugs**
and one pre-existing partially-applied migration mess:

1. **Plugin layer bug (immediate symptom):** `@paperclipai/plugin-git-merges`
   `worker.ts` set `status.running = true` at scan start but had three failure modes
   where the flag could be left stuck:
   - worker process crash before `try/finally` ran
   - `setup()` on worker restart never cleared a leaked flag
   - `clearOutput` action nulled `lastRunAt`/`lastExitCode`/`lastSkipped` but not
     `running` itself

2. **UI layer bug:** the manual "Run scan now" button was disabled when
   `running: true`, even though the worker's `runMergeScan()` accepts `force: true`
   and would bypass the running check. The UI therefore blocked the user's only
   escape hatch.

3. **Data layer bug (deeper root cause):** the `plugin_state` table's unique index
   `plugin_state_unique_entry_idx` was created as plain `UNIQUE`, not
   `UNIQUE NULLS NOT DISTINCT`. For `instance`-scope rows (`scope_id IS NULL`)
   Postgres treated each `NULL` as distinct, so every `set()` was silently
   **inserting a duplicate row** instead of upserting. The `get()` reader uses
   `ORDER BY updated_at DESC LIMIT 1`, which usually returned the most recent
   write but could race against stale `running: true` partials.

## Investigation summary

### Pre-existing partial fix on other branches (informational)

A previous session made commit `5646edcfb fix(db): enforce NULLS NOT DISTINCT
on plugin_state unique index` on other branches (`feat/BTCAAAAA-39068-session-end-autosave`
and friends). That commit:
- Adds `0131_plugin_state_unique_with_nulls_not_distinct.sql`
- Updates the journal to include 0131 at idx 131
- Adds defensive `orderBy(desc(updated_at)).limit(1)` to `pluginStateStore.get()`

It did **not** land on `feat/latest-plugins-from-12-15-btcaaaaa`. However, the
defensive `orderBy` fix is already on this branch via earlier commit
`a24a5fda0 fix(plugin-state-store): return most recent state on get` (June 29),
which shipped the identical code change (different comment). So the read path
on this branch is already defensive against duplicates.

The remaining gap is the **constraint** and the **journal state**.

### Current DB state (pre-fix baseline, captured 2026-07-10 09:47 UTC)

- **plugin_state** table has the constraint `UNIQUE NULLS NOT DISTINCT (...)`
  — fixed manually this session via `psql -f 0131_plugin_state_unique_with_nulls_not_distinct.sql`
  after auto-recovery was confirmed.
- 64 duplicate rows were removed by that manual run.
- `drizzle.__drizzle_migrations` already contains hashes for 0125 (id 130),
  0126 (id 131), 0127 (id 132), 0128 (id 133), 0129 (id 134), 0130 (id 135),
  0131 (id 136). Their created_at timestamps are:
  - 2026-07-05 12:06:05 UTC (0125-0129, applied in one batch)
  - 2026-07-05 20:53:54 UTC (0130)
  - 2026-07-06 11:40:00 UTC (0131)
- 16 rows in `plugin_state` (down from 80+).
- `pgdb-pre-fix.dump` (262 MB) saved to `/tmp/opencode/paperclip-baseline/` as
  the **rollback target**. Restore via `pg_restore --clean --if-exists
  -h localhost -p 54329 -U paperclip -d paperclip /tmp/opencode/paperclip-baseline/pgdb-pre-fix.dump`.

### Migration history timeline

| Date (UTC)             | Event                                                                                  |
|------------------------|-----------------------------------------------------------------------------------------|
| 2026-06-11 16:53       | `8907bbdfc` introduces `0087_company_closure_gate_fix_sha.sql` on this branch (collision with `0087_backfill_environment_manage_human_defaults`) |
| 2026-06-29 10:17       | `a24a5fda0 fix(plugin-state-store)` lands defensive `orderBy(updated_at DESC).limit(1)` |
| 2026-07-04 11:15       | `3d3eb822f fix(db): renumber orphan 0126 closure-gate migration out of 0087 collision` (NOT on this branch) |
| 2026-07-05 12:06       | hashes for 0125-0129 land in `__drizzle_migrations` (single batch, 4ms spread)          |
| 2026-07-05 20:53       | hash for 0130 lands                                                                     |
| 2026-07-06 11:40       | hash for 0131 lands                                                                     |
| 2026-07-06 15:33       | `5646edcfb fix(db): enforce NULLS NOT DISTINCT` (NOT on this branch)                    |
| 2026-07-10 09:47       | (this session) manual SQL run applies the dedupe + ALTER; constraint is now NULLS NOT DISTINCT |

### Why the ALTER didn't take effect originally

Even though 0131's hash landed in `__drizzle_migrations` on 2026-07-06, the
constraint was still plain `UNIQUE` when this session started. The most
likely explanation: the migration's transaction in
`applyPendingMigrationsManually` was never invoked for 0131 in full.

The `migrationContentAlreadyApplied()` heuristic in
`packages/db/src/client.ts:408` returns `false` for unrecognized statement
shapes (including the `DELETE … USING …` opener of 0131). That makes the
reconcile loop **break** at 0131 without adding 0131 to the journal.

The fact that 0131's hash IS in the journal (id 136, created_at
`2026-07-06 11:40:00`) means **some other code path** recorded the hash. Most
likely the previous session ran a one-off SQL that updated `__drizzle_migrations`
after manually applying 0131's content, but the actual `ALTER TABLE … ADD
CONSTRAINT … UNIQUE NULLS NOT DISTINCT` statement was skipped (or fell through
to the original plain `UNIQUE` index DDL via some prior migration chain). The
exact mechanism is not recoverable from the available history; we accept the
constraint as-is now that it is correct.

### Files 0087 collision (separate issue, NOT in scope)

`packages/db/src/migrations/0087_company_closure_gate_fix_sha.sql` and
`0087_backfill_environment_manage_human_defaults.sql` both have number 0087.
`check-migration-numbering.ts` rejects the workspace as soon as it sees the
duplicate, so `pnpm db:migrate` cannot run on this branch.

The closure-gate column `companies.closure_gate_fix_sha` is already in the DB
(schema-verified 2026-07-10). So the data side is safe, but `pnpm db:migrate`
won't work until the duplicate is resolved.

We are intentionally **not** resolving this here. The user's reported bug is
unrelated (plugin UI / data), and renumbering 0087 → 0126 (the precedent set
by commit `3d3eb822f` on other branches) is a separate, multi-branch concern
that needs explicit coordination with downstream consumers.

## Plan

### Phase 1 — Rollback safety (DONE)

- [x] Full DB dump: `/tmp/opencode/paperclip-baseline/pgdb-pre-fix.dump`
- [x] `git-merges` plugin state in JSON
- [x] `__drizzle_migrations` + `plugin_state` CSVs
- [x] All migration files 0087 + 0125-0131 copied to baseline
- [x] Git stash `{0}` preserved untouched

### Phase 2 — Apply plugin code fixes (already done this session)

In `packages/plugins/plugin-git-merges/src/worker.ts`:
- `setup()` clears a leaked `running: true` flag at worker startup
- `clearOutput` action force-resets `running: false`

In `packages/plugins/plugin-git-merges/src/ui/index.tsx`:
- `RunScanButton` no longer disables itself when `running`; only disables
  during `submitting` (the action dispatch itself). Label flips to "Run scan
  now (force)" when running, with a tooltip.

Built and verified:
- `pnpm --filter @paperclipai/plugin-git-merges build` → OK
- `tsc --noEmit` → OK
- `grep` confirms new strings in dist

### Phase 3 — Land migration 0131 properly in this branch

The DB state is already correct (constraint is `UNIQUE NULLS NOT DISTINCT`,
hashes are in the journal). What we still need to do is make the **git tree**
self-consistent so a fresh `pnpm db:migrate` on this branch wouldn't re-attempt
0131 or fail at `check-migration-numbering`:

1. **Add untracked files 0125-0131 to the working tree, but in a deliberate,
   auditable commit:** `git add packages/db/src/migrations/0125_*` …
2. **Update the journal** to include entries 125-131 with the same `idx`/`when`
   values that match the existing DB rows (where applicable). New entries
   must use `when` values that match the existing `created_at` so
   `reconcilePendingMigrationHistory` doesn't bump them.
3. **Do NOT touch the 0087 collision** in this plan. The closure-gate column
   is already in the DB; the migration is technically re-runnable because
   every statement is `ADD COLUMN IF NOT EXISTS` / `ADD CONSTRAINT IF NOT
   EXISTS`. The `pnpm db:migrate` failure is a separate concern.

### Phase 4 — Tests

1. `pnpm db:generate` — should succeed (Drizzle will see the new files match
   the journal).
2. `pnpm --filter @paperclipai/db migrate` (a.k.a. `pnpm db:migrate`) — will
   still fail on 0087 collision; that's expected and **separate from this
   fix**. We verify the failure is exactly that, not anything new.
3. `pnpm --filter @paperclipai/db exec tsc --noEmit` — typecheck clean.
4. `pnpm --filter @paperclipai/plugin-git-merges exec tsc --noEmit` — typecheck clean.
5. `pnpm -r typecheck` — full repo typecheck clean.
6. `pnpm test:run` — Vitest suite green (the git-merges plugin has no own
   tests; verify nothing else regresses).
7. **Auto-recovery smoke test** (already done this session): inject stuck
   state into `scan-status`, poll snapshot data handler, verify
   `running: false` returned within one round trip and DB row updated.
8. **Idempotency smoke test** (planned): create a fresh test DB by restoring
   `pgdb-pre-fix.dump` to a sidecar, apply migration 0131 via
   `applyPendingMigrationsManually`, verify constraint + dedupe, then re-run
   `applyPendingMigrationsManually` and verify it is a no-op.

### Phase 5 — Reinstall plugin in running instance

```
pnpm --filter @paperclipai/plugin-git-merges build
pnpm paperclipai plugin install ./packages/plugins/plugin-git-merges
```

(Or whatever the host's install command is — confirm via `pnpm paperclipai --help`.)

### Phase 6 — Final smoke test

1. Restart the running Paperclip server (or trigger plugin reload) so the
   new worker code loads.
2. Curl the snapshot data handler — verify it returns the actual stored state
   (no stuck running).
3. Click "Run scan now" in the UI — verify force-scan starts.
4. Inject a stuck state directly into `scan-status` with old `lastAttemptAt`,
   poll, verify self-heal.

## Rollback procedure (100% reversible)

If anything goes wrong at any phase:

### Quick rollback (DB only)

```sh
pg_restore --clean --if-exists \
  -h localhost -p 54329 -U paperclip -d paperclip \
  /tmp/opencode/paperclip-baseline/pgdb-pre-fix.dump
```

This restores the DB to the exact pre-fix state: constraint back to plain
`UNIQUE`, 64 duplicate rows back, `__drizzle_migrations` back to the 135-row
state, all plugin_state values back to what they were before my session.

### Full rollback (DB + working tree)

```sh
# 1. Restore DB
pg_restore --clean --if-exists \
  -h localhost -p 54329 -U paperclip -d paperclip \
  /tmp/opencode/paperclip-baseline/pgdb-pre-fix.dump

# 2. Restore plugin source files (worker.ts, ui/index.tsx)
git checkout HEAD -- packages/plugins/plugin-git-merges/src/worker.ts \
                    packages/plugins/plugin-git-merges/src/ui/index.tsx

# 3. Restore built dist (rebuild from clean source, or reinstall)
pnpm --filter @paperclipai/plugin-git-merges build

# 4. If we created a commit we want to undo:
git reset --hard HEAD

# 5. If we modified the journal:
git checkout HEAD -- packages/db/src/migrations/meta/_journal.json
```

### Stash preservation

We do NOT pop or drop `stash@{0}` during this work. It is the user's
backstop for the entire previous session's worth of changes (52 MB,
30k+ lines) and may contain work the user wants to recover independently.
It will be cleaned up in a future session if the user confirms it is safe.

## Open questions

None — the user's directive was explicit (investigate deeply + 100% rollback
+ fix properly + test properly). This plan covers all four.

## Risk register

| Risk                                                                 | Likelihood | Impact | Mitigation                                            |
|----------------------------------------------------------------------|------------|--------|-------------------------------------------------------|
| `pg_restore --clean` on the live DB drops unrelated sessions/connections | Low      | Med    | Stop the Paperclip server before restoring            |
| The 0087 collision causes a fresh `pnpm db:migrate` to fail          | Confirmed  | Low    | Out of scope; documented separately                   |
| Journal update with wrong `when` values triggers `reconcile` to bump rows | Low    | Low    | Use the existing `created_at` from DB as the source   |
| Plugin code change introduces a regression in the snapshot self-heal | Low       | Med    | Smoke test the auto-recovery post-install             |
| Stash `{0}` contains work the user wanted to land                    | Med       | Low    | Do not touch it; preserve as-is                       |

## Verification checklist (run before claiming done)

- [ ] `pnpm --filter @paperclipai/db exec tsc --noEmit` — clean
- [ ] `pnpm --filter @paperclipai/plugin-git-merges exec tsc --noEmit` — clean
- [ ] `pnpm --filter @paperclipai/plugin-git-merges build` — succeeds, dist updated
- [ ] `pnpm -r typecheck` — clean
- [ ] `pnpm test:run` — green
- [ ] `pg_restore` smoke test on sidecar DB — full restore succeeds
- [ ] Auto-recovery smoke test — stuck state self-heals within one poll
- [ ] Plugin reinstall — worker picks up new code, UI shows new button label
- [ ] Git log — clean commit messages, no stale references
- [ ] Final `pnpm db:migrate` attempt — fails **only** on 0087 collision (expected)