# BACKUP — Offsite Backup Pipeline Operator Overview

**Owner:** PlatformEngineer
**Last Updated:** 2026-05-12
**Cadence:** Every 4 hours (database), continuous (sync to GDrive)

## Pipeline Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  Backup Routine     │ ──> │  GDrive Sync        │ ──> │  Google Drive   │
│  (manage_backups.py)│     │  (sync_backups_to..)│     │  Paperclip-     │
│  every 4h via cron  │     │  runs after backup  │     │  Backups/<env>/ │
└─────────────────────┘     └─────────────────────┘     └─────────────────┘
         │                                                        │
         ▼                                                        ▼
  ┌──────────────┐                                       Remote / DR site
  │  Local disk  │
  │  (backup dir)│
  └──────────────┘
```

The pipeline has three stages:

1. **Backup creation** — `manage_backups.py create` produces a compressed SQL dump to local disk
2. **Sync to GDrive** — `sync_backups_to_gdrive.py` pushes the local backup directory to Google Drive via rclone
3. **Retention enforcement** — old backups purged locally (configurable, default 30 days)

---

## Where Files Live

| Path | Purpose |
|------|---------|
| `scripts/manage_backups.py` | PostgreSQL backup/restore CLI |
| `scripts/sync_backups_to_gdrive.py` | Sync to Google Drive via rclone |
| `scripts/rclone_bootstrap.sh` | One-time OAuth setup for GDrive |
| `src/optimizer_v3/database/backup.py` | Backup engine (pg_dump wrapper) |
| `logs/backup_cron.log` | Backup cron output |
| `POSTGRES_BACKUP_PATH` (.env) | Local backup directory (e.g. `/home/sirrus/backups/optimizer_v3`) |
| `~/.config/rclone/rclone.conf` | rclone config with GDrive token |

---

## How to Manually Trigger a Backup

```bash
# Create a fresh backup
python scripts/manage_backups.py create --compress

# Then sync to GDrive
python scripts/sync_backups_to_gdrive.py

# Preview what would be synced (no transfer)
python scripts/sync_backups_to_gdrive.py --dry-run
```

## How to Inspect Google Drive Contents

```bash
# List backup files on GDrive
rclone ls btc_backup:btc-trade-engine-backups/

# Check total usage
rclone about btc_backup:

# List all remotes configured
rclone listremotes
```

The remote name is `btc_backup` by default (configurable via `RCLONE_REMOTE` env var).

## Retention Policy

| Tier | Retention | Enforcement |
|------|-----------|-------------|
| Local backups | 30 days | `manage_backups.py cleanup` (manual or cron) |
| Google Drive | Manual (no auto-delete) | Oversee via `rclone ls` |

Set retention via `.env`:

```ini
POSTGRES_BACKUP_RETENTION_DAYS=30
POSTGRES_BACKUP_COMPRESSION=true
POSTGRES_BACKUP_PATH=/home/sirrus/backups/optimizer_v3
```

GDrive does not have auto-cleanup. Periodically review and prune old backups using:

```bash
# List backups older than N days on GDrive
rclone lsl btc_backup:btc-trade-engine-backups/ | awk '$1 < ( systime() - 90*86400 )'

# Remove them (careful!)
rclone delete btc_backup:btc-trade-engine-backups/old_backup_file.sql.gz
```

---

## Dead Man's Switch

A dead-man's-switch monitor checks whether a backup was created within the expected window. If no recent backup is found, an alert fires.

### How It Works

- Expected to run every hour (via cron or systemd timer)
- Checks for any backup file newer than `interval + grace_period` (default: 4h + 1h = 5h)
- If no recent backup found: creates a Paperclip alert issue assigned to CTO (or configured alert target)

### Manual Test

```bash
# Simulate a missed backup (expect alert)
python scripts/backup_deadman_switch.py

# Force alert creation even if backup is recent
python scripts/backup_deadman_switch.py --force-alert
```

---

## Scheduled Cadence

The intended schedule (configure via crontab):

```bash
# Backup every 4 hours
0 */4 * * * cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/manage_backups.py create --compress >> logs/backup_cron.log 2>&1

# Sync to GDrive 15 min after backup
15 */4 * * * cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/sync_backups_to_gdrive.py >> logs/gdrive_sync.log 2>&1

# Dead-man's-switch check every hour
0 * * * * cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/backup_deadman_switch.py >> logs/deadman.log 2>&1

# Weekly local cleanup
0 3 * * 0 cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/manage_backups.py cleanup --yes >> logs/backup_cron.log 2>&1
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Create backup | `python scripts/manage_backups.py create --compress` |
| List local backups | `python scripts/manage_backups.py list` |
| Verify backup | `python scripts/manage_backups.py verify <file>` |
| Sync to GDrive | `python scripts/sync_backups_to_gdrive.py` |
| Dry-run GDrive sync | `python scripts/sync_backups_to_gdrive.py --dry-run` |
| List GDrive backup dir | `rclone ls btc_backup:btc-trade-engine-backups/` |
| Stats | `python scripts/manage_backups.py stats` |
| Cleanup old local backups | `python scripts/manage_backups.py cleanup` |
