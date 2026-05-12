# Runbook: Database Migration

**Last updated:** 2026-05-12
**Owner:** DatabaseAdministrator
**Prerequisites:** `alembic` installed, database reachable, `.env` configured

---

## 1. Migration Lifecycle

```
Create → Review → Stage Apply → Production Apply → Verify
   ↑                                         |
   └──────────── Rollback ←──────────────────┘
```

---

## 2. Commands Quick Reference

```bash
# Activate environment first
source venv/bin/activate

# Create a new migration (autogenerate from model changes)
python scripts/manage_migrations.py create "Description of changes"

# Create an empty migration (manual SQL)
python scripts/manage_migrations.py create "Description" --no-autogenerate

# Apply all pending migrations
python scripts/manage_migrations.py upgrade

# Apply to a specific revision
python scripts/manage_migrations.py upgrade <revision_id>

# Rollback last migration (1 step)
python scripts/manage_migrations.py downgrade

# Rollback N steps
python scripts/manage_migrations.py downgrade 3

# Show current version
python scripts/manage_migrations.py current

# Show full history
python scripts/manage_migrations.py history
```

---

## 3. Safety Checklist

Before every migration apply:

- [ ] Backup taken: `python scripts/manage_backups.py create --compress`
- [ ] Target database confirmed: check `alembic current` first
- [ ] Migration reviewed: auto-generated SQL inspected for correctness
- [ ] Production window confirmed (if prod): no concurrent writers
- [ ] Rollback plan ready: migration downgrade is reversible

---

## 4. Create a Migration

```bash
# 1. Ensure your model changes are saved in src/optimizer_v3/database/models.py
# 2. Generate migration
python scripts/manage_migrations.py create "Add user preferences table"

# 3. Review the generated file in alembic/versions/
#    Check: upgrade() and downgrade() are both correct

# 4. If the autogenerate missed something:
python scripts/manage_migrations.py create "Manual fix" --no-autogenerate
# Then hand-edit the upgrade()/downgrade() functions
```

---

## 5. Apply Migrations

### Development / Staging

```bash
python scripts/manage_migrations.py upgrade
```

The script will:
- Load DB config from `src/optimizer_v3/database/config.py`
- Prompt for confirmation (`yes/no`)
- Run `alembic upgrade head`

### Production

```bash
# Step 1: Dry-run first (offline mode)
alembic upgrade head --sql 2>&1 | less

# Step 2: Verify current state
alembic current

# Step 3: Apply with confirmation
python scripts/manage_migrations.py upgrade
```

---

## 6. Rollback

```bash
# Rollback 1 step
python scripts/manage_migrations.py downgrade

# Rollback 3 steps
python scripts/manage_migrations.py downgrade 3

# Rollback to a specific revision
alembic downgrade <target_revision_id>

# Rollback all (DESTRUCTIVE — no recovery from here without restore)
alembic downgrade base
```

After rollback:
- Verify with `alembic current`
- Restore data if needed: `python scripts/manage_backups.py restore <file>`

---

## 7. Migration Version History

Current migration chain (14 revisions):

```
20260124_add_strategy_versioning.py       (base)
20260127_add_exit_conditions.py
20260129_enhance_test_results.py
20260131_add_validation_status.py
20260205_add_training_tables.py
20260215_add_strategy_type.py
20260509_add_ai_consultant_audit.py
20260509_add_ai_readonly_role.py
20260511_add_touch_index_tables.py
20260511_phase2_touch_index_deps.py
20260512_add_bug_files_source_col.py
20260512_add_bug_files_updated_at.py
20260512_add_fr_files_source_col.py
20260512_add_source_column_to_touch_index_tables.py  (head)
```

---

## 8. Failure Recovery

### Migration fails mid-apply

```bash
# 1. Don't panic — migration is in a transaction
# 2. Check the error message
# 3. Fix the issue (if possible)
# 4. Retry: 
python scripts/manage_migrations.py upgrade

# 5. If retry fails, rollback:
python scripts/manage_migrations.py downgrade 1
# Then fix the migration file and re-apply
```

### "Target database is not up to date" error

```bash
# Check what version the DB believes it is at
alembic current

# Compare with history
alembic history

# Resolve by upgrading to head or downgrading stale revisions
python scripts/manage_migrations.py upgrade
```

### Migration file has a bug

```bash
# 1. Fix the upgrade() function in the migration file
# 2. If already applied, downgrade first:
python scripts/manage_migrations.py downgrade 1
# 3. Fix the file
# 4. Re-apply:
python scripts/manage_migrations.py upgrade
```

---

## 9. Configuration Reference

Migration config is split across:

| File | Purpose |
|---|---|
| `alembic.ini` | Alembic runtime settings, template, logging |
| `alembic/env.py` | Database URL resolution, target metadata, online/offline mode |
| `src/optimizer_v3/database/config.py` | Programmatic DB config loader from `.env` |
| `src/optimizer_v3/database/models.py` | SQLAlchemy ORM models (source of truth for autogenerate) |

---

## 10. Related Documents

- [DATABASE_GUIDE.md](../architecture/DATABASE_GUIDE.md) — full schema, connection management, backup/restore
- [runbook-backup-restore.md](runbook-backup-restore.md) — backup/restore procedures
- [alembic/README](../alembic/README) — basic alembic usage
