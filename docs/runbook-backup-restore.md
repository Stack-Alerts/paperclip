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
| Check rclone auth | `~/.paperclip/scripts/rclone-headless-auth.sh --check` |
| Apply rclone token (headless) | `~/.paperclip/scripts/rclone-headless-auth.sh --apply-token` |
| Full backup pipeline health | `~/.paperclip/scripts/backup-health-check.sh` |

---

## 6. Offsite Backup Pipeline (Paperclip Instance → Google Drive)

**Owner:** AutomationEngineer
**Scripts:** `~/.paperclip/scripts/backup-to-drive.sh` (main)
**Monitor:** `deploy/systemd/paperclip-backup-deadman-switch.{service,timer}` (systemd timer, every 30 min)
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
SCOPE_BLOB=$(echo -n '{"scope":"drive"}' | base64 -w0 | sed 's/=//g')
rclone authorize "drive" "${SCOPE_BLOB}" --auth-no-open-browser
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

- **Systemd service:** `deploy/systemd/paperclip-backup-deadman-switch.service`
- **Systemd timer:** `deploy/systemd/paperclip-backup-deadman-switch.timer`
- **Interval:** Every 30 min
- **Threshold:** 4h (backup interval) + 8h (grace) = 12h since last success
- **Action:** Creates a critical Paperclip issue assigned to CTO if backup is overdue
- **State file:** `~/.paperclip/instances/default/backup-state/last-success.json`
- **Self-health state:** `~/.paperclip/backup_deadman_switch_state.json` (tracks total runs, last run, last alert)
- **Log file:** `~/.paperclip/backup_deadman_switch.log` (auto-rotated at 1 MB)
- **Install:** `deploy/systemd/install-backup-deadman-switch.sh`
- **Journal:** `journalctl --user -u paperclip-backup-deadman-switch.service -n 20`

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

- **Systemd service:** `deploy/systemd/paperclip-backup-deadman-monitor.service`
- **Systemd timer:** `deploy/systemd/paperclip-backup-deadman-monitor.timer`
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



#### 6.6.5 Dead-Man Switch Local Backup Monitor (systemd-based fallback)

The local backup monitor runs on the self-hosted machine via systemd timer.
It checks the dead-man switch state file directly, providing redundancy when
GitHub Actions API is unavailable.  It complements the GH Actions-based
deadman-switch-monitor.yml.

- **Timer:** `deploy/systemd/paperclip-deadman-monitor.timer`
- **Service:** `deploy/systemd/paperclip-deadman-monitor.service`
- **Interval:** Every 15 min (at :05, :20, :35, :50 — offset from the GH Actions monitor at :15/:45)
- **Threshold:** 45 min since the dead-man switch last ran (via `last_run_utc` in state file)
- **Runner:** self-hosted machine (direct filesystem access to state file)
- **Action:** Creates a critical Paperclip issue if the dead-man's-switch state is stale or missing
- **State file:** `~/.paperclip/deadman_switch_local_monitor_state.json`
- **Log file:** `~/.paperclip/deadman_switch_local_monitor.log` (auto-rotated at 1 MB)
- **Alert query:** "Dead-man's-switch local monitor alert" (distinct from the GH Actions monitor's alerts)

Manual check:

```bash
python scripts/deadman_switch_local_monitor.py
python scripts/deadman_switch_local_monitor.py --dry-run
python scripts/deadman_switch_local_monitor.py --threshold 30
python scripts/deadman_switch_local_monitor.py --json-summary
```

Enable the timer:

```bash
# Install units
mkdir -p ~/.config/systemd/user/
cp deploy/systemd/paperclip-deadman-monitor.service ~/.config/systemd/user/
cp deploy/systemd/paperclip-deadman-monitor.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now paperclip-deadman-monitor.timer
systemctl --user status paperclip-deadman-monitor.timer
```

Tests:

```bash
pytest tests/test_scripts/test_deadman_switch_local_monitor.py -v
```

#### 6.6.6 Backup Dead-Man's-Switch Monitor (Layer 3 — watchdog for the watchdog)

The backup dead-man's-switch monitor watches the deadman-switch-monitor
(the ubuntu-latest monitor from §6.6.4).  It closes the monitoring loop:
if the ubuntu-latest-based deadman-switch-monitor stops reporting, this
backup monitor detects the gap and alerts.

Runs in two redundant forms, both on the self-hosted machine:

| Form | Trigger | Offsets |
|------|---------|---------|
| Systemd timer | every 30 min | :08, :38 |
| GH Actions workflow | every 30 min | :12, :42 |

The :08/:38 (systemd) and :12/:42 (GH Actions) offsets are 4 min apart so
the two forms never collide and provide redundancy if one scheduler fails.

The monitor uses a dual-source liveness check:

1. **Primary:** ``gh run list`` against ``deadman-switch-monitor.yml``
   (queries the GH Actions API for recent successful runs).
2. **Fallback:** reads ``deadman_switch_monitor_state.json`` from the
   deadman-switch-monitor's own state file (if available on the
   self-hosted machine).

- **Systemd service:** ``deploy/systemd/paperclip-backup-deadman-monitor.service``
- **Systemd timer:** ``deploy/systemd/paperclip-backup-deadman-monitor.timer``
- **GH Actions workflow:** ``.github/workflows/backup-deadman-switch-monitor.yml``
- **Interval:** 30 min (expected deadman-switch-monitor runs at :15/:45)
- **Threshold:** 60 min since last successful deadman-switch-monitor run
- **Runner:** self-hosted machine
- **Action:** Creates a critical Paperclip issue assigned to CTO if the
  deadman-switch-monitor has no successful runs within the threshold
- **State file:** ``~/.paperclip/backup_deadman_switch_monitor_state.json``
- **Log file:** ``~/.paperclip/backup_deadman_switch_monitor.log`` (auto-rotated at 1 MB)
- **Alert query:** "Backup dead-man's-switch monitor alert"

Manual check:

```bash
python scripts/backup_deadman_switch_monitor.py
python scripts/backup_deadman_switch_monitor.py --dry-run
python scripts/backup_deadman_switch_monitor.py --threshold 30
python scripts/backup_deadman_switch_monitor.py --json-summary
```

Enable the timer:

```bash
deploy/systemd/install-backup-deadman-monitor.sh
```

Or manually:

```bash
mkdir -p ~/.config/systemd/user/
cp deploy/systemd/paperclip-backup-deadman-monitor.service ~/.config/systemd/user/
cp deploy/systemd/paperclip-backup-deadman-monitor.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now paperclip-backup-deadman-monitor.timer
systemctl --user status paperclip-backup-deadman-monitor.timer
```

Tests:

```bash
pytest tests/test_scripts/test_backup_deadman_switch_monitor.py -v
```

### 6.7 Troubleshooting

| Symptom | Check |
|---------|-------|
| Backup fails at rclone step | 1. Check auth: `~/.paperclip/scripts/rclone-headless-auth.sh --check`<br>2. If unauthenticated: `~/.paperclip/scripts/rclone-headless-auth.sh --apply-token` (paste token from `rclone authorize` on browser machine)<br>3. If "empty token found": the OAuth token was cleared — same fix as above<br>4. Comprehensive pipeline health: `~/.paperclip/scripts/backup-health-check.sh` |
| No DB dumps found | `ls ~/.paperclip/instances/default/data/backups/` — Paperclip embedded PG may not be producing dumps |
| Timer not firing | `systemctl --user status paperclip-backup.timer` — check linger: `loginctl show-user sirrus --property=Linger` |
| Dead-man alert fired | Backup overdue >12h. Run manual backup, then check dead-man log: `~/.paperclip/backup_deadman_switch.log` |
| Dead-man log rotated unexpectedly | Check `~/.paperclip/backup_deadman_switch.log.1` for the rotated content |
| Dead-man self-health shows old last_run_utc | The systemd timer may have stopped. Check `systemctl --user status paperclip-backup-deadman-switch.timer`. Verify `~/.paperclip/backup_deadman_switch_state.json` has recent `last_run_utc`. Check linger: `loginctl show-user sirrus --property=Linger` |
| Dead-man switch local monitor alert fired | The dead-man switch state file is stale or missing. Check `~/.paperclip/backup_deadman_switch_state.json` for `last_run_utc`. Check monitor log: `~/.paperclip/deadman_switch_local_monitor.log`. The local monitor runs via systemd: `systemctl --user status paperclip-deadman-monitor.timer` |
| Dead-man switch monitor alert fired | The dead-man's-switch itself is not running. Check systemd timer: `systemctl --user status paperclip-backup-deadman-switch.timer`. Check journal: `journalctl --user -u paperclip-backup-deadman-switch.service -n 20`. The systemd user session may have stopped. Verify linger: `loginctl show-user sirrus --property=Linger`. Check monitor log: `~/.paperclip/deadman_switch_monitor.log` |
| Backup dead-man-switch monitor alert fired | The deadman-switch-monitor (ubuntu-latest) is stalled or failing. Check workflow runs: `gh run list --repo Stack-Alerts/BTC-Trade-Engine-PaperClip --workflow deadman-switch-monitor.yml --limit 5`. Check backup monitor log: `~/.paperclip/backup_deadman_switch_monitor.log`. Check systemd timer: `systemctl --user status paperclip-backup-deadman-monitor.timer` |
| Service fails with "status=216/GROUP" | Remove any `User=` directive from the service unit — it's redundant in `systemctl --user` and causes GROUP permission errors. Also ensure `WantedBy=default.target` (not `multi-user.target`) for user units. |
| Timer not firing despite being enabled | Run `loginctl show-user sirrus --property=Linger` — must be `yes`. If `no`: `sudo loginctl enable-linger sirrus`. |
| | Lock held (flock) | Stale lock file: `rm /tmp/paperclip-backup.lock` |
