// src/constants.ts
var PLUGIN_ID = "paperclip.pause";
var PLUGIN_VERSION = "0.1.0";
var PLUGIN_DISPLAY_NAME = "Pause / Run Agent Control";

// src/manifest.ts
var SIDEBAR_SLOT_ID = "pause-run-button";
var manifest = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: PLUGIN_DISPLAY_NAME,
  description: "System-wide Pause / Run toggle for the Paperclip agent fleet. When PAUSED: running agents continue their in-flight work but no new tasks are dispatched to any agent (paused_at is set fleet-wide). When RUN (default): normal heartbeat dispatch resumes. The toggle is exposed in the host top bar (to the right of the version badge) as a sidebar slot the host renders inline.",
  author: "Paperclip",
  categories: ["automation", "ui"],
  capabilities: [
    "ui.sidebar.register",
    "plugin.state.read",
    "plugin.state.write",
    "jobs.schedule"
  ],
  entrypoints: {
    ui: "./dist/ui",
    worker: "./dist/worker.js"
  },
  ui: {
    slots: [
      {
        id: SIDEBAR_SLOT_ID,
        type: "sidebar",
        exportName: "PauseRunButton",
        displayName: "Pause / Run"
      }
    ]
  }
};
var manifest_default = manifest;
export {
  manifest_default as default
};
