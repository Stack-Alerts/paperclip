/**
 * AI Recommendations Panel — visual-regression suite (BTCAAAAA-37781).
 *
 * Mounts the deterministic storybook harness at `/storybook/ai-recs` and
 * snapshots each of the three mockups at three viewport widths that map
 * to the board's "responsive review" check (1920 = desktop XL, 1440 =
 * desktop standard, 1280 = laptop narrow) plus a 1439 px wrap probe that
 * catches the row-vs-rail layout break point.
 *
 * Snapshot fixtures are byte-locked — toggle state is pinned to rec-2 in
 * the page itself; the e2e never mutates localStorage or the DOM, so a
 * regenerated snapshot under the same Chromium build should produce
 * identical bytes.
 *
 * Snapshots land in `__snapshots__/ai-recs-panel.spec.ts/` via the
 * {snapshotDir}/{testFilePath}/{arg}{ext} template (playwright.config.ts).
 */
import { test, expect } from '@playwright/test';

const STORYBOOK_URL = '/storybook/ai-recs';

// Width matrix — covers the acceptance criteria (1920/1440/1280) and the
// 1439 px wrap probe for the row-vs-rail layout.
const WIDTHS = [1920, 1440, 1439, 1280] as const;

for (const width of WIDTHS) {
  test.describe(`AI Recs Panel @ ${width}px`, () => {
    test.use({ viewport: { width, height: 1080 } });

    test(`mockup-1 — recommendation row (A3) matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-1"]', {
        timeout: 10_000,
      });
      // Sub-pixel stability: wait one frame after layout settles so the
      // card's internal SVGs/fonts are painted before we snap.
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-1"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-1-${width}.png`);
    });

    test(`mockup-2 — KPI bar (A2) + recommendation row matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-2"]', {
        timeout: 10_000,
      });
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-2"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-2-${width}.png`);
    });

    test(`mockup-3 — full layout (banner + row + right rail) matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-3"]', {
        timeout: 10_000,
      });
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-3"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-3-${width}.png`);
    });
  });
}

// Sprint B7 (BTCAAAAA-38568) — pixel-diff tests for mockups 4, 5, 6.
// mockup-4: AI Request tab (5 collapsible sections + copy buttons).
// mockup-5: AI Response tab (chip strip + MarkdownRenderer).
// mockup-6: History tab (HistoryView with snapshot KPIs).

const B7_WIDTHS = [1920, 1439] as const;

for (const width of B7_WIDTHS) {
  test.describe(`AI Recs Panel B7 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 1080 } });

    test(`mockup-4 — AI Request tab (B1) matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-4"]', { timeout: 10_000 });
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-4"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-4-${width}.png`);
    });

    test(`mockup-5 — AI Response tab chip strip + markdown (B2) matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-5"]', { timeout: 10_000 });
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-5"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-5-${width}.png`);
    });

    test(`mockup-6 — History tab with snapshot KPIs (B3) matches board mockup`, async ({
      page,
    }) => {
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-6"]', { timeout: 10_000 });
      await page.waitForTimeout(50);
      const section = page.locator('[data-testid="mockup-6"]');
      await expect(section).toBeVisible();
      await expect(section).toHaveScreenshot(`mockup-6-${width}.png`);
    });
  });
}

test.describe('AI Recs Panel B7 — structural invariants', () => {
  test('mockup-4 renders all 5 collapsible sections', async ({ page }) => {
    await page.goto(STORYBOOK_URL);
    await page.waitForSelector('[data-testid="mockup-4"]');
    const sections = page.locator('[data-testid="mockup-4"] [aria-expanded]');
    await expect(sections).toHaveCount(5);
  });

  test('mockup-5 renders provider, tokens, and latency chips', async ({ page }) => {
    await page.goto(STORYBOOK_URL);
    await page.waitForSelector('[data-testid="mockup-5"]');
    await expect(page.locator('[data-testid="ai-recs-chip-provider"]')).toBeVisible();
    await expect(page.locator('[data-testid="ai-recs-chip-tokens"]')).toBeVisible();
    await expect(page.locator('[data-testid="ai-recs-chip-latency"]')).toBeVisible();
  });

  test('mockup-6 renders all 3 history cards', async ({ page }) => {
    await page.goto(STORYBOOK_URL);
    await page.waitForSelector('[data-testid="mockup-6"]');
    const cards = page.locator('[data-testid="mockup-6"] [data-testid^="history-row-"]');
    await expect(cards).toHaveCount(3);
  });

  test('mockup-4 copy buttons all present at 1439px wrap boundary', async ({ page }) => {
    await page.setViewportSize({ width: 1439, height: 1080 });
    await page.goto(STORYBOOK_URL);
    await page.waitForSelector('[data-testid="mockup-4"]');
    const copyBtns = page.locator('[data-testid="mockup-4"] [data-testid^="collapsible-copy-"]');
    await expect(copyBtns).toHaveCount(5);
  });
});

/**
 * Acceptance probe — the recommendation row should always render exactly
 * five cards regardless of viewport (BTCAAAAA-37781 row contract), and
 * the row-vs-rail grid in mockup-3 should not clip the right rail's
 * "staged-from-prior" pill at the 1439 px wrap boundary.
 */
test.describe('AI Recs Panel — structural invariants', () => {
  test('recommendation row renders all 5 cards at every target viewport', async ({
    page,
  }) => {
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 1080 });
      await page.goto(STORYBOOK_URL);
      await page.waitForSelector('[data-testid="mockup-1"]');
      const cards = page.locator(
        '[data-testid="mockup-1"] [data-testid^="rec-card-"]',
      );
      await expect(cards).toHaveCount(5);
    }
  });

  test('mockup-3 right rail — staged-from-prior pill is fully visible at 1439 px wrap boundary', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1439, height: 1080 });
    await page.goto(STORYBOOK_URL);
    await page.waitForSelector('[data-testid="mockup-3"]');
    const rail = page.locator(
      '[data-testid="mockup-3"] [data-testid="after-changes-rail"]',
    );
    await expect(rail).toBeVisible();
    const stagedPill = rail.locator(
      '[data-status="staged-from-prior"]',
    );
    await expect(stagedPill).toBeVisible();
    // Verify the pill's right edge is within the rail's right edge —
    // catches horizontal overflow at the wrap breakpoint.
    const railBox = await rail.boundingBox();
    const pillBox = await stagedPill.first().boundingBox();
    expect(railBox).not.toBeNull();
    expect(pillBox).not.toBeNull();
    expect(pillBox!.x + pillBox!.width).toBeLessThanOrEqual(
      railBox!.x + railBox!.width + 1, // 1px tolerance for sub-pixel rounding
    );
  });
});
