# paperclip-backup

Paperclip Backup & Restore plugin — surfaces offsite (rclone → Google Drive) and local DB dump management in the Paperclip UI for the BTC-Trade-Engine.

## What it does

- **Dashboard widget** — latest backup status & local DB dump count
- **Sidebar nav + Backup Manager page** at `/backups` — list offsite backups, list local DB dumps, run backup, prune, restore
- **Backup Settings page** — configure retention defaults + script paths
- **Auto-prune offsite job** — periodic rclone-based retention for GDrive backups

## Backed by

- `paperclip-backup` systemd service (or `scripts/backup-to-drive.sh`) for the actual rclone push
- `prune-local-dumps.sh` for local DB retention
- `restore-from-drive.sh` for offsite restore

## Plugin metadata

- Plugin key: `paperclip.backup`
- Display name: Backup & Restore
- API version: 1

## Slots

| Type | Slot ID | Display name |
| --- | --- | --- |
| dashboardWidget | `backup-dashboard-widget` | Backup Status |
| sidebar | `backup-sidebar-nav` | Backups |
| page (`/backups`) | `backup-page` | Backup Manager |
| settingsPage | `backup-settings-page` | Backup Settings |

## Install (local install via Paperclip API)

```bash
curl -X POST http://127.0.0.1:3100/api/plugins/install \
  -H 'Content-Type: application/json' \
  -d '{"packageName":"/home/sirrus/projects/.../packages/plugins/paperclip-backup","isLocalPath":true}'
```

## Default config paths

| Key | Default |
| --- | --- |
| `paperclipHome` | `$PAPERCLIP_HOME` or `/home/sirrus/.paperclip` |
| `backupScript` | `/home/sirrus/.paperclip/scripts/backup-to-drive.sh` |
| `restoreScript` | `/home/sirrus/.paperclip/scripts/restore-from-drive.sh` |
| `pruneScript` | `/home/sirrus/.paperclip/scripts/prune-local-dumps.sh` |
| `rcloneConfig` | `$RCLONE_CONFIG` or `/home/sirrus/.config/rclone/rclone.conf` |
| `rcloneRemote` | `$RCLONE_REMOTE` or `gdrive` |
| `defaultKeep` | `10` |
| `offsiteKeep` | `30` |
| `offsiteSchedule` | `every 168h` |