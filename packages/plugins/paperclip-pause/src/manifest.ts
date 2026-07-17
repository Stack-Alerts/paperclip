// manifest.ts — paperclip-pause plugin manifest
//
// Capabilities match exactly what the plugin's data providers, action
// handlers, and jobs actually use. The host validates this list at install
// time and refuses to load the plugin if it asks for capabilities it
// didn't declare.

import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";
import { PLUGIN_DISPLAY_NAME, PLUGIN_ID, PLUGIN_VERSION } from "./constants.js";

const SIDEBAR_SLOT_ID = "pause-run-button";

const manifest: PaperclipPluginManifestV1 = {
  id: PLUGIN_ID,
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: PLUGIN_DISPLAY_NAME,
  description:
    "System-wide Pause / Run toggle for the Paperclip agent fleet. " +
    "When PAUSED: running agents continue their in-flight work but no " +
    "new tasks are dispatched to any agent (paused_at is set fleet-wide). " +
    "When RUN (default): normal heartbeat dispatch resumes. " +
    "The toggle is exposed in the host top bar (to the right of the version " +
    "badge) as a sidebar slot the host renders inline.",
  author: "Paperclip",
  categories: ["automation", "ui"],
  capabilities: [
    "ui.sidebar.register",
    "plugin.state.read",
    "plugin.state.write",
    "jobs.schedule",
  ],
  entrypoints: {
    ui: "./dist/ui",
    worker: "./dist/worker.js",
  },
  ui: {
    slots: [
      {
        id: SIDEBAR_SLOT_ID,
        type: "sidebar",
        exportName: "PauseRunButton",
        displayName: "Pause / Run",
      },
    ],
  },
};

export default manifest;
