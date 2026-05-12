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
