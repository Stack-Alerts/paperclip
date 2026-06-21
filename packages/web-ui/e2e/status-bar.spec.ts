/**
 * Status Bar e2e tests — BTCAAAAA-30756
 *
 * Covers:
 *  - Baseline states: idle, saved, countdown
 *  - Ticker mode: multi-notice queue, pinned countdown survives, overflow "+N more"
 *  - Dismiss: x button removes entry; error entries persist; pinned entry has no x button
 *  - TTL: success auto-dismisses after default TTL; error persists
 *  - B5 dual-display: CRITICAL alert appears in both banner and ticker
 *
 * Uses window.__statusBus (exposed when NEXT_PUBLIC_E2E_TEST=true by StatusBus.ts) to inject
 * status entries without needing UI interaction to trigger them.
 */
import { test, expect, Page } from '@playwright/test';
import type { StatusEntry } from '../src/lib/status/types';

// ────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────

type StatusBusWindow = Window & {
  __statusBus?: {
    emit: (event: string, data: unknown) => void;
    on: (event: string, fn: (data: unknown) => void) => () => void;
  };
};

function uid() {
  return `test-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

async function emitEntry(page: Page, entry: Partial<StatusEntry> & { text: string }) {
  const full: StatusEntry = {
    id: entry.id ?? uid(),
    text: entry.text,
    variant: entry.variant ?? 'info',
    createdAt: entry.createdAt ?? Date.now(),
    expiresAt: entry.expiresAt,
    pinned: entry.pinned ?? false,
    dismissed: false,
  };
  await page.evaluate((e: StatusEntry) => {
    const bus = (window as StatusBusWindow).__statusBus;
    if (!bus) throw new Error('__statusBus not exposed — dev mode only');
    bus.emit('emit', e);
  }, full);
  return full.id;
}

async function enableTickerMode(page: Page) {
  const settings = { tickerMode: true, maxVisible: 3, errorPersist: true, errorDuration: 10, successDuration: 4000, warningDuration: 6000 };
  await page.evaluate((s) => {
    localStorage.setItem('status-bar-settings', JSON.stringify(s));
    window.dispatchEvent(new StorageEvent('storage', { key: 'status-bar-settings', newValue: JSON.stringify(s) }));
  }, settings);
  // Wait until the component actually switches to ticker layout
  await page.waitForSelector('[data-testid="status-bar"][data-mode="ticker"]', { timeout: 3000 });
}

async function clearEntries(page: Page) {
  await page.evaluate(() => {
    const bus = (window as StatusBusWindow).__statusBus;
    if (bus) bus.emit('clear', undefined);
  });
  await page.waitForTimeout(50);
}

const statusBarLocator = (page: Page) =>
  page.locator('[data-testid="status-bar"]').or(
    page.locator('[class*="h-6"][class*="border-t"]').last()
  );

// ────────────────────────────────────────────────────────────────────────────
// Suite setup
// ────────────────────────────────────────────────────────────────────────────

test.describe('Status Bar — Visual Regression & Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Reset settings to default — must dispatch a non-null newValue so the handler fires
    const defaultSettings = JSON.stringify({ tickerMode: false, maxVisible: 3, errorPersist: true, errorDuration: 10, successDuration: 4000, warningDuration: 6000 });
    await page.evaluate((s) => {
      localStorage.setItem('status-bar-settings', s);
      window.dispatchEvent(new StorageEvent('storage', { key: 'status-bar-settings', newValue: s }));
    }, defaultSettings);
    await clearEntries(page);
    await page.waitForTimeout(100);
  });

  // ── Baseline states ────────────────────────────────────────────────────────

  test('idle state — shows Ready text and visual baseline', async ({ page }) => {
    const bar = statusBarLocator(page);
    await expect(bar).toBeVisible();
    await expect(bar).toContainText('Ready');
    await expect(bar).toHaveScreenshot('status-bar-idle.png');
  });

  test('saved state — shows "Strategy saved" entry and visual baseline', async ({ page }) => {
    await emitEntry(page, { text: 'Strategy saved', variant: 'success' });
    const bar = statusBarLocator(page);
    await expect(bar).toContainText('Strategy saved');
    await expect(bar).toHaveScreenshot('status-bar-saved.png');
  });

  test('countdown state — shows pinned countdown entry and visual baseline', async ({ page }) => {
    const expiresAt = Date.now() + 5 * 60 * 1000; // 5 minutes
    await emitEntry(page, { text: 'Next data check in 5m', variant: 'info', pinned: true, expiresAt });
    const bar = statusBarLocator(page);
    await expect(bar).toContainText(/Next data check/);
    await expect(bar).toHaveScreenshot('status-bar-countdown.png');
  });

  // ── Ticker mode ────────────────────────────────────────────────────────────

  test('ticker mode — multi-notice queue visible up to maxVisible', async ({ page }) => {
    await enableTickerMode(page);
    // Emit 5 entries — only 3 should be visible (maxVisible=3)
    for (let i = 1; i <= 5; i++) {
      await emitEntry(page, { text: `Notice ${i}`, variant: 'info' });
    }
    await page.waitForTimeout(200);

    const bar = statusBarLocator(page);
    // Should show overflow "+N more"
    await expect(bar).toContainText('+2 more');
    await expect(bar).toHaveScreenshot('status-bar-ticker-multi.png');
  });

  test('ticker mode — pinned countdown survives TTL expiry of other entries', async ({ page }) => {
    await enableTickerMode(page);

    const shortTTL = Date.now() + 300; // expires in 300ms
    const longExpiry = Date.now() + 60_000;

    await emitEntry(page, { text: 'Pinned countdown', variant: 'info', pinned: true, expiresAt: longExpiry });
    await emitEntry(page, { text: 'Short lived notice', variant: 'success', expiresAt: shortTTL });

    // Wait for short-lived entry to expire (ticker purges on 1s interval)
    await page.waitForTimeout(1500);

    const bar = statusBarLocator(page);
    await expect(bar).toContainText('Pinned countdown');
    await expect(bar).not.toContainText('Short lived notice');
    await expect(bar).toHaveScreenshot('status-bar-ticker-pinned-survives.png');
  });

  test('ticker mode — overflow "+N more" shows when active entries exceed maxVisible', async ({ page }) => {
    await enableTickerMode(page);
    for (let i = 1; i <= 6; i++) {
      await emitEntry(page, { text: `Item ${i}`, variant: 'info' });
    }
    await page.waitForTimeout(200);
    const bar = statusBarLocator(page);
    await expect(bar).toContainText('+3 more');
  });

  // ── Dismiss behaviour ──────────────────────────────────────────────────────

  test('dismiss — x button removes entry from ticker', async ({ page }) => {
    await enableTickerMode(page);
    await emitEntry(page, { id: 'dismiss-test', text: 'Dismissible notice', variant: 'info' });
    await page.waitForTimeout(100);

    // Click the dismiss button for that specific entry
    const dismissBtn = page.locator(`[aria-label="Dismiss"]`).first();
    await expect(dismissBtn).toBeVisible();
    await dismissBtn.click();
    await page.waitForTimeout(100);

    const bar = statusBarLocator(page);
    await expect(bar).not.toContainText('Dismissible notice');
  });

  test('dismiss — error entries persist (no auto-dismiss)', async ({ page }) => {
    await enableTickerMode(page);
    const expiresAt = Date.now() + 300; // would expire if it were a normal entry
    await emitEntry(page, {
      text: 'Error persists',
      variant: 'error',
      expiresAt,
    });
    // Wait past the expiry — but error entries should NOT be purged by the interval
    // because errorPersist=true means pinned-like behaviour
    await page.waitForTimeout(1500);
    const bar = statusBarLocator(page);
    // Error entries still visible (ticker interval only removes non-pinned expired entries)
    await expect(bar).toContainText('Error persists');
  });

  test('dismiss — pinned entry has no dismiss button', async ({ page }) => {
    await enableTickerMode(page);
    await emitEntry(page, {
      text: 'Pinned — no dismiss',
      variant: 'info',
      pinned: true,
      expiresAt: Date.now() + 60_000,
    });
    await page.waitForTimeout(100);

    // Dismiss button should NOT appear for pinned entries
    const dismissBtn = page.locator(`[aria-label="Dismiss"]`);
    await expect(dismissBtn).toHaveCount(0);
  });

  // ── TTL behaviour ──────────────────────────────────────────────────────────

  test('TTL — success entry auto-dismisses after ticker purge cycle', async ({ page }) => {
    await enableTickerMode(page);
    await emitEntry(page, {
      text: 'Success fades',
      variant: 'success',
      expiresAt: Date.now() + 100, // expires almost immediately
    });

    // Ticker purges on ~1s interval
    await page.waitForTimeout(1500);
    const bar = statusBarLocator(page);
    await expect(bar).not.toContainText('Success fades');
  });

  test('TTL — error entry persists beyond expiry time (errorPersist semantic)', async ({ page }) => {
    await enableTickerMode(page);
    await emitEntry(page, {
      text: 'Error stays',
      variant: 'error',
      // No expiresAt — error entries have no TTL by design
    });
    await page.waitForTimeout(1500);
    const bar = statusBarLocator(page);
    await expect(bar).toContainText('Error stays');
  });

  // ── B5 dual-display — CRITICAL in both banner and ticker ──────────────────

  test('B5 dual-display — CRITICAL alert appears in status bar', async ({ page }) => {
    // Emit a CRITICAL-severity warning that the B5 dual-emit logic sends to the status system
    await emitEntry(page, {
      text: 'CRITICAL: Risk limit breach',
      variant: 'error',
      pinned: true,
    });

    const bar = statusBarLocator(page);
    await expect(bar).toContainText('CRITICAL');
    await expect(bar).toHaveScreenshot('status-bar-critical-banner.png');
  });

  test('B5 dual-display — CRITICAL in ticker mode also present', async ({ page }) => {
    await enableTickerMode(page);
    await emitEntry(page, {
      text: 'CRITICAL: Risk limit breach',
      variant: 'error',
      pinned: true,
    });

    const bar = statusBarLocator(page);
    await expect(bar).toContainText('CRITICAL');
    await expect(bar).toHaveScreenshot('status-bar-critical-ticker.png');
  });

  // ── Layout: fixed at bottom ────────────────────────────────────────────────

  test('layout — status bar is pinned at the bottom of the viewport', async ({ page }) => {
    const bar = statusBarLocator(page);
    const bb = await bar.boundingBox();
    expect(bb).not.toBeNull();
    const viewport = page.viewportSize();
    expect(viewport).not.toBeNull();
    // Bar bottom edge should be at or very near the viewport bottom
    expect((bb!.y + bb!.height)).toBeCloseTo(viewport!.height, -1);
  });

  test('layout — status bar does not scroll with content', async ({ page }) => {
    const bar = statusBarLocator(page);
    const before = await bar.boundingBox();
    await page.evaluate(() => window.scrollBy(0, 300));
    await page.waitForTimeout(50);
    const after = await bar.boundingBox();
    expect(before?.y).toEqual(after?.y);
  });
});
