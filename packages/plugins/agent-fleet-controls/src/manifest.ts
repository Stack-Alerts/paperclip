import type { PaperclipPluginManifestV1 } from "@paperclipai/plugin-sdk";

const PLUGIN_VERSION = "0.1.2";

const manifest: PaperclipPluginManifestV1 = {
  id: "paperclip-local.agent-fleet-controls",
  apiVersion: 1,
  version: PLUGIN_VERSION,
  displayName: "Agent Fleet Controls",
  description: "Compact global controls to pause and resume company agents in bulk.",
  author: "Paperclip Local",
  categories: ["ui"],
  capabilities: ["ui.action.register"],
  entrypoints: {
    worker: "./dist/worker.js",
    ui: "./dist/ui"
  },
  ui: {
    launchers: [
      {
        id: "agent-fleet-controls",
        displayName: "Agents",
        description: "Pause or resume all company agents with optional CEO and CTO exclusion.",
        placementZone: "globalToolbarButton",
        order: 100,
        action: {
          type: "openPopover",
          target: "AgentFleetControlsPopover"
        },
        render: {
          environment: "hostOverlay",
          bounds: "compact"
        }
      }
    ]
  }
};

export default manifest;
