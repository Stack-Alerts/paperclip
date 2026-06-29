import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";
import {
  DEFAULT_CONFIG,
  EXPORT_NAMES,
  PLUGIN_ID,
  PLUGIN_VERSION,
  PAGE_ROUTE,
  SLOT_IDS,
} from "./constants.js";

const manifest: PaperclipPluginManifestV1 = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: "Git Merges",
  description:
    "Runs BTC-Trade-Engine-PaperClip's scripts/merge_queue_status.py on a schedule and exposes the output as a Paperclip dashboard panel. Auto-refresh, time-block (e.g. every 5 min between 8am and 4pm), manual scan, and clear-output controls.",
  author: "Stack-Alerts",
  categories: ["ui", "automation", "connector"],
  capabilities: [
    "plugin.state.read",
    "plugin.state.write",
    "instance.settings.register",
    "ui.page.register",
    "ui.sidebar.register",
    "jobs.schedule",
    "events.subscribe",
  ],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui",
  },
  instanceConfigSchema: {
    type: "object",
    properties: {
      pythonPath: {
        type: "string",
        title: "Python interpreter",
        default: DEFAULT_CONFIG.pythonPath,
        description:
          "Absolute path to the python executable that runs the merge queue script. Defaults to the BTC repo's venv.",
      },
      repoPath: {
        type: "string",
        title: "BTC repo path",
        default: DEFAULT_CONFIG.repoPath,
        description:
          "Working directory for the script. The script reads .env from this directory.",
      },
      scriptPath: {
        type: "string",
        title: "Script path (relative to repoPath)",
        default: DEFAULT_CONFIG.scriptPath,
      },
      autoRefreshEnabled: {
        type: "boolean",
        title: "Auto-refresh enabled",
        default: DEFAULT_CONFIG.autoRefreshEnabled,
      },
      autoRefreshIntervalSeconds: {
        type: "integer",
        title: "Auto-refresh interval (seconds)",
        default: DEFAULT_CONFIG.autoRefreshIntervalSeconds,
        minimum: 30,
        maximum: 86_400,
      },
      timeBlockEnabled: {
        type: "boolean",
        title: "Limit auto-refresh to a time block",
        default: DEFAULT_CONFIG.timeBlockEnabled,
      },
      timeBlockStartHour: {
        type: "integer",
        title: "Time block start hour (0-23, local time)",
        default: DEFAULT_CONFIG.timeBlockStartHour,
        minimum: 0,
        maximum: 23,
      },
      timeBlockEndHour: {
        type: "integer",
        title: "Time block end hour (0-23, local time)",
        default: DEFAULT_CONFIG.timeBlockEndHour,
        minimum: 0,
        maximum: 23,
      },
      showJson: {
        type: "boolean",
        title: "Pass --json to the script",
        default: DEFAULT_CONFIG.showJson,
      },
      maxOutputChars: {
        type: "integer",
        title: "Max output characters to keep per scan",
        default: DEFAULT_CONFIG.maxOutputChars,
        minimum: 1000,
        maximum: 5_000_000,
      },
      scanTimeoutSeconds: {
        type: "integer",
        title: "Per-scan soft timeout (seconds)",
        default: DEFAULT_CONFIG.scanTimeoutSeconds,
        minimum: 10,
        maximum: 3600,
      },
    },
  },
  jobs: [
    {
      jobKey: "git-merges-auto-scan",
      displayName: "Git Merges auto-scan",
      description:
        "Periodic heartbeat that runs merge_queue_status.py when auto-refresh is enabled and (optionally) inside the configured time block.",
      schedule: "*/5 * * * *",
    },
  ],
  ui: {
    slots: [
      {
        type: "page",
        id: SLOT_IDS.page,
        displayName: "Git Merges",
        exportName: EXPORT_NAMES.page,
        routePath: PAGE_ROUTE,
      },
      {
        type: "sidebar",
        id: SLOT_IDS.presetsSidebar,
        displayName: "Git Merges",
        exportName: EXPORT_NAMES.presetsSidebar,
        order: 110,
      },
      {
        type: "settingsPage",
        id: SLOT_IDS.settingsPage,
        displayName: "Git Merges Settings",
        exportName: EXPORT_NAMES.settingsPage,
      },
    ],
  },
};

export default manifest;
