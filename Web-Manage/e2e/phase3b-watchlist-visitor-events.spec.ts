import { test, expect } from '@playwright/test';
import { attachErrorTracker, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 3B E2E Suite:
 * Watchlist (Identities, Incidents, Settings), Emergency Muster Roll,
 * Visitors (Passes, Settings), and Smart Events (Campaigns, Check-ins, Settings).
 */
test.describe('Phase 3B — Watchlist, Visitors & Smart Events (Modules 4, 5, 6)', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('3.4 Watchlist (Identities, Incidents, Settings) & Emergency Muster Roll load cleanly', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    for (const route of [
      '/#/company/sentinel-center',
      '/#/company/watchlist/identities',
      '/#/company/watchlist/incidents',
      '/#/company/watchlist/settings',
      '/#/company/visitors/muster-roll',
    ]) {
      await page.goto(route);
      await expect(page.locator('.main-content .box, .main-content .dpu-list-page').first()).toBeVisible({
        timeout: 15_000,
      });
    }
    tracker.assertClean();
  });

  test('3.5 Visitors (Passes & Settings) & Smart Events (Campaigns, Check-ins, Settings) load cleanly', async ({
    page,
  }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    for (const route of [
      '/#/company/visitors/passes',
      '/#/company/visitors/settings',
      '/#/company/events/campaigns',
      '/#/company/events/checkins',
      '/#/company/events/settings',
    ]) {
      await page.goto(route);
      await expect(page.locator('.main-content .box, .main-content .dpu-list-page').first()).toBeVisible({
        timeout: 15_000,
      });
    }
    tracker.assertClean();
  });
});
