// src/manifest.ts
var PLUGIN_VERSION = "0.1.2";
var manifest = {
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
var manifest_default = manifest;
export {
  manifest_default as default
};
//# sourceMappingURL=manifest.js.map
