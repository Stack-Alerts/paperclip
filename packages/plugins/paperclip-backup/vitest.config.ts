import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.spec.ts"],
    environment: "node",
    testTimeout: 30_000, // 30s — the cleanup walk runs real rclone calls and can be slow
  },
});
