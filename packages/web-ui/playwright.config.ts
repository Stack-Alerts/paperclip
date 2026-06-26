import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.001,
    },
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: process.env.CI
    ? {
        command: 'npm run start',
        url: 'http://localhost:3000',
        reuseExistingServer: false,
        timeout: 60_000,
      }
    : undefined,

  snapshotDir: './__snapshots__',
  // Default Playwright path: __snapshots__/<test-file-slug>/<arg>.png.
  // Lets each spec (status-bar, ai-recs-panel, …) keep its own snapshot folder.
  snapshotPathTemplate: '{snapshotDir}/{testFilePath}/{arg}{ext}',
});
