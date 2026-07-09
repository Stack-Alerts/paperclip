// manifest.ts — paperclip-backup plugin manifest

import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";
import {
  DEFAULT_CONFIG,
  PLUGIN_ID,
  PLUGIN_VERSION,
} from "./constants.js";

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
    "events.subscribe",
    "http.outbound",
    "agents.read",
    "issues.read",
    "issue.comments.read",
    "issue.comments.create",
    "issue.documents.read",
    "activity.log.write",
    "plugin.state.read",
    "plugin.state.write",
    "instance.settings.register",
    "jobs.schedule",
    "ui.dashboardWidget.register",
    "ui.sidebar.register",
    "ui.page.register",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui",
  },
  instanceConfigSchema: {
    type: "object",
    properties: {
      paperclipHome: { type: "string", title: "PAPERCLIP_HOME", default: DEFAULT_CONFIG.paperclipHome },
      backupScript: { type: "string", title: "Backup script", default: DEFAULT_CONFIG.backupScript },
      restoreScript: { type: "string", title: "Restore script", default: DEFAULT_CONFIG.restoreScript },
      pruneScript: { type: "string", title: "Prune script", default: DEFAULT_CONFIG.pruneScript },
      rcloneConfig: { type: "string", title: "rclone config", default: DEFAULT_CONFIG.rcloneConfig },
      rcloneRemote: { type: "string", title: "rclone remote", default: DEFAULT_CONFIG.rcloneRemote },
      defaultKeep: { type: "integer", title: "Default local keep", default: DEFAULT_CONFIG.defaultKeep },
      backupsSubdir: { type: "string", title: "Backups subdir", default: DEFAULT_CONFIG.backupsSubdir },
      offsiteKeep: { type: "integer", title: "Offsite keep", default: DEFAULT_CONFIG.offsiteKeep },
      offsiteSchedule: { type: "string", title: "Offsite schedule", default: DEFAULT_CONFIG.offsiteSchedule },
      recoveryScript: { type: "string", title: "Recovery script", default: DEFAULT_CONFIG.recoveryScript },
      recoveryDir: { type: "string", title: "Recovery snapshots dir", default: DEFAULT_CONFIG.recoveryDir },
    },
  },
  slots: [
    {
      type: "dashboardWidget",
      id: "backup-dashboard-widget",
      exportName: "BackupDashboardWidget",
      displayName: "Backup Status",
    },
    {
      type: "sidebar",
      id: "backup-sidebar-nav",
      exportName: "BackupSidebarNav",
      displayName: "Backups",
    },
    {
      type: "page",
      id: "backup-page",
      exportName: "BackupManagerPage",
      displayName: "Backup Manager",
      routePath: "backups",
    },
    {
      type: "settingsPage",
      id: "backup-settings-page",
      exportName: "BackupSettingsPage",
      displayName: "Backup Settings",
    },
  ],
};

export { manifest };
export default manifest;
