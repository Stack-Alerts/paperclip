#!/usr/bin/env node
// build-ui.mjs — no-op stub for the paperclip-backup plugin.
//
// The plugin UI bundle (dist/ui/) is committed to the repo and not
// regenerated as part of the worker build. The UI source lives outside
// this package (in the upstream Paperclip monorepo's plugins workspace)
// and is symlinked/copied into dist/ui/ at install time by the host.
//
// This stub exists so `pnpm build` can complete end-to-end without
// failing on a missing module. It verifies dist/ui/ exists, ensures the
// directory layout matches the plugin manifest's `entrypoints.ui`
// (./dist/ui), and exits 0.

import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(__dirname, "..");
const uiDir = path.join(pluginRoot, "dist", "ui");

if (!existsSync(uiDir)) {
  console.warn(`[build-ui] WARNING: ${uiDir} does not exist — UI bundle missing.`);
  console.warn(`[build-ui]          The plugin will fail to register UI slots until the UI bundle is installed.`);
  console.warn(`[build-ui]          Run the upstream paperclip plugin UI build, or copy the prebuilt dist/ui/ directory back.`);
  // Create an empty dist/ui/ so the plugin manifest's entrypoints.ui
  // resolves. This avoids an immediate hard failure but will produce a
  // visible error in the UI ("module not found") if slots are registered.
  mkdirSync(uiDir, { recursive: true });
  process.exit(0);
}

const entries = readdirSync(uiDir);
if (entries.length === 0) {
  console.warn(`[build-ui] WARNING: ${uiDir} is empty.`);
  process.exit(0);
}

const hasIndexJs = entries.some((n) => n === "index.js");
const hasIndexJsx = entries.some((n) => n === "index.jsx");
if (!hasIndexJs && !hasIndexJsx) {
  console.warn(`[build-ui] WARNING: ${uiDir} has no index.js or index.jsx entry point.`);
}

console.log(`[build-ui] OK: dist/ui/ has ${entries.length} entries (no rebuild required).`);
process.exit(0);