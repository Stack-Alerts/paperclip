// esbuild.config.mjs
// Build config for @frenocorp/trade-lifecycle-hooks

import * as esbuild from "esbuild";

const isWatch = process.argv.includes("--watch");

/** @type {import("esbuild").BuildOptions} */
const config = {
  entryPoints: ["src/manifest.ts", "src/worker.ts"],
  bundle: true,
  platform: "node",
  target: "node20",
  format: "esm",
  outdir: "dist",
  sourcemap: true,
  external: [
    "@paperclipai/plugin-sdk",
    "@paperclipai/shared",
    "pg",
  ],
  logLevel: "info",
};

if (isWatch) {
  const ctx = await esbuild.context(config);
  await ctx.watch();
  console.log("[plugin] Watching for changes...");
} else {
  await esbuild.build(config);
  console.log("[plugin] Build complete.");
}
