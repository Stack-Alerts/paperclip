/**
 * Paperclip Backup & Restore Plugin
 *
 * Surfaces the existing offsite backup machinery (rclone + paperclip-backup
 * systemd service) directly in the Paperclip UI:
 *   - Dashboard widget: latest backup status & local DB dump count
 *   - Sidebar nav entry: opens the full Backup Manager page
 *   - Page: list offsite backups, list local DB dumps, run backup, run
 *     prune, restore from offsite, restore from local
 *   - Settings page: configure retention defaults + script paths
 */
const PLUGIN_ID = "paperclip.backup";
const PLUGIN_VERSION = "0.1.0";
const DASHBOARD_WIDGET_SLOT_ID = "backup-dashboard-widget";
const SIDEBAR_SLOT_ID = "backup-sidebar-nav";
const PAGE_SLOT_ID = "backup-page";
const SETTINGS_PAGE_SLOT_ID = "backup-settings-page";
const BACKUP_ROUTE = "backups";
const manifest = {
    id: PLUGIN_ID,
    apiVersion: 1,
    version: PLUGIN_VERSION,
    displayName: "Backup & Restore",
    description: "Run, list, and restore Paperclip backups (offsite rclone to Google Drive, local DB dumps). " +
        "Wraps the existing paperclip-backup + prune-local-dumps systemd services.",
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
    jobs: [
        {
            jobKey: "auto-prune-offsite",
            displayName: "Auto-prune offsite (GDrive) backups",
            description: "Periodically deletes the oldest offsite backups beyond the configured retention count. " +
                "The schedule is read from the plugin's saved config ('every Nh' or 'every Nd'); empty = disabled.",
        },
    ],
    ui: {
        slots: [
            {
                type: "dashboardWidget",
                id: DASHBOARD_WIDGET_SLOT_ID,
                displayName: "Backup Status",
                exportName: "BackupDashboardWidget",
            },
            {
                type: "sidebar",
                id: SIDEBAR_SLOT_ID,
                displayName: "Backups",
                exportName: "BackupSidebarNavItem",
            },
            {
                type: "page",
                id: PAGE_SLOT_ID,
                displayName: "Backup Manager",
                exportName: "BackupManagerPage",
                routePath: BACKUP_ROUTE,
            },
            {
                type: "settingsPage",
                id: SETTINGS_PAGE_SLOT_ID,
                displayName: "Backup Settings",
                exportName: "BackupSettingsPage",
            },
        ],
    },
};
export default manifest;
//# sourceMappingURL=manifest.js.map