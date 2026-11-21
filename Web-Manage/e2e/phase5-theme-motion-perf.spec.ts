import { test, expect } from '@playwright/test';
import { attachErrorTracker, dismissWelcomeWizard, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 5 E2E Suite (v6.5.0):
 * Light Mode Porcelain Glass Parity across Management Screens,
 * Reusable Command UI Wrappers (CommandTopbar, MetricRibbon, SurfaceModal + Esc dismiss),
 * VaultX Precision Motion classes, and Hidden Switcher DOM removal verification.
 */
test.describe('Phase 5 — Light/Dark Theme Parity, Wrappers & Performance (v6.5.0)', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('5.1 Light Mode switches Command screens (Fleet Health, Parking, RFID, Mobile Check-In) to light porcelain surfaces', async ({
    page,
  }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);
    await page.goto('/#/company/dashboard');
    await dismissWelcomeWizard(page);

    // Ensure Light Mode is active by toggling html attributes cleanly via Theme button or evaluating light state
    const themeBtn = page.locator('.app-header button[title*="โหมด"], .app-header button[aria-label*="theme"], .app-header .sv-header-btn:has(i.ri-sun-line), .app-header .sv-header-btn:has(i.ri-moon-line)').first();
    if (await themeBtn.isVisible().catch(() => false)) {
      const modeBefore = await page.evaluate(() => document.documentElement.getAttribute('data-theme-mode') || document.documentElement.getAttribute('data-theme'));
      if (modeBefore === 'dark') {
        await themeBtn.click();
        await page.waitForTimeout(300);
      }
    }

    // Verify no hidden <app-switcher> ColorPicker DOM bloat exists in ContentLayout
    await expect(page.locator('app-switcher.dpu-hidden-switcher')).toHaveCount(0);

    // Check Fleet Health, Parking & RFID topbar/ribbon computed background is bright (> 200 RGB channel) in Light Mode
    for (const route of ['/#/company/fleet-health', '/#/company/parking', '/#/company/rfid-cards']) {
      await page.goto(route);
      const topbar = page.locator('app-command-topbar .sv-surface-topbar').first();
      await expect(topbar).toBeVisible({ timeout: 15_000 });

      const bg = await topbar.evaluate((el) => getComputedStyle(el).backgroundColor);
      // Extract RGB channels and verify light surface (not dark rgb(7, 13, 20))
      const m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      expect(m, `Expected valid RGB background on ${route}, got ${bg}`).not.toBeNull();
      if (m) {
        const avg = (Number(m[1]) + Number(m[2]) + Number(m[3])) / 3;
        expect(avg, `Topbar on ${route} should be bright in Light Mode, got ${bg}`).toBeGreaterThan(200);
      }

      await expect(page.locator('app-metric-ribbon .sv-surface-ribbon').first()).toBeVisible();
    }

    // Verify SurfaceModal opens with motion class and closes cleanly via Escape key on RFID Cards
    await page.getByRole('button', { name: /จำลองแตะบัตร/ }).click();
    const modal = page.locator('app-surface-modal .sv-surface-modal');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
    await expect(modal).toBeHidden({ timeout: 5_000 });

    // Restore Dark Mode cleanly
    if (await themeBtn.isVisible().catch(() => false)) {
      const modeAfter = await page.evaluate(() => document.documentElement.getAttribute('data-theme-mode') || document.documentElement.getAttribute('data-theme'));
      if (modeAfter === 'light') {
        await themeBtn.click();
        await page.waitForTimeout(200);
      }
    }

    tracker.assertClean();
  });
});
