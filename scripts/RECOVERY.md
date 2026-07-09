# paperclip-btcaaaaa-main recovery script

Single-script disaster recovery for this worktree. Bundles the live
embedded-postgres DB, the custom paperclip configurations, and the
current worktree git ref into a single restore point that lives on
gdrive (`gdrive:Paperclip-Backups/<companyId>/...`) and locally at
`/home/sirrus/paperclip-snapshots/`.

## Usage

The recommended entry point is **`doctor`** — it does the smart thing
based on paperclip's state.

```bash
# smart flow: status → start (if down) → offer recovery options
./scripts/recovery.sh doctor

# capture the current state (idempotent, takes ~50s local / ~5 min with upload)
./scripts/recovery.sh snapshot

# list all restore points (gdrive + local hourly dumps + local disaster snapshots)
./scripts/recovery.sh list

# preview a restore (does not touch the running paperclip)
./scripts/recovery.sh restore <id> --dry-run

# actually restore (will prompt "restore yes" to confirm unless --yes)
./scripts/recovery.sh restore <id>
./scripts/recovery.sh restore <id> --yes    # auto-confirm (used by the paperclip-backup plugin worker)

# start paperclip if down (no-op if already up)
./scripts/recovery.sh start

# paperclip + DB + rclone health check (read-only)
./scripts/recovery.sh status

# integrity check (fails if any expected file/path is missing)
./scripts/recovery.sh verify
```

## Decision flow (what `doctor` does)

1. **Is paperclip up?** Curl `/api/health` on `:3100`. If yes → done.
2. **If down, try to start it.** Run `scripts/launch-dev.sh` and wait up to
   60s for `/api/health` to come up. If yes → done.
3. **If start fails, offer recovery.** Print the recent log tail and
   instruct the user to run `list` then `restore <id>` to recover.

## Tiered retention (24/7 + 24/7)

Snapshots are kept in two tiers simultaneously:
- **Last 7 chronologically** (rapid recency for the most recent 7 snapshots)
- **One per day for the last 24 calendar days** (longer-term recovery)

This gives you both "I just made a mistake" recovery (last 7 hours) and
"I need to roll back to last week" recovery (last 24 days) at the same
time. Hardlink deduplication via `rsync --link-dest` means each snapshot
only stores files that actually changed. Storage grows by ~9MB per
snapshot (only the files that changed) regardless of snapshot count.

## How restore works

1. Stops the paperclip tmux session AND the embedded-postgres child
   process (it must be quiet before step 3's rsync — otherwise rsync
   overwrites files postgres is holding open, producing torn writes).
2. Backs up the current
   `/home/sirrus/.paperclip-worktrees/instances/paperclip-btcaaaaa-main/db/`
   to `/home/sirrus/paperclip-snapshots/restore-before-<id>/data/`.
3. Restores the data dir from the snapshot, then **clears the live
   `pg_wal/`** so postgres does a fresh startup from the snapshot's base
   (the snapshot excludes `pg_wal` by design; the live WAL is from the
   pre-kill postgres and is inconsistent with the new base).
4. Starts a temporary embedded-postgres (after `initdb`) on a free port
   and loads the snapshot's `paperclip-*.sql.gz` (custom `-Fc` format)
   via `pg_restore`. This is a sanity check that the SQL dump is
   well-formed; the live data dir has the snapshot's base from step 3.
5. `git checkout` the worktree to the snapshot's recorded ref.
6. `pnpm install --frozen-lockfile && pnpm --filter @paperclipai/server build && pnpm --filter @paperclipai/ui build`
7. Restarts `./scripts/launch-dev.sh` and waits for `/api/health` to come up.

## Why this is safe to run on a live paperclip

- The recovery always backs up the current data dir to
  `restore-before-<id>/data/` before overwriting it.
- Dry-run mode is the default path on `restore <id> --dry-run` and never touches
  the live system.
- `verify` only reads the filesystem and is safe to run anytime.
- `status` only opens a TCP connect; doesn't touch the DB.
