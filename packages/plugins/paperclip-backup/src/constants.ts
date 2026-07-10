// constants.ts — paperclip-backup plugin
//
// Kept in sync with dist/constants.js so the source is not missing any
// exported action / data / state keys that the deployed worker registers.

export const PLUGIN_ID = "paperclip.backup";
export const PLUGIN_VERSION = "0.1.0";
export const CONFIG_VERSION = "0.1.0";

export const DEFAULT_CONFIG = {
  paperclipHome: process.env.PAPERCLIP_HOME ?? "/home/sirrus/.paperclip",
  backupScript:
    process.env.PAPERCLIP_BACKUP_SCRIPT ??
    "/home/sirrus/.paperclip/scripts/backup-to-drive.sh",
  restoreScript:
    process.env.PAPERCLIP_RESTORE_SCRIPT ??
    "/home/sirrus/.paperclip/scripts/restore-from-drive.sh",
  pruneScript:
    process.env.PAPERCLIP_PRUNE_SCRIPT ??
    "/home/sirrus/.paperclip/scripts/prune-local-dumps.sh",
  rcloneConfig: process.env.RCLONE_CONFIG ?? "/home/sirrus/.config/rclone/rclone.conf",
  rcloneRemote: process.env.RCLONE_REMOTE ?? "gdrive",
  defaultKeep: 10,
  backupsSubdir: "instances/default/data/backups",
  offsiteKeep: 30,
  offsiteSchedule: "every 2h",
  recoveryScript:
    process.env.PAPERCLIP_RECOVERY_SCRIPT ??
    "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh",
  recoveryDir: process.env.PAPERCLIP_RECOVERY_DIR ?? "/home/sirrus/paperclip-snapshots",
  // tiered backup retention (consumed by gdrive-tiered-upload.sh)
  gdriveTierEnabled: true,
  gdriveTierDailyKeep: 3,
  gdriveTierHourlyKeep: 2,
  gdriveTierRoot: "Paperclip-Backups",
  worktreeBackupScript:
    process.env.PAPERCLIP_WORKTREE_BACKUP_SCRIPT ??
    "/home/sirrus/paperclip-btcaaaaa-main/scripts/worktree-offsite.sh",
  worktreeBackupEnabled: true,
  worktreeBackupScheduleMs: 2 * 60 * 60 * 1000, // every 2 hours
};

export const DATA_KEYS = {
  listing: "listing",
  status: "status",
  config: "config",
  recoverySnapshots: "recovery-snapshots",
  locations: "locations",
};

export const SCRIPT_KEYS = {
  backup: "backupScript",
  restore: "restoreScript",
  prune: "pruneScript",
};

export const ACTION_KEYS = {
  runBackup: "run-backup",
  pruneLocal: "prune-local",
  pruneOffsite: "prune-offsite",
  restoreOffsite: "restore-offsite",
  restoreLocal: "restore-local",
  saveConfig: "save-config",
  forceBackup: "force-backup",
  forceRestore: "force-restore",
};

export const JOB_KEYS = {
  autoPruneOffsite: "auto-prune-offsite",
  autoOffsiteBackup: "auto-offsite-backup",
};

export const STATE_KEYS = {
  config: "backup-config",
  retention: "backup-retention",
  offsiteSchedule: "backup-offsite-schedule",
  offsiteLastRun: "backup-offsite-last-run",
  offsiteRunning: "offsite-running",
  backupLastRun: "backup-last-run",
  backupRunning: "backup-running",
};

// Recovery-system action/data keys, kept as separate constants so the
// recovery-related registrations can be removed in a single edit without
// touching the rest of the worker.
export const RECOVERY_SCRIPT_KEY = "recoveryScript";
export const RECOVERY_SCRIPT_KEY_TIERED = "gdriveTieredUploadScript";

export const RECOVERY_ACTION_KEYS = {
  forceBackup: "force-backup",
  forceRestore: "force-restore",
  deleteRecoverySnapshots: "delete-recovery-snapshots",
  uploadDailyBackup: "upload-daily-backup",
  uploadHourlyBackup: "upload-hourly-backup",
  setTierKeep: "set-tier-keep",
};

export const RECOVERY_DATA_KEYS = {
  snapshots: "recovery-snapshots",
  recoveryStatus: "recovery-status",
  tierStatus: "gdrive-tier-status",
};

export const DASHBOARD_WIDGET_SLOT_ID = "backup-dashboard-widget";
export const SIDEBAR_SLOT_ID = "backup-sidebar-nav";
export const PAGE_SLOT_ID = "backup-page";
export const SETTINGS_PAGE_SLOT_ID = "backup-settings-page";
export const BACKUP_ROUTE = "backups";