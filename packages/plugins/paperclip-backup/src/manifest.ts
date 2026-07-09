// manifest.ts — paperclip-backup plugin manifest
//
// Kept in sync with dist/manifest.js. The capability list is intentionally
// conservative (matches what the deployed dist/manifest.js requests) so the
// plugin capability validator on rebuild doesn't reject the package for
// declaring capabilities the worker never uses.

import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";
import {
  DEFAULT_CONFIG,
  PLUGIN_ID,
} from "./constants.js";

const PLUGIN_VERSION = "0.1.0";
const DASHBOARD_WIDGET_SLOT_ID = "backup-dashboard-widget";
const SIDEBAR_SLOT_ID = "backup-sidebar-nav";
const PAGE_SLOT_ID = "backup-page";
const SETTINGS_PAGE_SLOT_ID = "backup-settings-page";
const BACKUP_ROUTE = "backups";

const manifest: PaperclipPluginManifestV1 = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: "Backup & Restore",
  description:
    "Run, list, and restore Paperclip backups (offsite rclone to Google Drive, local DB dumps). " +
    "Wraps the existing paperclip-backup + prune-local-dumps systemd services. " +
    "Adds Force Backup and Force Restore actions wired to scripts/recovery.sh.",
  author: "Paperclip",
  categories: ["automation", "ui"],
  capabilities: [
    "ui.dashboardWidget.register",
    "ui.sidebar.register",
    "ui.page.register",
    "plugin.state.read",
    "plugin.state.write",
    "instance.settings.register",
    "jobs.schedule",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui",
  },
  instanceConfigSchema: {
    type: "object",
    properties: {
      paperclipHome: {
        type: "string",
        title: "PAPERCLIP_HOME",
        default: DEFAULT_CONFIG.paperclipHome,
      },
      backupScript: {
        type: "string",
        title: "Backup script",
        default: DEFAULT_CONFIG.backupScript,
      },
      restoreScript: {
        type: "string",
        title: "Restore script",
        default: DEFAULT_CONFIG.restoreScript,
      },
      pruneScript: {
        type: "string",
        title: "Prune script",
        default: DEFAULT_CONFIG.pruneScript,
      },
      rcloneConfig: {
        type: "string",
        title: "rclone config",
        default: DEFAULT_CONFIG.rcloneConfig,
      },
      rcloneRemote: {
        type: "string",
        title: "rclone remote",
        default: DEFAULT_CONFIG.rcloneRemote,
      },
      defaultKeep: {
        type: "integer",
        title: "Default local keep",
        default: DEFAULT_CONFIG.defaultKeep,
      },
      backupsSubdir: {
        type: "string",
        title: "Backups subdir",
        default: DEFAULT_CONFIG.backupsSubdir,
      },
      offsiteKeep: {
        type: "integer",
        title: "Offsite keep",
        default: DEFAULT_CONFIG.offsiteKeep,
      },
      offsiteSchedule: {
        type: "string",
        title: "Offsite schedule",
        default: DEFAULT_CONFIG.offsiteSchedule,
      },
      recoveryScript: {
        type: "string",
        title: "Recovery script",
        default: DEFAULT_CONFIG.recoveryScript,
      },
      recoveryDir: {
        type: "string",
        title: "Recovery snapshots dir",
        default: DEFAULT_CONFIG.recoveryDir,
      },
    },
  },
  ui: {
    slots: [
      {
        type: "dashboardWidget",
        id: DASHBOARD_WIDGET_SLOT_ID,
        exportName: "BackupDashboardWidget",
        displayName: "Backup Status",
      },
      {
        type: "sidebar",
        id: SIDEBAR_SLOT_ID,
        exportName: "BackupSidebarNav",
        displayName: "Backups",
      },
      {
        type: "page",
        id: PAGE_SLOT_ID,
        exportName: "BackupManagerPage",
        displayName: "Backup Manager",
        routePath: BACKUP_ROUTE,
      },
      {
        type: "settingsPage",
        id: SETTINGS_PAGE_SLOT_ID,
        exportName: "BackupSettingsPage",
        displayName: "Backup Settings",
      },
    ],
  },
  jobs: [
    {
      jobKey: "auto-prune-offsite",
      displayName: "Auto-prune offsite (GDrive) backups",
      description:
        "Periodically deletes the oldest offsite backups beyond the configured retention count.",
    },
  ],
};

export { manifest };
export default manifest;