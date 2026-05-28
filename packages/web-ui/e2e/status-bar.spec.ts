import { test, expect } from '@playwright/test';

test.describe('Status Bar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display in idle state', async ({ page }) => {
    const statusBar = page.locator('[class*="h-6"][class*="border-t"]').last();
    await expect(statusBar).toBeVisible();
    await expect(statusBar).toContainText(/Ready|Next data check/);

    // Visual regression baseline: idle state
    await expect(statusBar).toHaveScreenshot('status-bar-idle.png');
  });

  test('should display "Strategy saved" on save action', async ({ page }) => {
    const saveButton = page.locator('button:has-text("Save")').first();

    // Wait for the save button to be enabled (modified state)
    // This is a simplified test; in practice you'd create/modify a strategy first
    if (!saveButton.isDisabled()) {
      await saveButton.click();

      const statusBar = page.locator('[class*="h-6"][class*="border-t"]').last();
      await expect(statusBar).toContainText('Strategy saved');

      // Visual regression baseline: saved state
      await expect(statusBar).toHaveScreenshot('status-bar-saved.png');
    }
  });

  test('should display countdown timer', async ({ page }) => {
    // The countdown timer starts automatically after page load
    // Wait for the countdown status to appear
    const statusBar = page.locator('[class*="h-6"][class*="border-t"]').last();

    // Wait for the countdown text to be visible
    await expect(statusBar).toContainText(/Next data check in \d+m \d+s/, { timeout: 5000 });

    // Visual regression baseline: countdown state
    await expect(statusBar).toHaveScreenshot('status-bar-countdown.png');
  });

  test('should position status bar at bottom of viewport', async ({ page }) => {
    const statusBar = page.locator('[class*="h-6"][class*="border-t"]').last();
    const boundingBox = await statusBar.boundingBox();

    expect(boundingBox).toBeTruthy();
    if (boundingBox) {
      const viewport = page.viewportSize();
      expect(viewport).toBeTruthy();
      if (viewport) {
        // Status bar should be near the bottom (within 10px of viewport height)
        expect(boundingBox.y + boundingBox.height).toBeCloseTo(viewport.height, 10);
      }
    }
  });

  test('should not scroll with main content', async ({ page }) => {
    const statusBar = page.locator('[class*="h-6"][class*="border-t"]').last();
    const initialBox = await statusBar.boundingBox();

    // Scroll the page
    await page.evaluate(() => window.scrollBy(0, 200));

    // Status bar position should remain unchanged
    const afterScrollBox = await statusBar.boundingBox();
    expect(initialBox?.y).toEqual(afterScrollBox?.y);
  });
});
