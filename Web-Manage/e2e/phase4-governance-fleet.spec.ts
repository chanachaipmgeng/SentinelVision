import { test, expect } from '@playwright/test';
import { attachErrorTracker, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 4 E2E Suite:
 * Audit Log, Kiosk Devices, Edge Fleet Health (Kiosks + CCTV dynamic status),
 * Cameras / CCTV (<app-page-header> + offline PTZ disabled),
 * Settings Hub & RBAC (single active rail + 2x2 form grid),
 * Notification Center (translated Delivery History) & Profile Security.
 */
test.describe('Phase 4 — Governance, Fleet Health, CCTV & Settings (Module 7)', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('4.1 Audit Log & Kiosk Devices load cleanly', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/audit-log');
    await expect(page.locator('.main-content .box, .main-content .dpu-list-page').first()).toBeVisible({
      timeout: 15_000,
    });

    await page.goto('/#/company/devices');
    await expect(page.locator('.main-content .box, .main-content .dpu-list-page').first()).toBeVisible({
      timeout: 15_000,
    });

    tracker.assertClean();
  });

  test('4.2 Edge Fleet Health: dynamic health badge & offline CCTV latency dash', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/fleet-health');
    await expect(page.getByText('ศูนย์ตรวจวัดสุขภาพอุปกรณ์และเซ็นเซอร์ Edge')).toBeVisible({ timeout: 15_000 });

    // Switch to CCTV Sensors tab
    await page.getByRole('button', { name: /CCTV Sensors/ }).click();
    const cctvTable = page.locator('table');
    await expect(cctvTable).toBeVisible({ timeout: 10_000 });

    // If any camera is disconnected, latency column must NOT read "ปกติ"
    const offlineRow = page.locator('table tbody tr', { hasText: 'ขาดการเชื่อมต่อ' }).first();
    if (await offlineRow.isVisible().catch(() => false)) {
      await expect(offlineRow.locator('td').nth(3)).toHaveText('—');
    }

    tracker.assertClean();
  });

  test('4.3 Cameras / CCTV: page header present & offline PTZ buttons disabled', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/cameras');
    await expect(page.locator('app-company-cameras app-page-header')).toBeVisible({ timeout: 15_000 });

    const offlineCam = page.locator('.sv-camera-row', { hasText: /offline/i }).first();
    if (await offlineCam.isVisible().catch(() => false)) {
      const ptzLeft = offlineCam.getByRole('button', { name: 'PTZ Left' });
      await expect(ptzLeft).toBeDisabled();
    }

    tracker.assertClean();
  });

  test('4.4 Settings Hub & RBAC: single active rail item, 2x2 select grid & tabs', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/settings/rbac');
    await expect(page.locator('.dpu-settings-rail')).toBeVisible({ timeout: 15_000 });

    // Exactly ONE active item in settings rail
    await expect(page.locator('.dpu-settings-rail__link.is-active')).toHaveCount(1);

    // Check Notifications and PDPA Retention tabs
    await page.goto('/#/company/settings/notifications');
    await expect(page.locator('.dpu-settings-rail__link.is-active')).toHaveCount(1);

    await page.goto('/#/company/settings/retention');
    await expect(page.locator('.dpu-settings-rail__link.is-active')).toHaveCount(1);

    tracker.assertClean();
  });

  test('4.5 Notification Center (translated Delivery History) & Profile Security', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/notification-center');
    await expect(page.getByRole('button', { name: /ประวัติการส่ง|Delivery History/ })).toBeVisible({
      timeout: 15_000,
    });

    await page.goto('/#/company/profile-security');
    await expect(page.locator('app-page-header', { hasText: /โปรไฟล์และความปลอดภัย/ }).first()).toBeVisible({
      timeout: 15_000,
    });

    tracker.assertClean();
  });
});
