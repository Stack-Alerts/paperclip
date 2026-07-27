# paperclip-backup

Paperclip Backup & Restore plugin — surfaces offsite (rclone → Google Drive) and local DB dump management in the Paperclip UI for the BTC-Trade-Engine.

## What it does

- **Dashboard widget** — latest backup status & local DB dump count
- **Sidebar nav + Backup Manager page** at `/backups` — list offsite backups, list local DB dumps, run backup, prune, restore
- **Backup Settings page** — configure retention defaults + script paths
- **Auto-prune offsite job** — periodic rclone-based retention for GDrive backups
- **GDrive cleanup panel** — flag backup leaves as "golden" to protect them, and bulk-prune stale leaves with defense-in-depth safety guards. The cleanup tab walks every backup leaf on gdrive under `Paperclip-Backups/`, lets you mark/unmark each leaf as golden, and previews exactly what would be deleted before any actual deletion.

## GDrive cleanup panel — safety model

The cleanup tab exposes three operations, each with its own safety flags:

| Operation | Default | Required flags for real delete | Scope guard |
| --- | --- | --- | --- |
| `gdrive-cleanup-listing` (read-only) | always safe | n/a (read-only) | n/a |
| `gdrive-cleanup-preview` (read-only) | always safe | n/a (read-only) | n/a |
| `mark-golden` (write sidecar) | safe by default | none — writes a brand-new sidecar file | path must start with a known tier root |
| `cleanup-stale` (delete) | **dry-run + testOnly** | `confirmDelete:true` for production scopes, `allowActiveBtcCompany:true` for per-company scope, `dryRun:false` to actually delete | the golden sidecar always protects a leaf, no matter what flags are passed |

### Defense-in-depth guarantees

1. **Golden sidecar is sacred.** A `.golden.json` sidecar file in any leaf directory protects that leaf from `cleanup-stale`. The action refuses to delete any leaf whose sidecar says `golden: true`, regardless of which other flags are set.
2. **`dryRun` defaults to `true`.** The action only does real deletes when the caller passes `dryRun: false`. A bare `cleanup-stale` invocation is always a preview.
3. **Scope defaults to `testOnly`.** A bare `cleanup-stale` invocation with no scope only touches the `Paperclip-Backups/test-cleanup-panel` subtree, which is dedicated to integration testing and never contains real backups.
4. **`confirmDelete` is required for any production scope.** Scopes `perCompany`, `hourly`, `daily`, `all` all require `confirmDelete: true` before any deletion will be considered.
5. **`allowActiveBtcCompany` is required for the per-company prefix.** The per-company tier is the only tier that contains real production backups, so it requires an explicit second opt-in.

### Path whitelist

`mark-golden` and `cleanup-stale` both reject any leaf path that does not start with one of:

- `Paperclip-Backups/<companyId>/...` (per-company tier)
- `Paperclip-Backups/hourly/...` (global hourly tier)
- `Paperclip-Backups/daily/...` (global daily tier)
- `Paperclip-Backups/test-cleanup-panel/...` (cleanup-panel integration test prefix)

The path check uses a strict `^Paperclip-Backups/[^/]+/` regex for the per-company tier so `Paperclip-Backups-evil/...` is rejected even though it contains the substring.

### Logging

Every action logs a warning before any real delete (or any sidecar write), so the operator can audit the cleanup activity in the worker log:

```
cleanup-panel: writing golden sidecar=<path> setBy=<user> reason=<text>
cleanup-stale: deleting leaf path=<path> scope=<scope> thresholdDays=<N>
```

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
| page (`/backups`) | `backup-page` | Backup Manager (with Cleanup (GDrive) tab) |
| settingsPage | `backup-settings-page` | Backup Settings |

## Plugin actions

| Key | Purpose |
| --- | --- |
| `run-backup`, `prune-local`, `prune-offsite`, `restore-offsite`, `restore-local` | existing |
| `force-backup`, `force-restore`, `delete-recovery-snapshots`, `upload-daily-backup`, `upload-hourly-backup`, `set-tier-keep` | existing |
| `mark-golden` | write/delete a `.golden.json` sidecar on a backup leaf |
| `cleanup-stale` | delete non-golden stale backup leaves (with safety guards) |
| `set-golden-cleanup-threshold` | persist a preferred threshold (days) for the cleanup panel |

## Plugin data providers

| Key | Purpose |
| --- | --- |
| `listing`, `status`, `config`, `recovery-snapshots`, `gdrive-tier-status` | existing |
| `gdrive-cleanup-listing` | walk every leaf on gdrive under `Paperclip-Backups/`, with per-leaf golden flag + golden bytes |
| `gdrive-cleanup-preview` | dry-run preview: what `cleanup-stale` WOULD delete given a scope and threshold |

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

## Tests

```bash
pnpm test
```

The cleanup test suite (`tests/cleanup.spec.ts`) covers:

- `cleanup-stale` refuses production scope without `confirmDelete`
- `cleanup-stale` refuses perCompany/all scope without `allowActiveBtcCompany`
- `cleanup-stale` defaults to `testOnly` scope (safe default)
- `cleanup-stale` defaults to `dryRun=true` (no real deletes)
- Unknown scope falls back to `testOnly`
- `thresholdDays` is clamped to 1–365
- `mark-golden` rejects paths outside `Paperclip-Backups/`
- `mark-golden` rejects the `Paperclip-Backups-evil/` pattern
- `mark-golden` accepts valid per-company / hourly / daily / test prefix paths
- `gdrive-cleanup-listing` always returns the four-tier structure
- `gdrive-cleanup-preview` is always `dryRun: true`
- `gdrive-cleanup-preview` returns `scopeErrors` for perCompany without `allowActiveBtcCompany`
- Manifest wires up the right capabilities