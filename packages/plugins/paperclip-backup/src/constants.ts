// constants.ts — paperclip-backup plugin

export const PLUGIN_ID = "paperclip.backup";
export const PLUGIN_VERSION = "0.2.0";
export const CONFIG_VERSION = "0.1.0";

export const DEFAULT_CONFIG = {
  paperclipHome: process.env.PAPERCLIP_HOME ?? "/home/sirrus/.paperclip",
  backupScript: process.env.PAPERCLIP_BACKUP_SCRIPT ?? "/home/sirrus/.paperclip/scripts/backup-to-drive.sh",
  restoreScript: process.env.PAPERCLIP_RESTORE_SCRIPT ?? "/home/sirrus/.paperclip/scripts/restore-from-drive.sh",
  pruneScript: process.env.PAPERCLIP_PRUNE_SCRIPT ?? "/home/sirrus/.paperclip/scripts/prune-local-dumps.sh",
  rcloneConfig: process.env.RCLONE_CONFIG ?? "/home/sirrus/.config/rclone/rclone.conf",
  rcloneRemote: process.env.PAPERCLONE_REMOTE ?? "gdrive",
  defaultKeep: 10,
  backupsSubdir: "instances/default/data/backups",
  offsiteKeep: 30,
  offsiteSchedule: "every 168h",
  recoveryScript: process.env.PAPERCLIP_RECOVERY_SCRIPT ?? "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh",
  recoveryDir: process.env.PAPERCLIP_RECOVERY_DIR ?? "/home/sirrus/paperclip-snapshots",
};

export const DATA_KEYS = {
  listing: "listing",
  status: "status",
  config: "config",
  recoverySnapshots: "recovery-snapshots",
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

export const DASHBOARD_WIDGET_SLOT_ID = "backup-dashboard-widget";
export const SIDEBAR_SLOT_ID = "backup-sidebar-nav";
export const PAGE_SLOT_ID = "backup-page";
export const SETTINGS_PAGE_SLOT_ID = "backup-settings-page";
export const BACKUP_ROUTE = "backups";
