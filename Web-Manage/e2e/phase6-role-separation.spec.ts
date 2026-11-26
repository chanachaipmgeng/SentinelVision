import { test, expect } from '@playwright/test';
import { attachErrorTracker, dismissWelcomeWizard, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 6 E2E Suite:
 * Strict Role & Console Separation between System Admin (/admin/*) and Company Console (/company/*).
 */
test.describe('Phase 6 — System Admin vs. Company Admin Role Separation', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('6.1 System Admin Platform Infrastructure (/admin/infrastructure) loads live GPU & schema telemetry', async ({
    page,
  }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/admin/infrastructure');
    await expect(page.getByText('ศูนย์ควบคุมโครงสร้างพื้นฐานแพลตฟอร์ม')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('HEALTHY')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/cuda:0|CPU/)).toBeVisible();

    tracker.assertClean();
  });

  test('6.2 System Admin Context Banner appears in Company Console and returns cleanly to Admin Console', async ({
    page,
  }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/dashboard');
    await dismissWelcomeWizard(page);
    const banner = page.locator('.sv-sysadmin-banner');
    await expect(banner).toBeVisible({ timeout: 15_000 });
    await expect(banner).toContainText(/กำลังดูในสิทธิ์ผู้ดูแลระบบสูงสุด|Viewing as System Admin|โหมด System Admin/);

    await banner
      .getByRole('button', { name: /กลับภาพรวมแพลตฟอร์ม|Back to Platform Overview|กลับ System Admin Console/ })
      .click();
    await expect(page).toHaveURL(/\/#\/admin\/manage-companys/, { timeout: 10_000 });

    tracker.assertClean();
  });

  test('6.3 Company RBAC (/company/settings/rbac) excludes SYSTEM_ADMIN role from tenant scope', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/settings/rbac');
    await expect(page.locator('.dpu-settings-rail')).toBeVisible({ timeout: 15_000 });

    // SYSTEM_ADMIN must NOT be exposed inside a Company's RBAC role options or permission matrix
    const roleOptions = await page.locator('app-rbac-management-panel select').nth(1).locator('option').allTextContents();
    expect(roleOptions.some((t) => t.includes('SYSTEM_ADMIN'))).toBe(false);

    tracker.assertClean();
  });
});
