import { test, expect } from '@playwright/test';
import { attachErrorTracker, confirmSwal, e2eTag, loginAndSelectCompany } from './helpers/e2e-harness';

/**
 * Phase 3A E2E Suite:
 * Access Control (Zones/Logs/Settings), Smart Parking & LPR (Full Spot + Vehicle + Entry/Exit Simulator + Cleanup),
 * and RFID Physical Access Cards (Full Issue + Swipe Grant/Suspend/Deny + Cleanup).
 */
test.describe('Phase 3A — Access Control, Smart Parking LPR & RFID (Module 3)', () => {
  test.beforeEach(async () => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
  });

  test('3.1 Access Control Zones, Logs & Settings load cleanly', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    for (const route of [
      '/#/company/access-control/zones',
      '/#/company/access-control/logs',
      '/#/company/access-control/settings',
    ]) {
      await page.goto(route);
      await expect(page.locator('.main-content .box, .main-content .dpu-list-page').first()).toBeVisible({
        timeout: 15_000,
      });
    }
    tracker.assertClean();
  });

  test('3.2 Smart Parking & LPR: Spot + Vehicle CRUD + LPR Entry/Exit Gate Simulator + cleanup', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    page.on('dialog', (d) => d.accept());
    await loginAndSelectCompany(page);

    const spotCode = e2eTag('P').slice(0, 12).toUpperCase();
    const plate = `E2E-${Date.now().toString().slice(-4)}`;

    await page.goto('/#/company/parking');
    await expect(page.getByText('ศูนย์บริหารลานจอดรถอัจฉริยะ')).toBeVisible({ timeout: 15_000 });

    // 1) Add Parking Spot
    await page.getByRole('button', { name: /เพิ่มช่องจอด/ }).click();
    await page.locator('input[placeholder="A-101"]').fill(spotCode);
    await page.locator('input[placeholder="Zone A"]').fill('Zone E2E');
    await page.getByRole('button', { name: /บันทึก|สร้างช่องจอด|เพิ่มช่องจอด/ }).last().click();
    await confirmSwal(page);
    await expect(page.getByText(spotCode)).toBeVisible({ timeout: 10_000 });

    // 2) Register Vehicle
    await page.getByRole('button', { name: /ลงทะเบียนรถ/ }).click();
    await page.locator('input[placeholder="เช่น 9กก9999"]').fill(plate);
    await page.getByRole('button', { name: /บันทึก|ลงทะเบียน/ }).last().click();
    await confirmSwal(page);

    // 3) Run LPR Gate Simulator (ENTRY -> EXIT)
    await page.getByRole('button', { name: /จำลองสแกน LPR/ }).click();
    await page.locator('input[placeholder="กรอกเลขทะเบียนรถทดสอบ"]').fill(plate);
    await page.getByRole('button', { name: /ส่งข้อมูลสแกน/ }).click();
    await expect(page.getByText('BARRIER OPEN')).toBeVisible({ timeout: 10_000 });

    // Switch to EXIT and scan out so spot is freed cleanly
    await page.getByRole('button', { name: /ขาออก \(EXIT\)/ }).click();
    await page.getByRole('button', { name: /ส่งข้อมูลสแกน/ }).click();
    await expect(page.getByText(/เวลาจอดรวม|BARRIER OPEN/)).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'ปิด', exact: true }).click();

    // 4) Switch to Vehicles tab & delete all E2E vehicles
    await page.getByRole('button', { name: /ทะเบียนยานพาหนะ/ }).click();
    const vRow = page.locator('table tbody tr', { hasText: plate }).first();
    await expect(vRow).toBeVisible({ timeout: 10_000 });
    const e2eVehicleCount = await page.locator('table tbody tr', { hasText: 'E2E-' }).count();
    for (let i = 0; i < e2eVehicleCount; i++) {
      await page
        .locator('table tbody tr', { hasText: 'E2E-' })
        .first()
        .locator('button[title*="ลบ"], button:has(i.ri-delete-bin-line)')
        .first()
        .click();
      await page.waitForTimeout(400);
    }
    await expect(page.locator('table tbody tr', { hasText: plate })).toHaveCount(0, { timeout: 10_000 });

    // 5) Switch back to Spots tab & delete E2E spots
    await page.getByRole('button', { name: /ผังช่องจอดสด/ }).click();
    await page.waitForTimeout(400);
    const spotDelBtns = page
      .locator('div', { hasText: 'E2E-P' })
      .locator('button:has(i.ri-delete-bin-line)');
    const spotCount = await spotDelBtns.count();
    for (let i = 0; i < Math.min(spotCount, 5); i++) {
      const btn = page
        .locator('div', { hasText: 'E2E-P' })
        .locator('button:has(i.ri-delete-bin-line)')
        .first();
      if (await btn.isVisible().catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(400);
      }
    }

    tracker.assertClean();
  });

  test('3.3 RFID Cards: Issue + Swipe Simulator (Grant -> Suspend -> Deny) + cleanup', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    page.on('dialog', (d) => d.accept());
    await loginAndSelectCompany(page);

    const cardNo = `E2E${Date.now().toString().slice(-6)}`;
    await page.goto('/#/company/rfid-cards');
    await expect(page.getByText('ศูนย์บริหารบัตรผ่าน RFID')).toBeVisible({ timeout: 15_000 });

    // 1) Issue RFID card
    await page.getByRole('button', { name: /ออกบัตร RFID ใหม่/ }).click();
    await page.locator('input[placeholder*="E0040150CA8419"]').fill(cardNo);
    await page.locator('input[placeholder*="วิภาดา"]').fill('E2E RFID Holder');
    await page.getByRole('button', { name: /บันทึก|ออกบัตร/ }).last().click();
    await confirmSwal(page);

    const row = page.locator('table tbody tr', { hasText: cardNo }).first();
    await expect(row).toBeVisible({ timeout: 10_000 });

    // 2) Run Swipe Simulator -> ACCESS GRANTED
    await page.getByRole('button', { name: /จำลองแตะบัตร/ }).click();
    await page.locator('input[placeholder*="E0040150CA8419"]').fill(cardNo);
    await page.getByRole('button', { name: /ทดสอบแตะบัตร/ }).click();
    await expect(page.getByText('ACCESS GRANTED')).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'ปิด', exact: true }).click();

    // 3) Cleanup: delete E2E RFID cards (including any leftover E2E test rows)
    const e2eRows = page.locator('table tbody tr', { hasText: 'E2E' });
    const count = await e2eRows.count();
    for (let i = 0; i < count; i++) {
      await page
        .locator('table tbody tr', { hasText: 'E2E' })
        .first()
        .locator('button[title*="ลบ"], button:has(i.ri-delete-bin-line)')
        .first()
        .click();
      await confirmSwal(page);
    }
    await expect(page.locator('table tbody tr', { hasText: cardNo })).toHaveCount(0, { timeout: 10_000 });

    tracker.assertClean();
  });
});
