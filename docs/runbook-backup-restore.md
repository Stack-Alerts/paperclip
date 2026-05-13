# Runbook: Backup & Restore

**Owner:** PlatformEngineer / DocWriter
**Audience:** Platform Engineers, Operations, On-call responders
**Last Updated:** 2026-05-12

## Overview

This runbook covers backup and restore procedures for all persistent data in the BTC Trade Engine. The system has three data tiers:

| Tier | Data | Retention |
|------|------|-----------|
| **PostgreSQL** | Strategies, backtest results, optimization runs, AI recommendations, validation reports, signal metrics, trade history | 30 days (configurable) |
| **Configuration** | `.env` (credentials), `lock_gate_exceptions.json`, `.module_lock_registry.json` | Version-controlled in git |
| **Application State** | Optimizer cache, training data, Lake API cache, test results | Managed by application |

---

## 1. Database Backup

### 1.1 Prerequisites

- PostgreSQL 12+ running and accessible
- `pg_dump` and `psql` installed (part of `postgresql-client` package)
- `.env` file configured with `POSTGRES_*` variables
- Backup directory exists (configurable via `POSTGRES_BACKUP_PATH`)

### 1.2 Create a Backup

```bash
# Default backup (timestamped, compressed per .env config)
python scripts/manage_backups.py create

# Named backup with compression
python scripts/manage_backups.py create --name pre_migration_20260512 --compress

# Uncompressed backup (useful for inspection/diffing)
python scripts/manage_backups.py create --name debug_snapshot
```

The backup target is configured via `.env`:

```ini
POSTGRES_BACKUP_PATH=/home/sirrus/backups/optimizer_v3
POSTGRES_BACKUP_RETENTION_DAYS=30
POSTGRES_BACKUP_COMPRESSION=true
```

Backup files are named `optimizer_v3_YYYYMMDD_HHMMSS.sql` or `optimizer_v3_YYYYMMDD_HHMMSS.sql.gz`.

### 1.3 List Available Backups

```bash
python scripts/manage_backups.py list
```

### 1.4 Verify Backup Integrity

```bash
python scripts/manage_backups.py verify /path/to/backup.sql.gz
```

### 1.5 Backup Statistics

```bash
python scripts/manage_backups.py stats
```

Shows total backups, total size, compression ratio, oldest/newest, and retention policy.

### 1.6 Cleanup Old Backups

```bash
# Uses retention days from .env (default: 30)
python scripts/manage_backups.py cleanup

# Custom retention with auto-confirm
python scripts/manage_backups.py cleanup --retention 7 --yes
```

**Note:** Cleanup uses file creation time (`ctime`), not modification time. This means a file copied or moved will keep its original creation date.

### 1.7 Scheduled Backups (Cron)

Add to crontab for nightly backups:

```bash
# Nightly at 2 AM
0 2 * * * cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/manage_backups.py create --compress >> logs/backup_cron.log 2>&1

# Weekly cleanup
0 3 * * 0 cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip && venv/bin/python scripts/manage_backups.py cleanup --yes >> logs/backup_cron.log 2>&1
```

---

## 2. Database Restore

### 2.1 Standard Restore

```bash
# Restore with confirmation prompt
python scripts/manage_backups.py restore /path/to/backup.sql.gz

# Restore with drop-create + auto-confirm (for full disaster recovery)
python scripts/manage_backups.py restore /path/to/backup.sql.gz --drop --yes
```

### 2.2 What Happens During Restore

1. **Without `--drop`:** The backup is restored over the existing database. Tables are replaced but the database itself is not recreated. This is safe for minor rollbacks.
2. **With `--drop`:** Drops the existing database, creates a fresh database, then restores from backup.

### 2.3 Post-Restore: Re-apply AI Grants

After any restore, verify AI consultant roles have correct privileges:

```bash
python -c "
from src.optimizer_v3.database.backup import get_backup_manager
get_backup_manager().reapply_ai_grants()
"
```

This is necessary because some backups predate the `--no-acl` pg_dump fix, and Alembic skips already-recorded grant migrations.

### 2.4 Verify Restore

```bash
# Check migration version
python scripts/manage_migrations.py current

# Verify strategies exist
python -c "
from src.optimizer_v3.database.config import get_db_url
from sqlalchemy import create_engine, text
engine = create_engine(get_db_url())
with engine.connect() as conn:
    result = conn.execute(text('SELECT count(*) FROM strategies'))
    print(f'Strategies: {result.scalar()}')
"
```

### 2.5 Emergency Restore (Manual)

If `manage_backups.py` is unavailable:

```bash
# Compressed backup
gunzip -c /path/to/backup.sql.gz | psql -h localhost -U optimizer_admin -d optimizer_v3

# Uncompressed backup
psql -h localhost -U optimizer_admin -d optimizer_v3 -f /path/to/backup.sql

# With drop-create
psql -h localhost -U optimizer_admin -d postgres -c "DROP DATABASE IF EXISTS optimizer_v3"
psql -h localhost -U optimizer_admin -d postgres -c "CREATE DATABASE optimizer_v3"
gunzip -c /path/to/backup.sql.gz | psql -h localhost -U optimizer_admin -d optimizer_v3
```

---

## 3. Configuration Backup

### 3.1 What to Back Up

| File | Location | Method |
|------|----------|--------|
| Environment secrets | `.env` | Manual secure backup (NOT git) |
| Lock gate exceptions | `lock_gate_exceptions.json` | Git (tracked) |
| Module lock registry | `.module_lock_registry.json` | Git (tracked) |
| Alembic migrations | `alembic/versions/` | Git (tracked) |
| User strategies | `user_strategies/` | Git or manual |

### 3.2 .env Backup Procedure

The `.env` file contains credentials and **MUST NEVER** be committed to git.

```bash
# Backup .env to secure location
cp .env /home/sirrus/backups/env/optimizer_v3.env.$(date +%Y%m%d)
chmod 600 /home/sirrus/backups/env/optimizer_v3.env.$(date +%Y%m%d)

# Restore
cp /home/sirrus/backups/env/optimizer_v3.env.20260512 .env
```

### 3.3 Git-Tracked Configuration

Restored via normal `git checkout`:

- `lock_gate_exceptions.json`
- `.module_lock_registry.json`
- `alembic/versions/*.py`
- `alembic.ini`

---

## 4. Disaster Recovery Procedures

### 4.1 Full Recovery from Scratch

```bash
# 1. Restore .env from secure backup
cp /home/sirrus/backups/env/optimizer_v3.env.20260512 .env

# 2. Restore database
python scripts/manage_backups.py restore /home/sirrus/backups/optimizer_v3/newest.sql.gz --drop --yes

# 3. Re-apply AI grants
python -c "
from src.optimizer_v3.database.backup import get_backup_manager
get_backup_manager().reapply_ai_grants()
"

# 4. Apply any pending migrations
python scripts/manage_migrations.py upgrade

# 5. Verify
python scripts/manage_migrations.py current
python scripts/manage_backups.py stats
```

### 4.2 Recovery Checklist

- [ ] `.env` restored from secure backup
- [ ] PostgreSQL running and accessible
- [ ] Database restored from backup
- [ ] AI grants reapplied
- [ ] Migrations at correct revision
- [ ] Lock gate exceptions and module registry restored from git
- [ ] Application starts and connects to DB
- [ ] Smoke test: list strategies, run a backtest

---

## 5. Database Migration Management

### 5.1 Create a Migration

```bash
python scripts/manage_migrations.py create "Description of changes"
```

### 5.2 Apply Migrations

```bash
python scripts/manage_migrations.py upgrade
```

### 5.3 Rollback Migrations

```bash
# Rollback 1 step
python scripts/manage_migrations.py downgrade

# Rollback 3 steps
python scripts/manage_migrations.py downgrade 3
```

### 5.4 Check Migration State

```bash
python scripts/manage_migrations.py current
python scripts/manage_migrations.py history
```

---

## Appendix A: Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_BACKUP_PATH` | `/tmp/optimizer_v3_backups` | Backup storage directory |
| `POSTGRES_BACKUP_RETENTION_DAYS` | `30` | Days to retain backups |
| `POSTGRES_BACKUP_COMPRESSION` | `true` | Enable gzip compression |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `optimizer_v3` | Database name |
| `POSTGRES_USER` | `optimizer_admin` | Database user |
| `POSTGRES_PASSWORD` | *(required)* | Database password |

## Appendix B: Quick Reference

| Action | Command |
|--------|---------|
| Create backup | `python scripts/manage_backups.py create` |
| List backups | `python scripts/manage_backups.py list` |
| Restore | `python scripts/manage_backups.py restore <file> --drop --yes` |
| Verify | `python scripts/manage_backups.py verify <file>` |
| Cleanup | `python scripts/manage_backups.py cleanup` |
| Stats | `python scripts/manage_backups.py stats` |
| Apply migrations | `python scripts/manage_migrations.py upgrade` |
| Re-apply AI grants | `python -c "from src.optimizer_v3.database.backup import get_backup_manager; get_backup_manager().reapply_ai_grants()"` |

---

## 6. Offsite Backup Pipeline (Paperclip Instance → Google Drive)

**Owner:** AutomationEngineer
**Scripts:** `~/.paperclip/scripts/backup-to-drive.sh` (main)
**Monitor:** `.github/workflows/backup-deadman-switch.yml` (runs every 30 min)
**State file:** `~/.paperclip/instances/default/backup-state/last-success.json`

### 6.1 Overview

The `backup-to-drive.sh` script bundles the latest Paperclip database dump
with instance data (companies, projects, skills, storage) and uploads the
payload to Google Drive via rclone.

- **Source:** `~/.paperclip/instances/default/data/backups/` (freshest DB dump)
- **Destination:** `gdrive:Paperclip-Backups/<companyId>/YYYY/MM/DD/HHMM/`
- **Includes:** DB dump, sanitized config.json, companies/, projects/, skills/, storage/
- **Manifest:** `MANIFEST.json` with SHA-256 checksum and payload size

### 6.2 Scheduling

The backup runs every 4 hours via a user-level systemd timer.

```bash
# Check timer status
systemctl --user status paperclip-backup.timer

# View next trigger
systemctl --user list-timers paperclip-backup.timer

# Trigger a backup immediately
systemctl --user start paperclip-backup.service

# View logs
journalctl --user -u paperclip-backup.service -f

# Service/timer definitions
ls ~/.config/systemd/user/paperclip-backup.{service,timer}
```

**Timer schedule:** `00:00, 04:00, 08:00, 12:00, 16:00, 20:00` (UTC-based via systemd `OnCalendar`, randomized by up to 10 min)

### 6.3 rclone Configuration

The `gdrive` rclone remote must be configured with OAuth tokens.

```bash
# Check if gdrive remote is configured
rclone listremotes | grep gdrive

# Verify remote works
rclone lsd gdrive:Paperclip-Backups
```

#### 6.3.1 Headless OAuth Setup

This server has no display. Use the headless auth helper:

```bash
# On a machine WITH a browser (your laptop):
rclone authorize "drive" "drive.file" --auth-no-open-browser
# → Open URL → authorize Google → paste verification code → copy JSON token block

# On THIS server:
~/.paperclip/scripts/rclone-headless-auth.sh --apply-token
# → Paste the JSON token block → press Ctrl+D
```

Or use SSH forwarding:

```bash
# On your laptop:
ssh -L 53682:127.0.0.1:53682 sirrus-serv

# On the server:
rclone config reconnect gdrive:
# → Open URL — callback forwarded to server
```

#### 6.3.2 Bootstrap (interactive, needs display)

```bash
~/.paperclip/scripts/rclone-bootstrap.sh
```

### 6.4 Manual Backup

```bash
# Run a full backup (DB dump + instance data → GDrive)
~/.paperclip/scripts/backup-to-drive.sh
```

### 6.5 Restore from Google Drive

```bash
# List available backups
~/.paperclip/scripts/restore-from-drive.sh list

# Restore most recent backup
~/.paperclip/scripts/restore-from-drive.sh latest /tmp/restore

# Restore specific backup
~/.paperclip/scripts/restore-from-drive.sh 2026/05/13/0152 /tmp/restore
```

### 6.6 Dead-Man Switch

The dead-man switch monitors backup liveness:

- **Workflow:** `.github/workflows/backup-deadman-switch.yml`
- **Interval:** Every 30 min
- **Threshold:** 4h (backup interval) + 8h (grace) = 12h since last success
- **Action:** Creates a critical Paperclip issue assigned to CTO if backup is overdue
- **State file:** `~/.paperclip/instances/default/backup-state/last-success.json`
- **Self-health state:** `~/.paperclip/backup_deadman_switch_state.json` (tracks total runs, last run, last alert)
- **Log file:** `~/.paperclip/backup_deadman_switch.log` (auto-rotated at 1 MB)
- **CI step summary:** Workflow writes a step summary with backup age, threshold, and self-health metrics

Manual dead-man check:

```bash
python scripts/backup_deadman_switch.py
python scripts/backup_deadman_switch.py --dry-run
python scripts/backup_deadman_switch.py --grace 6
python scripts/backup_deadman_switch.py --json-summary    # JSON output for CI
```

#### 6.6.1 Log Rotation

The dead-man switch log (`~/.paperclip/backup_deadman_switch.log`) auto-rotates
when it exceeds 1 MB. The old log is preserved as
`~/.paperclip/backup_deadman_switch.log.1`.

#### 6.6.2 Self-Health State

The state file `~/.paperclip/backup_deadman_switch_state.json` tracks:

```json
{
  "total_runs": 42,
  "last_run_utc": "2026-05-13T20:00:00+00:00",
  "last_alert_utc": "2026-05-10T04:30:00+00:00"
}
```

#### 6.6.3 Tests

```bash
pytest tests/test_scripts/test_backup_deadman_switch.py -v
pytest tests/bug_regression/test_btcaaaaa_25851_regression.py -v
```

#### 6.6.4 Dead-Man Switch Monitor (Watchdog on the Watchdog)

The dead-man switch monitor watches the backup dead-man's-switch itself.
It runs on GitHub-hosted runners (`ubuntu-latest`) to avoid being affected
by the same self-hosted runner failures it monitors.

- **Workflow:** `.github/workflows/deadman-switch-monitor.yml`
- **Interval:** Every 30 min (at :15 and :45, offset from the dead-man switch)
- **Threshold:** 45 min since last successful dead-man-switch run
- **Runner:** `ubuntu-latest` (GitHub-hosted, **not** self-hosted)
- **Action:** Creates a critical Paperclip issue if the dead-man's-switch has no successful runs within the threshold
- **State file:** `~/.paperclip/deadman_switch_monitor_state.json`
- **Log file:** `~/.paperclip/deadman_switch_monitor.log` (auto-rotated at 1 MB)

Manual monitor check:

```bash
python scripts/deadman_switch_monitor.py
python scripts/deadman_switch_monitor.py --dry-run
python scripts/deadman_switch_monitor.py --threshold 30
python scripts/deadman_switch_monitor.py --json-summary
```

Tests:

```bash
pytest tests/test_scripts/test_deadman_switch_monitor.py -v
```


### 6.7 Troubleshooting

| Symptom | Check |
|---------|-------|
| Backup fails at rclone step | `rclone lsd gdrive:` — token may be expired. Run `rclone-headless-auth.sh --apply-token` |
| No DB dumps found | `ls ~/.paperclip/instances/default/data/backups/` — Paperclip embedded PG may not be producing dumps |
| Timer not firing | `systemctl --user status paperclip-backup.timer` — check linger: `loginctl show-user sirrus --property=Linger` |
| Dead-man alert fired | Backup overdue >12h. Run manual backup, then check dead-man log: `~/.paperclip/backup_deadman_switch.log` |
| Dead-man log rotated unexpectedly | Check `~/.paperclip/backup_deadman_switch.log.1` for the rotated content |
| Dead-man self-health shows old last_run_utc | The GH Actions workflow may have stopped. Check `~/.paperclip/backup_deadman_switch_state.json` and verify the CI schedule is active |
| Dead-man switch monitor alert fired | The dead-man's-switch itself is not running. Check GitHub Actions for `backup-deadman-switch.yml` run history. The self-hosted runner may be down. Check monitor log: `~/.paperclip/deadman_switch_monitor.log` |
| Service fails with "status=216/GROUP" | Remove any `User=` directive from the service unit — it's redundant in `systemctl --user` and causes GROUP permission errors. Also ensure `WantedBy=default.target` (not `multi-user.target`) for user units. |
| Timer not firing despite being enabled | Run `loginctl show-user sirrus --property=Linger` — must be `yes`. If `no`: `sudo loginctl enable-linger sirrus`. |
| | Lock held (flock) | Stale lock file: `rm /tmp/paperclip-backup.lock` |
