#!/usr/bin/env node
// build-ui.mjs — bundle src/ui/index.tsx → dist/ui/index.js
//
// We compile the React UI source with esbuild so the plugin's UI bundle
// is fully reproducible from this worktree (no symlink dance with the
// upstream monorepo).

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(__dirname, "..");
const uiDir = path.join(pluginRoot, "dist", "ui");
const entryTsx = path.join(pluginRoot, "src", "ui", "index.tsx");
const entryTs = path.join(pluginRoot, "src", "ui", "index.ts");
const entryJsx = path.join(pluginRoot, "src", "ui", "index.jsx");
const outJs = path.join(uiDir, "index.js");

mkdirSync(uiDir, { recursive: true });

let entry = null;
for (const candidate of [entryTsx, entryTs, entryJsx]) {
  if (existsSync(candidate)) {
    entry = candidate;
    break;
  }
}

if (!entry) {
  console.error(`[build-ui] no UI entry found (looked for ${entryTsx}, ${entryTs}, ${entryJsx})`);
  process.exit(1);
}

const result = spawnSync(
  "pnpm",
  [
    "exec",
    "esbuild",
    entry,
    "--bundle",
    "--format=esm",
    "--target=es2020",
    "--jsx=automatic",
    "--loader:.tsx=tsx",
    "--loader:.ts=ts",
    "--loader:.js=js",
    "--external:@paperclipai/plugin-sdk/ui",
    "--external:react",
    "--external:react-dom",
    `--outfile=${outJs}`,
  ],
  { stdio: "inherit", cwd: pluginRoot },
);

if (result.status !== 0) {
  console.error(`[build-ui] esbuild failed (exit ${result.status})`);
  process.exit(result.status ?? 1);
}

console.log(`[build-ui] bundled ${path.relative(pluginRoot, entry)} → ${path.relative(pluginRoot, outJs)}`);
