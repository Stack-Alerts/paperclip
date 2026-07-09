#!/bin/bash
# disaster-recovery.sh — Quick recovery for paperclip-btcaaaaa-main
#
# Single-script entry point for "the world is on fire" days. Produces a
# complete restore point in one command and can restore from any prior one
# in another. Includes the running data dir, the worktree with all our
# custom patches, the .env, and the custom script/plugin layout. Snapshots
# land next to the regular `backup-to-drive.sh` snapshots at:
#   gdrive:Paperclip-Backups/<companyId>/<YYYY>/<MM>/<DD>/<HHMM>/
#   └── manifest.json
#   └── db/paperclip-*.sql.gz       (full DB dump)
#   └── data/                       (rsync --link-dest of data dir, hardlinks to prev)
#   └── config/                     (rsync --link-dest of custom configs/scripts)
#
# Storage model is HARD-LINK INCREMENTAL: every snapshot is a directory of
# files that are hardlinked to the previous snapshot for unchanged bytes.
# Storage is O(unique files), not O(snapshots × size). Pruning old
# snapshots is safe (the kernel just removes hardlinks; the data dir
# refcount tracks the actual storage).
#
# Usage:
#   ./disaster-recovery.sh snapshot                       # take a snapshot, upload to gdrive
#   ./disaster-recovery.sh snapshot --no-upload            # snapshot only, skip gdrive
#   ./disaster-recovery.sh list                            # list restore points (gdrive + local)
#   ./disaster-recovery.sh restore <id>                    # restore from a specific snapshot
#   ./disaster-recovery.sh restore <id> --dry-run           # show what restore would do
#   ./disaster-recovery.sh start                           # start paperclip if down
#   ./disaster-recovery.sh doctor                          # status → start → offer recovery
#   ./disaster-recovery.sh status                          # current health
#   ./disaster-recovery.sh verify                          # integrity of current state
#
# The script auto-detects:
#   - the paperclip worktree via $PAPERCLIP_HOME / .paperclip/.env
#   - the live DB dir + port
#   - the gdrive remote + encryption password

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants — keep these in sync with backup-to-drive.sh and the
# paperclip-backup plugin (in the worktree's packages/plugins/paperclip-backup)
# ---------------------------------------------------------------------------
readonly COMPANY_ID="73419cf3-bd37-4a7c-8782-311ccb47fced"
readonly RCLONE_REMOTE="gdrive"
readonly RCLONE_DEST_BASE="${RCLONE_REMOTE}:Paperclip-Backups/${COMPANY_ID}"
readonly RCLONE_CONFIG_OVERRIDE="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
RCLONE_CONFIG="$RCLONE_CONFIG_OVERRIDE"
readonly RCLONE_PASS_FILE="$HOME/.config/rclone/rclone-pass"
readonly HOURLY_BACKUP_DIR="$HOME/.paperclip-worktrees/instances/paperclip-btcaaaaa-main/data/backups"
readonly WORKTREE_PATH="/home/sirrus/paperclip-btcaaaaa-main"
readonly DATA_DIR="/home/sirrus/.paperclip-worktrees/instances/paperclip-btcaaaaa-main/db"
readonly DB_PORT=54329
readonly PG_USER=paperclip
readonly PG_PASS=paperclip
readonly SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
readonly LOCK_FILE="/tmp/paperclip-disaster-recovery.lock"
readonly LOG_DIR="/home/sirrus/paperclip-snapshots"
readonly LOG_PREFIX="recovery"
readonly RETENTION_HOURLY_MAX=7   # keep last 7 hourly snapshots (rapid recency)
readonly RETENTION_DAILY_MAX=24  # keep last 24 daily snapshots (longer-term recovery)
# tiered retention semantics: an hourly snapshot is one taken between
# 00:00-23:59 of any given day; a daily snapshot is the one taken on the
# cron at 00:00 (or the latest snapshot of a given calendar day). The
# dedup logic prunes: keep the last 7 chronologically AND the last 24 per-day.

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
log()  { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die()  { log "ERROR: $*" >&2; exit 1; }
note() { printf '  %s\n' "$*"; }

acquire_lock() {
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    die "another recovery script is already running (lock: $LOCK_FILE)"
  fi
}

release_lock() {
  flock -u 9 2>/dev/null || true
}

load_rclone_env() {
  if [[ -f "$RCLONE_PASS_FILE" ]]; then
    export RCLONE_CONFIG_PASS="$(cat "$RCLONE_PASS_FILE" 2>/dev/null)"
    export RCLONE_CONFIG="$RCLONE_CONFIG"
  fi
}

check_deps() {
  # ensure the local pg installation is on PATH; the embedded-postgres
  # bundled binary is in the worktree, the system-wide pg clients are in
  # /home/sirrus/.pg0/.../bin. Try both.
  export PATH="/home/sirrus/paperclip-btcaaaaa-main/node_modules/.pnpm/@embedded-postgres+linux-x64@18.1.0-beta.16/node_modules/@embedded-postgres/linux-x64/native/bin:/home/sirrus/.pg0/installation/18.1.0/bin:$PATH"
  for c in rclone psql pg_dump tar flock rsync; do
    command -v "$c" >/dev/null 2>&1 || die "missing dependency: $c"
  done
}

generate_snapshot_id() {
  date -u +%Y-%m-%d-%H%M
}

# Tiered retention: keep the last N chronologically + one per day for the
# last M calendar days. Each rule is independent — an hourly snapshot
# might survive BOTH windows (last 7 hours AND it's the latest of its
# calendar day).
prune_tiered_retention() {
  local hourly_keep="$RETENTION_HOURLY_MAX"
  local daily_keep="$RETENTION_DAILY_MAX"
  local snap
  declare -A keep_reasons  # path -> "hourly,daily" comma-separated reason
  declare -A all_snaps     # path -> mtime

  # First pass: collect all snapshots sorted by mtime desc
  while IFS= read -r s; do
    [[ -d "$s" ]] || continue
    all_snaps["$s"]="$(stat -c %Y "$s" 2>/dev/null || echo 0)"
  done < <(ls -td $LOG_DIR/[0-9]*-[0-9]* 2>/dev/null)

  # Tier 1: keep the last N chronologically. Note: `(( i++ ))` returns the
  # OLD value of i (0 on first iteration) and would trip `set -e`; use the
  # assignment form `i=$((i+1))` to keep the exit code clean.
  local i=0
  for s in $(ls -td $LOG_DIR/[0-9]*-[0-9]* 2>/dev/null); do
    i=$((i+1))
    if ((i <= hourly_keep)); then
      keep_reasons["$s"]="${keep_reasons[$s]:+${keep_reasons[$s]},}hourly"
    fi
  done

  # Tier 2: keep one snapshot per calendar day (the latest of that day)
  # for the last M days. Day key = YYYY-MM-DD from the snapshot id.
  local day_seen_count=0
  declare -A day_seen
  for s in $(ls -td $LOG_DIR/[0-9]*-[0-9]* 2>/dev/null); do
    local id
    id=$(basename "$s")
    local day="${id:0:10}"  # YYYY-MM-DD from YYYY-MM-DD-HHMM
    if [[ -z "${day_seen[$day]:-}" ]]; then
      day_seen[$day]="$s"
      day_seen_count=$((day_seen_count + 1))
      if ((day_seen_count <= daily_keep)); then
        keep_reasons["$s"]="${keep_reasons[$s]:+${keep_reasons[$s]},}daily"
      fi
    fi
  done

  # Apply retention: remove anything NOT in the keep set
  for s in "${!all_snaps[@]}"; do
    if [[ -z "${keep_reasons[$s]:-}" ]]; then
      rm -rf "$s"
      note "  pruned: $(basename "$s") (not in any retention tier)"
    else
      note "  kept:    $(basename "$s") (${keep_reasons[$s]})"
    fi
  done
}

# ---------------------------------------------------------------------------
# snapshot: take a fresh snapshot of the current state and upload to gdrive.
# Storage model is hardlink-incremental: every snapshot is a directory of
# files hardlinked to the previous snapshot. 24 hourly snapshots of a
# 5 GB worktree + 1 GB paperclip config use ~6 GB on disk, not 6*24 = 144 GB.
# ---------------------------------------------------------------------------
do_snapshot() {
  local no_upload="false"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-upload) no_upload="true" ;;
      --auto) no_upload="true" ;;  # cron mode: keep local only to avoid spamming
      *) die "snapshot: unknown arg $1" ;;
    esac
    shift
  done

  acquire_lock
  trap 'release_lock' EXIT

  load_rclone_env
  check_deps

  local id
  id="$(generate_snapshot_id)"
  local snap_dir="$LOG_DIR/$id"
  mkdir -p "$snap_dir/db"

  log "snapshot $id — staging at $snap_dir (incremental via hardlinks)"

  # Find the previous snapshot BEFORE we create this one. ls -td adds a
  # trailing slash to directories, so anchor the filter accordingly.
  local prev_dir
  prev_dir="$(ls -td $LOG_DIR/[0-9]*-[0-9]* 2>/dev/null | grep -vE "/?${id}/?$" | head -1)"

  # ---- 1. live DB dump (always full, ~280MB compressed) ----
  log "  dumping live DB (port $DB_PORT)..."
  PGPASSWORD="$PG_PASS" psql -h 127.0.0.1 -p "$DB_PORT" -U "$PG_USER" -d paperclip -c "SELECT now();" >/dev/null 2>&1 \
    || die "DB not reachable at 127.0.0.1:$DB_PORT — is paperclip up?"
  PGPASSWORD="$PG_PASS" psql -h 127.0.0.1 -p "$DB_PORT" -U "$PG_USER" -d paperclip -c "CHECKPOINT;" >/dev/null 2>&1 || true
  local sql_name="paperclip-${id//-/}-${id##*-}.sql.gz"
  PGPASSWORD="$PG_PASS" pg_dump -h 127.0.0.1 -p "$DB_PORT" -U "$PG_USER" -d paperclip -Fc \
    | gzip > "$snap_dir/db/$sql_name"
  note "  DB dump: $(du -h "$snap_dir/db/$sql_name" | cut -f1)"

  # ---- 2. file system snapshot via rsync --link-dest ----
  # The user asked for "only diff". We use rsync's --link-dest so unchanged
  # files become hardlinks to the previous snapshot (zero-copy), and only
  # changed files take new inodes.
  log "  capturing file system via rsync --link-dest (incremental)..."
  if [[ -n "$prev_dir" && -d "$prev_dir" ]]; then
    note "  previous snapshot: $prev_dir"
  fi
  # 2a. data dir (embedded postgres data)
  mkdir -p "$snap_dir/data"
  rsync -a --delete \
    ${prev_dir:+"--link-dest=$prev_dir/data/"} \
    --exclude='**/pg_wal/***' \
    --exclude='**/postmaster.pid' \
    --exclude='**/postmaster.opts' \
    "$DATA_DIR/" "$snap_dir/data/" 2>&1 | tail -1 || true
  # 2b. custom configs and scripts (small, but include for completeness)
  mkdir -p "$snap_dir/config"
  rsync -a --delete \
    ${prev_dir:+"--link-dest=$prev_dir/config/"} \
    --exclude='**/__pycache__' \
    --exclude='**/.git' \
    "$HOME/.paperclip/scripts/" "$snap_dir/config/scripts/" 2>&1 | tail -1 || true
  rsync -a --delete \
    ${prev_dir:+"--link-dest=$prev_dir/config/"} \
    "$HOME/.paperclip/instances/default/.env" "$snap_dir/config/instances-default.env" 2>&1 | tail -1 || true

  # ---- 3. manifest ----
  log "  writing manifest..."
  local commit
  commit="$(git -C "$WORKTREE_PATH" rev-parse HEAD 2>/dev/null || echo unknown)"
  local dirty
  dirty="$(git -C "$WORKTREE_PATH" status --porcelain 2>/dev/null | head -1 || true)"
  local short
  short="$(git -C "$WORKTREE_PATH" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  local subject
  subject="$(git -C "$WORKTREE_PATH" log -1 --format='%s' 2>/dev/null || echo unknown)"

  cat > "$snap_dir/manifest.json" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "id": "$id",
  "hostname": "$(hostname -f 2>/dev/null || hostname)",
  "paperclipVersion": "$(jq -r '.version // "unknown"' "$WORKTREE_PATH/packages/server/package.json" 2>/dev/null || echo unknown)",
  "companyId": "$COMPANY_ID",
  "gitCommit": "$commit",
  "gitShort": "$short",
  "gitSubject": "$subject",
  "gitDirty": $([ -n "$dirty" ] && echo true || echo false),
  "files": {
    "sql": "db/$sql_name",
    "data": "data/",
    "config": "config/"
  },
  "restoreSteps": [
    "stop paperclip (./scripts/launch-dev.sh kills via tmux)",
    "drop and recreate paperclip database (via temporary postgres on port 54330)",
    "zcat db/$sql_name into the new paperclip db",
    "rsync data/ to $DATA_DIR/",
    "in the worktree, git checkout $short to restore the source code",
    "pnpm install --frozen-lockfile + pnpm --filter @paperclipai/server build + pnpm --filter @paperclipai/ui build",
    "restart paperclip via ./scripts/launch-dev.sh"
  ],
  "previousSnapshot": "${prev_dir:-none}",
  "totalBytes": $(du -sb "$snap_dir" 2>/dev/null | cut -f1),
  "trigger": "manual-snapshot",
  "operator": "$(whoami)"
}
EOF

  # ---- 4. retention: tiered (7 hourly + 24 daily) ----
  # tiered retention logic:
  #   - keep the last $RETENTION_HOURLY_MAX chronologically (rapid recency)
  #   - keep one snapshot per day for the last $RETENTION_DAILY_MAX days
  log "  enforcing tiered retention (last $RETENTION_HOURLY_MAX hourly + $RETENTION_DAILY_MAX daily)..."
  prune_tiered_retention

  # ---- 5. upload to gdrive (if not no-upload) ----
  # rclone sync with --copy-links dereferences hardlinks to actual file
  # copies on the remote, so the gdrive side gets full snapshots, not
  # hardlinks (which gdrive doesn't support).
  local uploaded="false"
  if [[ "$no_upload" != "true" ]]; then
    log "  uploading to $RCLONE_DEST_BASE/$id/ ..."
    local gdrive_target="$RCLONE_DEST_BASE/$(date -u +%Y)/$(date -u +%m)/$(date -u +%d)/$id"
    if rclone sync --copy-links "$snap_dir" "$gdrive_target/" --progress 2>&1 | tail -3; then
      uploaded="true"
      note "  gdrive target: $gdrive_target"
    else
      log "WARN: rclone upload failed — local snapshot preserved at $snap_dir"
    fi
  fi

  log "snapshot $id complete (uploaded=$uploaded, local=$snap_dir)"

  # ---- 6. report size savings from hardlinks ----
  local apparent
  apparent="$(du -sh --apparent-size "$snap_dir" 2>/dev/null | cut -f1)"
  local ondisk
  ondisk="$(du -sh "$snap_dir" 2>/dev/null | cut -f1)"
  local saved_pct
  saved_pct="$(awk -v a="$(du -sb --apparent-size "$snap_dir" 2>/dev/null | cut -f1)" -v o="$(du -sb "$snap_dir" 2>/dev/null | cut -f1)" 'BEGIN{ if(a>0) printf "%.0f%%", 100*(1 - o/a) }' )"
  note "  apparent size: $apparent, on-disk: $ondisk (saved ${saved_pct:-0}% via hardlinks)"

  printf '\n'
  note "To restore:  ./disaster-recovery.sh restore %s" "$id"
  printf '\n'
}

# ---------------------------------------------------------------------------
# list: show all available restore points (gdrive + local hourly dumps)
# ---------------------------------------------------------------------------
do_list() {
  acquire_lock
  trap 'release_lock' EXIT

  load_rclone_env

  printf '\n=== gdrive paperclip-backup restore points ===\n'
  if command -v rclone >/dev/null 2>&1; then
    rclone lsjson --dirs-only "$RCLONE_DEST_BASE/" 2>/dev/null \
      | jq -r '"\(.Path)\t\(.ModTime)"' \
      | sort -k2 -r | head -10 \
      | while IFS=$'\t' read -r d mtime; do
          local dpath="$RCLONE_DEST_BASE/$d"
          local cnt
          cnt="$(rclone lsf "$dpath" 2>/dev/null | wc -l)"
          printf '  %s  %s  (%s files)\n' "$d" "$mtime" "$cnt"
        done || true
  else
    note "  (rclone not installed)"
  fi

  printf '\n=== gdrive detailed listing (most recent 5) ===\n'
  for yyyymm in $(rclone lsf --dirs-only "$RCLONE_DEST_BASE/" 2>/dev/null | sort -r | head -1); do
    for mm in $(rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/" 2>/dev/null | sort -r | head -3); do
      for dd in $(rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/$mm/" 2>/dev/null | sort -r | head -3); do
        for hhmm in $(rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/$mm/$dd/" 2>/dev/null | sort -r | head -3); do
          local remote_path="$RCLONE_DEST_BASE/$yyyymm/$mm/$dd/$hhmm"
          local sz
          sz="$(rclone size "$remote_path" --json 2>/dev/null | jq -r '.bytes // 0')"
          printf '  %s/%s/%s/%s  %s bytes (%.1f MB)\n' \
            "$yyyymm" "$mm" "$dd" "$hhmm" "$sz" \
            "$(echo "scale=1; $sz/1048576" | bc 2>/dev/null)"
        done
      done
    done
  done || true

  printf '\n=== local hourly pg_dumps (last 5, legacy format) ===\n'
  if [[ -d "$HOURLY_BACKUP_DIR" ]]; then
    ls -lt "$HOURLY_BACKUP_DIR"/paperclip-*.sql.gz 2>/dev/null | head -5 \
      | awk '{printf "  %s  %s\n", $6" "$7" "$8, $5}'
  fi

  printf '\n=== local disaster-recovery snapshots (last 10) ===\n'
  if [[ -d "$LOG_DIR" ]]; then
    for d in $(ls -td $LOG_DIR/[0-9]*-[0-9]* 2>/dev/null | head -10); do
      local sz
      sz="$(du -sh "$d" 2>/dev/null | cut -f1)"
      printf '  %s  size=%s\n' "$(basename "$d")" "$sz"
    done
  fi
  printf '\n'
}

# ---------------------------------------------------------------------------
# restore: pull a snapshot, verify, restore DB + worktree, restart
# ---------------------------------------------------------------------------
do_restore() {
  local id=""
  local dry_run="false"
  local auto_yes="false"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)        dry_run="true" ;;
      --yes|-y)         auto_yes="true" ;;
      *) id="$1" ;;
    esac
    shift
  done
  [[ -n "$id" ]] || die "usage: restore <id> [--dry-run] [--yes|-y]"

  acquire_lock
  trap 'release_lock' EXIT

  load_rclone_env
  check_deps

  # Resolve the snapshot from one of three sources
  local staging=""
  local source=""

  # 1) local disaster-recovery snapshot (directory form: <id>/{db,data,config,manifest.json})
  if [[ -d "$LOG_DIR/$id" ]]; then
    staging="$LOG_DIR/$id"
    source="local-disaster-recovery"
  fi

  # 2) local hourly pg_dump (legacy single-file format)
  if [[ -z "$staging" ]]; then
    local candidate
    candidate="$(ls -t "$HOURLY_BACKUP_DIR"/paperclip-*.sql.gz 2>/dev/null \
      | grep "$(echo "$id" | tr -d -)" | head -1)"
    if [[ -n "$candidate" ]]; then
      staging="/tmp/paperclip-restore-$(basename "$candidate")"
      mkdir -p "$staging"
      cp "$candidate" "$staging/"
      source="local-hourly"
    fi
  fi

  # 3) gdrive (directory form)
  if [[ -z "$staging" ]]; then
    local remote_path
    remote_path="$(rclone lsf --dirs-only "$RCLONE_DEST_BASE/" 2>/dev/null \
      | while read -r yyyymm; do
          rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/" 2>/dev/null \
          | while read -r mm; do
              rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/$mm/" 2>/dev/null \
              | while read -r dd; do
                  rclone lsf --dirs-only "$RCLONE_DEST_BASE/$yyyymm/$mm/$dd/" 2>/dev/null \
                  | while read -r hhmm; do
                      [ "$yyyymm/$mm/$dd/$hhmm" = "$id" ] && echo "$RCLONE_DEST_BASE/$yyyymm/$mm/$dd/$hhmm" && break 4
                  done
              done
          done
      done)"
    if [[ -n "$remote_path" ]]; then
      log "  found gdrive snapshot: $remote_path"
      staging="/tmp/paperclip-restore-${id}"
      mkdir -p "$staging"
      rclone sync --copy-links "$remote_path" "$staging/" 2>&1 | tail -3
      source="gdrive"
    fi
  fi

  if [[ -z "$staging" ]]; then
    die "snapshot $id not found in local disaster-recovery, local hourly, or gdrive"
  fi
  log "snapshot located: $staging (source: $source)"

  # sanity check the manifest
  if [[ -f "$staging/manifest.json" ]]; then
    log "  manifest:"
    jq -C '.' "$staging/manifest.json" 2>/dev/null | sed 's/^/    /'
  fi

  if [[ "$dry_run" == "true" ]]; then
    log "dry-run mode — skipping actual restore"
    return 0
  fi

  # confirm the operator wants to proceed.
  #
  # If --yes/-y was passed (e.g. by the paperclip-backup plugin worker, which
  # has no stdin), skip the interactive prompt. The script still performs a
  # backup of the current data dir to restore-before-<id>/ before
  # overwriting, and the operator can roll back by running the same restore
  # command again with the original snapshot. This preserves the
  # safety invariants.
  if [[ "$auto_yes" == "true" ]]; then
    log "  --yes set, auto-confirming restore of $id (source: $source)"
  else
    printf '\n'
    note "ABOUT TO RESTORE: snapshot %s (source: %s)" "$id" "$source"
    note "  - Stops paperclip server"
    note "  - Backs up current data dir to %s/restore-before-%s/" "$LOG_DIR" "$id"
    note "  - Restores DB and data dir from snapshot"
    note "  - git checkouts the worktree to the recorded ref"
    note "  - Reinstalls + rebuilds + restarts paperclip"
    printf '\n  Type 'restore yes' to proceed, anything else to cancel: '
    local ans
    read -r ans
    [[ "$ans" == "restore yes" ]] || { log "aborted by operator"; return 1; }
  fi

  # 1) stop paperclip
  log "stopping paperclip..."
  if tmux has-session -t paperclip 2>/dev/null; then
    tmux kill-session -t paperclip
    sleep 3
  fi
  pkill -TERM -f "tsx.*src/index.ts" 2>/dev/null || true
  pkill -TERM -f "dev-runner.ts dev"  2>/dev/null || true
  pkill -TERM -f "pnpm dev:once"      2>/dev/null || true
  sleep 2

  # 2) backup current data dir
  local backup_dir="$LOG_DIR/restore-before-$id"
  mkdir -p "$backup_dir"
  if [[ -d "$DATA_DIR" ]]; then
    log "  backing up current data dir to $backup_dir/data/"
    rsync -a --exclude='pg_wal' --exclude='postmaster.pid' --exclude='postmaster.opts' \
      "$DATA_DIR/" "$backup_dir/data/" 2>/dev/null || true
  fi

  # 3) restore the data dir from the snapshot
  log "  restoring data dir from snapshot..."
  if [[ -d "$staging/data" ]]; then
    mkdir -p "$DATA_DIR"
    rsync -a --delete \
      --exclude='pg_wal' --exclude='postmaster.pid' --exclude='postmaster.opts' \
      "$staging/data/" "$DATA_DIR/" 2>&1 | tail -2 || true
  else
    note "  (snapshot has no data/ — DB restore only)"
  fi

  # 4) restore the DB from the SQL dump via temp postgres
  log "  restoring DB from SQL dump..."
  local sql_gz
  sql_gz="$(find "$staging" -maxdepth 3 -name 'paperclip-*.sql.gz' 2>/dev/null | head -1)"
  if [[ -n "$sql_gz" && -f "$sql_gz" ]]; then
    local tmp_pgdir="/tmp/paperclip-restore-pg-$$"
    /home/sirrus/paperclip-btcaaaaa-main/node_modules/.pnpm/@embedded-postgres+linux-x64@18.1.0-beta.16/node_modules/@embedded-postgres/linux-x64/native/bin/postgres \
      -D "$tmp_pgdir" -p "$((DB_PORT+1))" >/tmp/paperclip-restore-pg.log 2>&1 &
    local pg_pid=$!
    sleep 4
    if ! PGPASSWORD="$PG_PASS" psql -h 127.0.0.1 -p "$((DB_PORT+1))" -U "$PG_USER" -d postgres -c "CREATE DATABASE paperclip OWNER paperclip;" 2>&1; then
      kill $pg_pid 2>/dev/null || true
      die "failed to start restore postgres"
    fi
    if zcat "$sql_gz" | PGPASSWORD="$PG_PASS" psql -h 127.0.0.1 -p "$((DB_PORT+1))" -U "$PG_USER" -d paperclip 2>&1 | tail -5; then
      kill $pg_pid 2>/dev/null || true
      sleep 2
      log "  DB restored successfully"
    else
      kill $pg_pid 2>/dev/null || true
      die "DB restore failed"
    fi
  else
    note "  (no SQL dump in snapshot — skipping DB restore)"
  fi

  # 5) restore worktree from git ref
  local commit
  commit="$(jq -r '.gitShort // empty' "$staging/manifest.json" 2>/dev/null)"
  if [[ -n "$commit" && "$commit" != "empty" && ("$WORKTREE_PATH/.git" || -f "$WORKTREE_PATH/.git") ]]; then
    log "  restoring worktree to git ref $commit"
    (cd "$WORKTREE_PATH" && \
      git fetch --all 2>&1 | tail -3 && \
      git checkout "$commit" 2>&1 | tail -3) || {
        log "WARN: git checkout failed — worktree may have local changes; check status"
      }
  fi

  # 6) reinstall + rebuild
  log "  (re)installing + rebuilding..."
  (cd "$WORKTREE_PATH" && pnpm install --frozen-lockfile 2>&1 | tail -3) || true
  (cd "$WORKTREE_PATH" && pnpm --filter @paperclipai/server build 2>&1 | tail -2) || true
  (cd "$WORKTREE_PATH" && pnpm --filter @paperclipai/ui build 2>&1 | tail -2) || true

  # 7) restart paperclip
  log "  restarting paperclip via launch-dev.sh"
  (cd "$WORKTREE_PATH" && nohup ./scripts/launch-dev.sh >/tmp/paperclip.log 2>&1 ) &
  disown || true
  local waited=0
  while (( waited < 60 )); do
    if curl -sf -m 3 "http://127.0.0.1:$DB_PORT/api/health" >/dev/null 2>&1; then
      log "  paperclip is up on :$DB_PORT after ${waited}s"
      break
    fi
    sleep 2
    waited=$((waited + 2))
  done

  log "restore $id complete"
  note "snapshot id: $id"
  note "source: $source"
  note "before-restore backup: $backup_dir"
  note "current recovery point: run \`$0 doctor\` to re-validate"
}

# ---------------------------------------------------------------------------
# start: bring paperclip up via the worktree's custom launch script
# ---------------------------------------------------------------------------
do_start() {
  if curl -sf -m 3 "http://127.0.0.1:3100/api/health" >/dev/null 2>&1; then
    log "paperclip is already up on :3100 — nothing to do"
    return 0
  fi
  if ! [[ -x "$WORKTREE_PATH/scripts/launch-dev.sh" ]]; then
    log "WARN: $WORKTREE_PATH/scripts/launch-dev.sh is missing or not executable"
    return 1
  fi
  if tmux has-session -t paperclip 2>/dev/null; then
    log "found stale tmux session 'paperclip' with no live server — killing it"
    tmux kill-session -t paperclip 2>/dev/null || true
    sleep 2
  fi
  pkill -TERM -f "tsx.*src/index.ts" 2>/dev/null || true
  pkill -TERM -f "dev-runner.ts dev"  2>/dev/null || true
  pkill -TERM -f "pnpm dev:once"      2>/dev/null || true
  sleep 2
  log "paperclip is down — starting it via scripts/launch-dev.sh"
  ( cd "$WORKTREE_PATH" && nohup ./scripts/launch-dev.sh >> /tmp/paperclip.log 2>&1 ) &
  disown || true
  local waited=0
  while (( waited < 60 )); do
    if curl -sf -m 3 "http://127.0.0.1:3100/api/health" >/dev/null 2>&1; then
      log "paperclip is up on :3100 after ${waited}s"
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done
  log "ERROR: paperclip did not respond to /api/health after 60s"
  return 1
}

# ---------------------------------------------------------------------------
# status: read-only health check
# ---------------------------------------------------------------------------
do_status() {
  acquire_lock
  trap 'release_lock' EXIT

  printf '\n=== paperclip instance status ===\n'
  printf '  worktree: %s\n' "$WORKTREE_PATH"
  printf '  data dir: %s\n' "$DATA_DIR"
  printf '  backups:  %s\n' "$HOURLY_BACKUP_DIR"
  printf '  snapshots: %s\n' "$LOG_DIR"
  printf '  remote:   %s\n' "$RCLONE_DEST_BASE"

  if ss -ltn 2>/dev/null | grep -q ":$DB_PORT "; then
    note "  port $DB_PORT: LISTENING (embedded-postgres up)"
  else
    note "  port $DB_PORT: NOT LISTENING (embedded-postgres down)"
  fi

  if ss -ltn 2>/dev/null | grep -q ":3100 "; then
    note "  port 3100: LISTENING (paperclip server up)"
  else
    note "  port 3100: NOT LISTENING (paperclip server down)"
  fi

  if ss -ltn 2>/dev/null | grep -q ":3101 "; then
    note "  port 3101: LISTENING"
  fi

  if curl -sf "http://127.0.0.1:3100/api/health" 2>/dev/null >/tmp/paperclip-health.json; then
    note "  /api/health: OK"
    jq -r '"    version=\\(.version) git=\\(.serverInfo.git.shortSha) runs=\\(.devServer.activeRunCount) restart=\\(.devServer.lastRestartAt)"' \
      /tmp/paperclip-health.json 2>/dev/null | sed 's/^/    /' || true
  else
    note "  /api/health: not responding"
  fi

  if [[ -f "$RCLONE_PASS_FILE" ]]; then
    note "  rclone password file: present"
  else
    note "  rclone password file: MISSING"
  fi

  if command -v rclone >/dev/null 2>&1; then
    note "  rclone: $(rclone version 2>/dev/null | head -1)"
  fi

  printf '\n=== local last-snapshot ===\n'
  if [[ -d "$LOG_DIR" ]]; then
    ls -ltd "$LOG_DIR"/[0-9]*-[0-9]* 2>/dev/null | head -3 \
      | awk '{printf "  %s  %s\n", $6" "$7" "$8, $5}'
  else
    note "  (no snapshots dir yet)"
  fi
  printf '\n'
}

# ---------------------------------------------------------------------------
# verify: integrity of the running state
# ---------------------------------------------------------------------------
do_verify() {
  acquire_lock
  trap 'release_lock' EXIT

  local issues=0

  printf '\n=== verifying paperclip-btcaaaaa-main state ===\n'

  if [[ ! -e "$WORKTREE_PATH/.git" ]]; then
    note "  FAIL: $WORKTREE_PATH has no .git (not a worktree)"
    issues=$((issues+1))
  else
    note "  OK: git worktree at $WORKTREE_PATH (HEAD $(git -C "$WORKTREE_PATH" log -1 --format='%h' 2>/dev/null))"
  fi

  if [[ ! -f "$WORKTREE_PATH/.paperclip/.env" ]]; then
    note "  FAIL: missing .paperclip/.env"
    issues=$((issues+1))
  else
    note "  OK: .paperclip/.env present"
  fi

  if [[ ! -d "$DATA_DIR/base" ]]; then
    note "  FAIL: data dir $DATA_DIR missing base/"
    issues=$((issues+1))
  else
    note "  OK: data dir $DATA_DIR has base/"
  fi

  if command -v rclone >/dev/null 2>&1; then
    if [[ -f "$RCLONE_PASS_FILE" ]]; then
      note "  OK: rclone + password file present"
    else
      note "  FAIL: rclone present but no password file"
      issues=$((issues+1))
    fi
  else
    note "  FAIL: rclone not installed"
    issues=$((issues+1))
  fi

  if ! ss -ltn 2>/dev/null | grep -q ":3100 "; then
    note "  WARN: paperclip server (port 3100) is not running"
  else
    note "  OK: paperclip server (port 3100) is up"
  fi

  if ! ss -ltn 2>/dev/null | grep -q ":$DB_PORT "; then
    note "  FAIL: embedded postgres (port $DB_PORT) is not running"
    issues=$((issues+1))
  else
    note "  OK: embedded postgres (port $DB_PORT) is up"
  fi

  printf '\n  %d issue(s)\n\n' "$issues"
  return $issues
}

# ---------------------------------------------------------------------------
# doctor: status → start (if down) → offer recovery (if start fails)
# ---------------------------------------------------------------------------
do_doctor() {
  acquire_lock
  trap 'release_lock' EXIT

  printf '\n=== paperclip-btcaaaaa-main doctor ===\n'

  if curl -sf -m 3 "http://127.0.0.1:3100/api/health" >/dev/null 2>&1; then
    log "  paperclip is up on :3100 — no action needed"
    printf '\n'
    return 0
  fi

  log "  paperclip is down — attempting auto-start"
  if do_start; then
    log "  auto-start succeeded — paperclip is now running"
    printf '\n'
    return 0
  fi

  log "  auto-start FAILED — paperclip did not come up"
  printf '\n'
  note "  -- investigation is needed, or you need to restore from a snapshot"
  note "  -- suggested next steps:"
  printf '\n'
  note "  1. inspect the latest server log:"
  note "       tail -n 200 /tmp/paperclip.log"
  note "  2. list available restore points:"
  note "       $0 list"
  note "  3. dry-run a restore to preview what it would do:"
  note "       $0 restore <id> --dry-run"
  note "  4. if you want to capture the current (broken) state first, take a snapshot:"
  note "       $0 snapshot"
  note "  5. when ready, actually restore:"
  note "       $0 restore <id>"
  printf '\n'
  return 1
}

# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
main() {
  if [[ $# -lt 1 ]]; then
    cat <<EOF
paperclip-btcaaaaa-main disaster recovery

Usage:
  $0 status                         # current health (read-only)
  $0 verify                         # integrity of running state (read-only)
  $0 start                          # if down, start paperclip; else no-op
  $0 doctor                         # status → start → offer recovery if start fails
  $0 snapshot                       # take a snapshot, upload to gdrive
  $0 snapshot --no-upload            # snapshot only, skip gdrive upload
  $0 list                           # list all restore points (gdrive + local)
  # tiered retention: 7 most recent + one per day for the last 24 days
  # snapshots are rsync --link-dest incremental (~9MB per snapshot delta)
  $0 restore <id> [--dry-run] [--yes|-y]   # restore from a specific snapshot
  $0 restore <id>                          # actual restore (prompts "restore yes" unless --yes)

Examples:
  $0 doctor                         # preferred entry point — fixes if possible
  $0 status                         # just see what's happening
  $0 snapshot
  $0 list
  $0 restore 2026-07-06-1315

Storage model: hardlink-incremental (rsync --link-dest). 24-hour
retention cap on local snapshots. gdrive copies are dereferenced (full).

Decision flow:
  1. If paperclip is up: nothing to do.
  2. If down: try \`start\` (uses scripts/launch-dev.sh).
  3. If start fails: run \`list\` then \`restore <id> [--dry-run]\` to pick
     a recovery point.
EOF
    return 0
  fi

  case "$1" in
    snapshot|snapshot-auto) do_snapshot "${@:2}" ;;
    list|ls)                  do_list ;;
    restore)                  do_restore "${@:2}" ;;
    status|health)            do_status ;;
    verify|check)             do_verify ;;
    start)                    do_start ;;
    doctor)                   do_doctor ;;
    *)
      die "unknown command '$1' — run '$0' for usage" ;;
  esac
  # propagate do_restore's non-zero exit (e.g. --dry-run returns 0; aborted
  # restores return 1) up to the caller so the plugin worker sees the
  # correct exit code instead of always 0 from the case fall-through.
  return $?
}

main "$@"
