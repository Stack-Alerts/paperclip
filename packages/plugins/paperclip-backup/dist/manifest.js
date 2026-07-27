// src/constants.ts
var PLUGIN_ID = "paperclip.backup";
var DEFAULT_CONFIG = {
  paperclipHome: process.env.PAPERCLIP_HOME ?? "/home/sirrus/.paperclip",
  backupScript: process.env.PAPERCLIP_BACKUP_SCRIPT ?? "/home/sirrus/.paperclip/scripts/backup-to-drive.sh",
  restoreScript: process.env.PAPERCLIP_RESTORE_SCRIPT ?? "/home/sirrus/.paperclip/scripts/restore-from-drive.sh",
  pruneScript: process.env.PAPERCLIP_PRUNE_SCRIPT ?? "/home/sirrus/.paperclip/scripts/prune-local-dumps.sh",
  rcloneConfig: process.env.RCLONE_CONFIG ?? "/home/sirrus/.config/rclone/rclone.conf",
  rcloneRemote: process.env.RCLONE_REMOTE ?? "gdrive",
  defaultKeep: 10,
  backupsSubdir: "instances/default/data/backups",
  offsiteKeep: 30,
  offsiteSchedule: "every 2h",
  recoveryScript: process.env.PAPERCLIP_RECOVERY_SCRIPT ?? "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh",
  recoveryDir: process.env.PAPERCLIP_RECOVERY_DIR ?? "/home/sirrus/paperclip-snapshots",
  // tiered backup retention (consumed by gdrive-tiered-upload.sh)
  gdriveTierEnabled: true,
  gdriveTierDailyKeep: 3,
  gdriveTierHourlyKeep: 2,
  gdriveTierRoot: "Paperclip-Backups",
  worktreeBackupScript: process.env.PAPERCLIP_WORKTREE_BACKUP_SCRIPT ?? "/home/sirrus/paperclip-btcaaaaa-main/scripts/worktree-offsite.sh",
  worktreeBackupEnabled: true,
  worktreeBackupScheduleMs: 2 * 60 * 60 * 1e3
  // every 2 hours
};

// src/manifest.ts
var PLUGIN_VERSION = "0.1.0";
var DASHBOARD_WIDGET_SLOT_ID = "backup-dashboard-widget";
var SIDEBAR_SLOT_ID = "backup-sidebar-nav";
var PAGE_SLOT_ID = "backup-page";
var SETTINGS_PAGE_SLOT_ID = "backup-settings-page";
var BACKUP_ROUTE = "backups";
var manifest = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: "Backup & Restore",
  description: "Run, list, and restore Paperclip backups (offsite rclone to Google Drive, local DB dumps). Wraps the existing paperclip-backup + prune-local-dumps systemd services. Adds Force Backup and Force Restore actions wired to scripts/recovery.sh.",
  author: "Paperclip",
  categories: ["automation", "ui"],
  capabilities: [
    "ui.dashboardWidget.register",
    "ui.sidebar.register",
    "ui.page.register",
    "plugin.state.read",
    "plugin.state.write",
    "instance.settings.register",
    "jobs.schedule"
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui"
  },
  instanceConfigSchema: {
    type: "object",
    properties: {
      paperclipHome: {
        type: "string",
        title: "PAPERCLIP_HOME",
        default: DEFAULT_CONFIG.paperclipHome
      },
      backupScript: {
        type: "string",
        title: "Backup script",
        default: DEFAULT_CONFIG.backupScript
      },
      restoreScript: {
        type: "string",
        title: "Restore script",
        default: DEFAULT_CONFIG.restoreScript
      },
      pruneScript: {
        type: "string",
        title: "Prune script",
        default: DEFAULT_CONFIG.pruneScript
      },
      rcloneConfig: {
        type: "string",
        title: "rclone config",
        default: DEFAULT_CONFIG.rcloneConfig
      },
      rcloneRemote: {
        type: "string",
        title: "rclone remote",
        default: DEFAULT_CONFIG.rcloneRemote
      },
      defaultKeep: {
        type: "integer",
        title: "Default local keep",
        default: DEFAULT_CONFIG.defaultKeep
      },
      backupsSubdir: {
        type: "string",
        title: "Backups subdir",
        default: DEFAULT_CONFIG.backupsSubdir
      },
      offsiteKeep: {
        type: "integer",
        title: "Offsite keep",
        default: DEFAULT_CONFIG.offsiteKeep
      },
      offsiteSchedule: {
        type: "string",
        title: "Offsite schedule",
        default: DEFAULT_CONFIG.offsiteSchedule
      },
      recoveryScript: {
        type: "string",
        title: "Recovery script",
        default: DEFAULT_CONFIG.recoveryScript
      },
      recoveryDir: {
        type: "string",
        title: "Recovery snapshots dir",
        default: DEFAULT_CONFIG.recoveryDir
      }
    }
  },
  ui: {
    slots: [
      {
        type: "dashboardWidget",
        id: DASHBOARD_WIDGET_SLOT_ID,
        exportName: "BackupDashboardWidget",
        displayName: "Backup Status"
      },
      {
        type: "sidebar",
        id: SIDEBAR_SLOT_ID,
        exportName: "BackupSidebarNav",
        displayName: "Backups"
      },
      {
        type: "page",
        id: PAGE_SLOT_ID,
        exportName: "BackupManagerPage",
        displayName: "Backup Manager",
        routePath: BACKUP_ROUTE
      },
      {
        type: "settingsPage",
        id: SETTINGS_PAGE_SLOT_ID,
        exportName: "BackupSettingsPage",
        displayName: "Backup Settings"
      }
    ]
  },
  jobs: [
    {
      jobKey: "auto-prune-offsite",
      displayName: "Auto-prune offsite (GDrive) backups",
      description: "Periodically deletes the oldest offsite backups beyond the configured retention count.",
      // Daily at 04:13 local (after the daily snapshot/upload at 04:00 finishes
      // and before the 4h offsite cycle at 0/4/8/12/16/20).
      schedule: "13 4 * * *"
    },
    {
      jobKey: "auto-offsite-backup",
      displayName: "Auto offsite backup (DB + worktree) every 2h",
      description: "Uploads the latest DB dump and a worktree snapshot to gdrive under the same per-company prefix. Retention is then controlled by the prune-offsite action which honors the configured keep counts.",
      // Every 2 hours on the hour.
      schedule: "0 */2 * * *"
    },
    {
      jobKey: "tiered-hourly-upload",
      displayName: "Tiered hourly backup upload (gdrive)",
      description: "Promotes the latest recovery snapshot into the gdrive 'hourly' tier so the last 6h of state stays recoverable at short retention.",
      // Every 6 hours: 00:00, 06:00, 12:00, 18:00.
      schedule: "0 */6 * * *"
    },
    {
      jobKey: "tiered-daily-upload",
      displayName: "Tiered daily backup upload (gdrive)",
      description: "Promotes the latest recovery snapshot into the gdrive 'daily' tier so the last 3 days of state stays recoverable at medium retention.",
      // Daily at 04:05 local — runs just after auto-prune-offsite so the
      // daily promotion sees the same snapshot pruned moments earlier.
      schedule: "5 4 * * *"
    }
  ]
};
var manifest_default = manifest;
export {
  manifest_default as default,
  manifest
};
//# sourceMappingURL=manifest.js.map
