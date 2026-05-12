# Runbook: Deployment

**Last updated:** 2026-05-12
**Owner:** CTO / RepoSteward

---

## 1. Overview

Deployment follows a standard CI → merge → verify flow. There is no separate deployment environment beyond `main` branch — code deploys by merging to `main` and passing all gates.

### Deployment Flow

```
Developer branch → PR → CI (lint + test + lock gate) → Merge to main → Main CI → Deployed
```

---

## 2. Pre-Deployment Checklist

Before merging to main:

- [ ] PR has ≥1 approving review (branch protection enforced)
- [ ] Lint workflow passes (no T201 print statements, no DTZ003 naive datetime)
- [ ] Test workflow passes (pytest + coverage gate ≥20%)
- [ ] Lock gate passes (no unauthorized locked module changes)
- [ ] Freeze-lift evidence tests pass
- [ ] Migration created (if schema changes) — `python scripts/manage_migrations.py create "desc"`
- [ ] Migration tested on dev DB — `python scripts/manage_migrations.py upgrade`
- [ ] Backup taken before prod migration — `python scripts/manage_backups.py create --compress`
- [ ] CHANGELOG or relevant doc updated

---

## 3. Deployment Steps

### 3.1 Standard Deployment (no migration)

```bash
# 1. Merge PR to main (via GitHub UI or API)
# 2. CI auto-runs on push to main
# 3. Verify:
gh run list --branch main --limit 5 --json name,conclusion,status
```

### 3.2 Deployment with Database Migration

```bash
# 1. Backup current state
python scripts/manage_backups.py create --compress

# 2. Review the migration SQL
alembic upgrade head --sql 2>&1 | less

# 3. Apply migration to production DB
python scripts/manage_migrations.py upgrade

# 4. Verify migration
alembic current

# 5. Merge code PR to main
```

### 3.3 Hotfix / Emergency Deployment

```bash
# 1. Branch from main
git checkout main
git checkout -b hotfix/issue-description

# 2. Fix, commit, push
git add <files>
git commit -m "fix: description"
git push -u origin hotfix/issue-description

# 3. Create PR (bypass review only with CTO approval)
# 4. Merge once CI passes
```

---

## 4. Rollback

### 4.1 Code Rollback

```bash
# Identify the commit to revert to
git log --oneline -10

# Revert the last merge commit
git revert HEAD
git push origin main
```

### 4.2 Database Rollback

```bash
# Rollback migration
python scripts/manage_migrations.py downgrade 1

# If migration is irreversible, restore from backup
python scripts/manage_backups.py restore <backup_file> --drop --yes
```

---

## 5. Post-Deployment Verification

- [ ] CI passes on main for all workflows
- [ ] Workers cycle without errors (wait 1-2 poll cycles)
- [ ] Lock gate passes on subsequent commits
- [ ] Touch index catches up (FR + Bug workers)
- [ ] Blast radius reports generate for any fix→in_review transitions
- [ ] Impact Gate validates fixes

```bash
# Quick health check
gh run list --branch main --limit 10 --json name,conclusion,status
```

---

## 6. Related Documents

- [runbook-ci-cd.md](runbook-ci-cd.md) — CI/CD pipeline reference
- [runbook-database-migration.md](runbook-database-migration.md) — migration procedures
- [runbook-incident-response.md](runbook-incident-response.md) — rollback and incident handling
- [runbook-backup-restore.md](runbook-backup-restore.md) — backup/restore
