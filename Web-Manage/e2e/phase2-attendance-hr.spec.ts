import { test, expect } from '@playwright/test';
import { attachErrorTracker, confirmSwal, e2eTag, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 2 E2E Suite:
 * Attendance Timestamps, Warning Approvals, Approval Inbox, Reports,
 * Self-Service (0 HTTP 404), Mobile Check-In, GPS Locations,
 * HR Schedule (Shifts/Leaves/Holidays CRUD + cleanup), and Face Scan Kiosk PDPA.
 */
test.describe('Phase 2 — Attendance, HR Schedule & Face Kiosk (Module 2)', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('2.1 Timestamp Log, Warning Timestamp Log & Approval Inbox load cleanly', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/timestamp-log');
    await expect(page.locator('.dpu-list-page')).toBeVisible({ timeout: 15_000 });

    await page.goto('/#/company/warning-timestamp-log');
    await expect(page.locator('.main-content .dpu-list-page, .main-content .box').first()).toBeVisible({
      timeout: 15_000,
    });

    await page.goto('/#/company/approval-inbox');
    await expect(page.locator('.main-content .inbox-page, .main-content .box').first()).toBeVisible({
      timeout: 15_000,
    });

    tracker.assertClean();
  });

  test('2.2 Attendance Reports, Self-Service (0 HTTP 404) & Mobile Check-In upload UX', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/reports');
    await expect(page.locator('.main-content .dpu-list-page, .main-content .box').first()).toBeVisible({
      timeout: 15_000,
    });

    // Self-Service must NOT trigger HTTP 404 for System Admin
    await page.goto('/#/company/self-service');
    await expect(page.locator('.dpu-ess-page')).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1000);

    // Mobile Check-In styled upload button
    await page.goto('/#/company/mobile-checkin');
    await expect(page.getByText(/ถ่ายภาพ \/ เลือกไฟล์รูปภาพ/)).toBeVisible({ timeout: 15_000 });

    tracker.assertClean();
  });

  test('2.3 GPS Locations & HR Schedule (Shifts, Leaves, Holidays CRUD + cleanup)', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/company-location');
    await expect(page.locator('.main-content .dpu-list-page, .main-content .box').first()).toBeVisible({
      timeout: 15_000,
    });

    await page.goto('/#/company/hr-schedule/shifts');
    await expect(page.locator('.main-content .box').first()).toBeVisible({ timeout: 15_000 });

    await page.goto('/#/company/hr-schedule/leaves');
    await expect(page.locator('.main-content .box').first()).toBeVisible({ timeout: 15_000 });

    // Holidays: open side-drawer, verify styled CSV/iCal upload button + Create & Delete E2E holiday
    const holidayName = e2eTag('Holiday');
    await page.goto('/#/company/hr-schedule/holidays');
    await expect(page.locator('.sv-subpanel__group').first()).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: /\+ เพิ่มวันหยุด \/ นำเข้า/ }).click();
    await expect(page.getByText(/เลือกไฟล์ CSV \/ iCal/)).toBeVisible({ timeout: 10_000 });

    await page.locator('input[type="date"]').first().fill('2026-12-29');
    await page.locator('input[placeholder*="วันสงกรานต์"]').fill(holidayName);
    await page.getByRole('button', { name: /\+ เพิ่มวันหยุดบริษัท/ }).click();
    await confirmSwal(page);

    const row = page.locator('table tbody tr', { hasText: holidayName }).first();
    await expect(row).toBeVisible({ timeout: 10_000 });

    // Cleanup
    await row.getByRole('button', { name: 'ลบ' }).click();
    await confirmSwal(page);
    await expect(page.locator('table tbody tr', { hasText: holidayName })).toHaveCount(0, { timeout: 10_000 });

    tracker.assertClean();
  });

  test('2.4 Face Scan Kiosk (/company/scan/attendance) displays PDPA consent cleanly', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/scan/attendance');
    await expect(page.locator('.dpu-kiosk, [data-station-mode="ATTENDANCE"]').first()).toBeVisible({
      timeout: 20_000,
    });
    // PDPA consent modal or active kiosk view should appear cleanly
    await page.waitForTimeout(1000);
    tracker.assertClean();
  });
});
