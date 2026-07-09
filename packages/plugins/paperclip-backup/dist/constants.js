export const PLUGIN_ID = "paperclip.backup";
export const CONFIG_VERSION = "0.1.0";
export const DEFAULT_CONFIG = {
    // Default paths match the layout used by the paperclip-backup systemd
    // service (see /home/sirrus/.paperclip/scripts/backup-to-drive.sh).
    paperclipHome: process.env.PAPERCLIP_HOME ?? "/home/sirrus/.paperclip",
    backupScript: "/home/sirrus/.paperclip/scripts/backup-to-drive.sh",
    restoreScript: "/home/sirrus/.paperclip/scripts/restore-from-drive.sh",
    pruneScript: "/home/sirrus/.paperclip/scripts/prune-local-dumps.sh",
    rcloneConfig: process.env.RCLONE_CONFIG ?? "/home/sirrus/.config/rclone/rclone.conf",
    rcloneRemote: process.env.RCLONE_REMOTE ?? "gdrive",
    defaultKeep: 10,
    backupsSubdir: "instances/default/data/backups",
    // Offsite prune: keep the newest N dated folders on GDrive, delete older ones.
    // 0 = disabled (never auto-prune offsite).
    offsiteKeep: 30,
    // Schedule for the auto-prune. Format:
    //   "every Nh"  → run every N hours (e.g. "every 24h")
    //   "every Nd"  → run every N days (e.g. "every 7d")
    //   ""          → disabled
    offsiteSchedule: "every 168h",
    // GDrive tiered-backup retention (used by gdrive-tiered-upload.sh):
    //   gdriveTierEnabled      toggle the whole tiered backup flow
    //   gdriveTierDailyKeep    how many daily-tier dirs to keep on GDrive
    //   gdriveTierHourlyKeep   how many hourly-tier dirs to keep on GDrive
    //   gdriveTierRoot         GDrive prefix (default Paperclip-Backups)
    gdriveTierEnabled: true,
    gdriveTierDailyKeep: 3,
    gdriveTierHourlyKeep: 2,
    gdriveTierRoot: "Paperclip-Backups",
};
export const DATA_KEYS = {
    listing: "listing",
    status: "status",
    config: "config",
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
//# sourceMappingURL=constants.js.map

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
