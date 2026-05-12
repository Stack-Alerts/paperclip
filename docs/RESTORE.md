# RESTORE — Operator Restore Runbook

**Owner:** PlatformEngineer / DBA
**Audience:** On-call engineers (read this at 3am during a real incident)
**Last Updated:** 2026-05-12
**Drill reference:** `scripts/postgres_restore_drill.py` (BTCAAAAA-2080)

## Contents

1. [DB-Only Restore](#1-db-only-restore) — quickest path to recovery
2. [Full Restore from Scratch](#2-full-restore-from-scratch) — new machine or total loss
3. [Choosing a Backup](#3-choosing-a-backup)
4. [Post-Restore Verification](#4-post-restore-verification)
5. [Rollback a Migration](#5-rollback-a-migration)
6. [Emergency Commands Cheat Sheet](#6-emergency-commands-cheat-sheet)

---

## 1. DB-Only Restore

Use when: the database is corrupted or lost, but the application code is intact.

### Step 1: Pull the latest backup from GDrive

```bash
# List available backups on GDrive
rclone ls btc_backup:btc-trade-engine-backups/

# Pull the newest one
rclone copy btc_backup:btc-trade-engine-backups/optimizer_v3_20260512_020002.sql.gz /tmp/
```

### Step 2: Restore via CLI tool

```bash
# Check what you're about to restore
python scripts/manage_backups.py list

# Standard restore (requires confirmation)
python scripts/manage_backups.py restore /tmp/optimizer_v3_20260512_020002.sql.gz

# Emergency restore (skip confirmation, drop existing DB first)
python scripts/manage_backups.py restore /tmp/optimizer_v3_20260512_020002.sql.gz --drop --yes
```

### Step 3: Re-apply AI grants

Backups taken before migration `20260509_add_ai_readonly_role` may not include the correct grants:

```bash
python -c "
from src.optimizer_v3.database.backup import get_backup_manager
get_backup_manager().reapply_ai_grants()
"
```

### Step 4: Verify

```bash
python scripts/manage_migrations.py current
python -c "
from src.optimizer_v3.database.config import get_db_url
from sqlalchemy import create_engine, text
e = create_engine(get_db_url())
c = e.connect()
print('Strategies:', c.execute(text('SELECT count(*) FROM strategies')).scalar())
print('Alembic version:', c.execute(text('SELECT version_num FROM alembic_version')).scalar())
c.close()
"
```

---

## 2. Full Restore from Scratch

Use when: you have a brand-new machine or total environment loss.

### Prerequisites

- Python 3.11+, Poetry, PostgreSQL 12+
- Project cloned from git
- `.env` restored from secure backup (see Section 2.2)
- rclone configured with GDrive access

### Step 1: Restore .env

```bash
# Copy from secure backup (NOT from git — .env is in .gitignore)
cp /home/sirrus/backups/env/optimizer_v3.env.20260512 .env
chmod 600 .env
```

### Step 2: Restore PostgreSQL database

```bash
# List backups on GDrive
rclone ls btc_backup:btc-trade-engine-backups/

# Download the latest
rclone copy btc_backup:btc-trade-engine-backups/optimizer_v3_latest.sql.gz /tmp/

# Restore (drop + create + restore)
python scripts/manage_backups.py restore /tmp/optimizer_v3_latest.sql.gz --drop --yes

# Re-apply AI grants
python -c "
from src.optimizer_v3.database.backup import get_backup_manager
get_backup_manager().reapply_ai_grants()
"
```

### Step 3: Apply pending migrations

```bash
python scripts/manage_migrations.py upgrade
```

### Step 4: Verify

```bash
python scripts/manage_migrations.py current
python scripts/manage_backups.py list
```

---

## 3. Choosing a Backup

| Criterion | Pick |
|-----------|------|
| Latest data | Newest file by timestamp |
| Before a bad migration | Backup file dated before the migration was applied |
| Verify this DB | Drill or staging — use a copy of latest |

**Naming convention:** `optimizer_v3_YYYYMMDD_HHMMSS.sql.gz`

---

## 4. Post-Restore Verification

Always run this checklist after any restore:

```bash
# 1. Migration version
python scripts/manage_migrations.py current

# 2. Row counts match expected
python scripts/postgres_restore_drill.py
```
The drill script creates a throwaway database, restores, and compares row counts on
`strategies`, `strategy_versions`, and `strategy_test_results` tables plus the
`alembic_version`. Expected output:

```
OK  1. Create backup
OK  2. Verify backup integrity
OK  3. Validate SQL content
OK  4. Create drill database
OK  5. Restore backup
OK  6. Row count match: strategies         src=42 dst=42
OK  6. Row count match: strategy_versions  src=156 dst=156
OK  6. Row count match: strategy_test_results src=890 dst=890
OK  6. Verify data integrity
OK  7. Alembic version match               src=20260512_add_bug_files_source_col dst=20260512_add_bug_files_source_col
```

### 4.1 Manual Verification (if drill script unavailable)

```bash
for tbl in strategies strategy_versions strategy_test_results; do
  echo "$tbl: $(psql -h localhost -U optimizer_admin -d optimizer_v3 -tAc "SELECT count(*) FROM $tbl")"
done
echo "alembic: $(psql -h localhost -U optimizer_admin -d optimizer_v3 -tAc "SELECT version_num FROM alembic_version")"
```

---

## 5. Rollback a Migration

If a recent migration introduced a problem:

```bash
# Check current version
python scripts/manage_migrations.py current

# Rollback 1 step
python scripts/manage_migrations.py downgrade

# Rollback N steps
python scripts/manage_migrations.py downgrade 3
```

After rollback, verify the schema matches the backup you intend to restore.

---

## 6. Emergency Commands Cheat Sheet

```bash
# ── DB Restore ──────────────────────────────────────────────
# Restore with drop-create (DESTRUCTIVE — last resort)
python scripts/manage_backups.py restore <file> --drop --yes

# Manual restore via psql
gunzip -c <file> | psql -h localhost -U optimizer_admin -d optimizer_v3

# Manual restore with drop-create via psql
psql -h localhost -U optimizer_admin -d postgres -c "DROP DATABASE IF EXISTS optimizer_v3"
psql -h localhost -U optimizer_admin -d postgres -c "CREATE DATABASE optimizer_v3"
gunzip -c <file> | psql -h localhost -U optimizer_admin -d optimizer_v3

# ── GDrive ──────────────────────────────────────────────────
rclone ls btc_backup:btc-trade-engine-backups/
rclone copy btc_backup:btc-trade-engine-backups/<file> /tmp/

# ── Post-restore ────────────────────────────────────────────
python scripts/manage_migrations.py upgrade
python -c "from src.optimizer_v3.database.backup import get_backup_manager; get_backup_manager().reapply_ai_grants()"
python scripts/manage_migrations.py current

# ── Migration rollback ──────────────────────────────────────
python scripts/manage_migrations.py downgrade
python scripts/manage_migrations.py current
```
