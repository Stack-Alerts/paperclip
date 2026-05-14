# BACKUP — PaperClip Offsite Backup Pipeline (Operator Overview)

**Owner:** PlatformEngineer
**Last Updated:** 2026-05-12
**Cadence:** Every 4 hours (PaperClip routine)

## Pipeline Overview

```
PaperClip Instance                          Google Drive
+----------------------------+     +--------------------------+
|  backup-to-drive.sh         | --> |  gdrive:Paperclip-       |
|                             |     |  Backups/<companyId>/    |
|  Bundles:                   |     |  YYYY/MM/DD/HHMM/        |
|  * DB dump (paperclip-*)    |     |                          |
|  * companies/               |     |  * paperclip-instance-   |
|  * projects/                |     |    YYYYMMDD-HHMM.tar.gz  |
|  * skills/                  |     |  * MANIFEST.json          |
|  * data/storage/            |     |  * paperclip-*.sql.gz    |
|  * config.json (sanitized)  |     |                          |
|  * MANIFEST.json (SHA-256)  |     +--------------------------+
+----------------------------+
```

Backups are created by `backup-to-drive.sh` at `/home/sirrus/.paperclip/scripts/`. They bundle instance data (companies, projects, skills, file storage), the latest database dump, and a sanitised config.json with a SHA-256 manifest, then upload to Google Drive under a timestamped path.

A dead-man's-switch within the PaperClip routine alerts if no backup has been created within the expected window.

---

## Where Files Live

| Path | Purpose |
|------|---------|
| `/home/sirrus/.paperclip/scripts/backup-to-drive.sh` | Backup orchestrator script |
| `/home/sirrus/.paperclip/scripts/restore-from-drive.sh` | Restore orchestrator script |
| `/home/sirrus/.paperclip/scripts/rclone-bootstrap.sh` | One-time OAuth setup |
| `/home/sirrus/.paperclip/instances/default/logs/backup.log` | Backup log output |
| `/home/sirrus/.paperclip/instances/default/backup-state/last-success` | Timestamp of last successful backup |
| `/home/sirrus/.paperclip/instances/default/backup-state/last-failure` | Timestamp + error of last failure |
| `/home/sirrus/.paperclip/instances/default/data/backups/` | Local DB dump files |
| `~/.config/rclone/rclone.conf` | rclone OAuth tokens (**encrypted at rest** via `rclone config encryption`) |
| `~/.config/rclone/rclone-pass` | rclone config encryption password (chmod 600, outside repo) |

---

## How to Manually Trigger a Backup

```
/home/sirrus/.paperclip/scripts/backup-to-drive.sh
```

The script uses `flock` so concurrent runs (manual + scheduled) never collide.

### What Gets Uploaded

For a run at 2026-05-12T10:08Z, the GDrive path is:

```
gdrive:Paperclip-Backups/<companyId>/2026/05/12/1008/
  - paperclip-instance-20260512-1008.tar.gz   # instance data bundle
  - MANIFEST.json                              # SHA-256 + metadata
  - paperclip-20260512_100800.sql.gz           # raw DB dump (if one exists locally)
```

The tarball contains: `companies/`, `projects/`, `skills/`, `data/storage/`, `config.json` (sanitised).

---

## How to Inspect Google Drive Contents

```
# List backup directories (YYYY/MM/DD/HHMM tree)
rclone tree gdrive:Paperclip-Backups/<companyId> --depth 4

# Quick listing of latest backups
rclone ls gdrive:Paperclip-Backups/<companyId> --max-depth 4

# Check total usage
rclone about gdrive:

# View a MANIFEST.json for a specific backup
rclone cat gdrive:Paperclip-Backups/<companyId>/2026/05/12/1008/MANIFEST.json
```

Replace `<companyId>` with your actual company UUID from the PaperClip instance.

---

## Retention Policy

| Layer | Retention | Enforcement |
|-------|-----------|-------------|
| Google Drive | Manual | No auto-delete -- review periodically |
| Local DB dumps | Managed by PaperClip | PaperClip's internal retention |

To prune old backups on GDrive (example: delete backups older than 90 days):

```
# List backup directories with dates
rclone lsl gdrive:Paperclip-Backups/<companyId> --max-depth 4

# Remove a specific old backup
rclone purge gdrive:Paperclip-Backups/<companyId>/2026/02/01/0000
```

---

## State Files (Dead-Man's-Switch)

The PaperClip routine records success/failure timestamps:

```
# Last successful backup
cat /home/sirrus/.paperclip/instances/default/backup-state/last-success

# Last failure (if any)
cat /home/sirrus/.paperclip/instances/default/backup-state/last-failure
```

The dead-man's-switch fires an alert if no `last-success` update is detected within the expected interval + grace period.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Run backup now | `/home/sirrus/.paperclip/scripts/backup-to-drive.sh` |
| List GDrive backups | `rclone tree gdrive:Paperclip-Backups/<companyId> --depth 4` |
| View manifest | `rclone cat gdrive:Paperclip-Backups/<companyId>/2026/05/12/1008/MANIFEST.json` |
| Check last success | `cat /home/sirrus/.paperclip/instances/default/backup-state/last-success` |
| Check last failure | `cat /home/sirrus/.paperclip/instances/default/backup-state/last-failure` |
| Inspect live log | `tail -f /home/sirrus/.paperclip/instances/default/logs/backup.log` |
| Verify rclone remote | `rclone listremotes` (expect `gdrive:`) |
| Re-run OAuth | `/home/sirrus/.paperclip/scripts/rclone-bootstrap.sh` |
