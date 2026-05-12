# RESTORE — PaperClip Restore from Google Drive (Operator Runbook)

**Owner:** PlatformEngineer / DBA
**Audience:** On-call engineers
**Last Updated:** 2026-05-12

## Restore Tool

The restore script lives at `/home/sirrus/.paperclip/scripts/restore-from-drive.sh`.

```
Usage: restore-from-drive.sh <command> [args]

Commands:
  list                          List available backups
  latest  [dest-dir]            Restore most recent backup
  <path>  [dest-dir]            Restore specific backup (e.g. 2026/05/12/1008)
```

---

## 1. DB-Only Restore

Use when: the PostgreSQL database is corrupted but instance files are intact.

### Step 1: List available backups

```
/home/sirrus/.paperclip/scripts/restore-from-drive.sh list
```

This shows the available backup timestamps from GDrive.

### Step 2: Download the latest backup

```
/home/sirrus/.paperclip/scripts/restore-from-drive.sh latest /tmp/restore
```

Or a specific backup:

```
/home/sirrus/.paperclip/scripts/restore-from-drive.sh 2026/05/12/1008 /tmp/restore
```

### Step 3: Restore the database

```
# Find the SQL dump in the download directory
ls /tmp/restore/paperclip-*.sql.gz

# Restore it
gunzip -c /tmp/restore/paperclip-20260512_100800.sql.gz | psql -h localhost paperclip
```

### Step 4: Verify

```
# Check alembic version matches expected
psql -h localhost paperclip -c "SELECT version_num FROM alembic_version"

# Spot-check key tables
psql -h localhost paperclip -c "SELECT count(*) FROM companies"
psql -h localhost paperclip -c "SELECT count(*) FROM projects"
```

---

## 2. Full Restore from Scratch

Use when: you have a new machine or total instance loss.

### Step 1: Reinstall PaperClip

Follow the standard PaperClip installation procedure to get a base instance running.

### Step 2: Restore .env and config

```
# Restore from secure backup (NOT from git)
cp /path/to/backup/.env /home/sirrus/.paperclip/instances/default/.env
chmod 600 /home/sirrus/.paperclip/instances/default/.env
```

### Step 3: Download the latest backup

```
/home/sirrus/.paperclip/scripts/restore-from-drive.sh latest /tmp/restore
```

### Step 4: Examine the manifest

```
cat /tmp/restore/MANIFEST.json
```

Expected output:
```json
{
  "timestamp": "2026-05-12T10:08:00Z",
  "hostname": "paperclip-server",
  "paperclipVersion": "x.y.z",
  "companyId": "<uuid>",
  "sourceDump": "paperclip-20260512_100800.sql.gz",
  "payloadSha256": "abc123...",
  "payloadSizeBytes": 12345678
}
```

### Step 5: Restore the database

```
gunzip -c /tmp/restore/paperclip-*.sql.gz | psql -h localhost paperclip
```

### Step 6: Copy instance files

The payload tarball was already extracted by `restore-from-drive.sh`:

```
/tmp/restore/
  - MANIFEST.json
  - paperclip-instance-20260512-1008.tar.gz
  - paperclip-20260512_100800.sql.gz
  - config.json
  - companies/
  - projects/
  - skills/
  - storage/
```

Copy these into the PaperClip instance directory:

```
INSTANCE_DIR=/home/sirrus/.paperclip/instances/default

cp /tmp/restore/config.json "$INSTANCE_DIR/config.json"
cp -r /tmp/restore/companies/* "$INSTANCE_DIR/companies/"
cp -r /tmp/restore/projects/* "$INSTANCE_DIR/projects/"
cp -r /tmp/restore/skills/* "$INSTANCE_DIR/skills/"
cp -r /tmp/restore/storage/* "$INSTANCE_DIR/data/storage/"
```

### Step 7: Restart PaperClip

```
# Restart the PaperClip service
systemctl restart paperclip
```

### Step 8: Verify

1. Log in to the PaperClip UI
2. Confirm all companies, projects, and skills are present
3. Check the alembic migration version:
   ```
   psql -h localhost paperclip -c "SELECT version_num FROM alembic_version"
   ```

---

## 3. Backup Selection Guide

| Criterion | Command |
|-----------|---------|
| Latest backup | `restore-from-drive.sh latest /tmp/restore` |
| Specific date/time | `restore-from-drive.sh 2026/05/12/1008 /tmp/restore` |
| Before a bad migration | Pick a backup timestamped before the migration was applied |
| Preview manifest (no download) | `rclone cat gdrive:Paperclip-Backups/<companyId>/<path>/MANIFEST.json` |
| List all backups | `rclone tree gdrive:Paperclip-Backups/<companyId> --depth 4` |

---

## 4. Emergency Commands Cheat Sheet

```
# -- List backups --------------------------------------------------
/home/sirrus/.paperclip/scripts/restore-from-drive.sh list
rclone tree gdrive:Paperclip-Backups/<companyId> --depth 4

# -- Download + restore latest -------------------------------------
/home/sirrus/.paperclip/scripts/restore-from-drive.sh latest /tmp/restore

# -- DB restore ----------------------------------------------------
gunzip -c /tmp/restore/paperclip-*.sql.gz | psql -h localhost paperclip

# -- Full file restore ---------------------------------------------
INSTANCE_DIR=/home/sirrus/.paperclip/instances/default
cp /tmp/restore/config.json "$INSTANCE_DIR/config.json"
cp -r /tmp/restore/companies/* "$INSTANCE_DIR/companies/" 2>/dev/null || true
cp -r /tmp/restore/projects/* "$INSTANCE_DIR/projects/" 2>/dev/null || true
cp -r /tmp/restore/skills/* "$INSTANCE_DIR/skills/" 2>/dev/null || true
cp -r /tmp/restore/storage/* "$INSTANCE_DIR/data/storage/" 2>/dev/null || true

# -- Verify --------------------------------------------------------
psql -h localhost paperclip -c "SELECT count(*) FROM companies"
psql -h localhost paperclip -c "SELECT version_num FROM alembic_version"
systemctl status paperclip

# -- Manual GDrive download ----------------------------------------
rclone copy gdrive:Paperclip-Backups/<companyId>/2026/05/12/1008 /tmp/restore --progress
```
