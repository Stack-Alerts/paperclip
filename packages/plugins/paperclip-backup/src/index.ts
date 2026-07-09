// index.ts — entry point for the worker (esbuild picks this up)

export { default as manifest } from "./manifest.js";
export { pluginInstance as worker } from "./worker.js";
export { default } from "./worker.js";
