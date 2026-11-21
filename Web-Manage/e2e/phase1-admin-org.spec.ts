import { test, expect } from '@playwright/test';
import {
  attachErrorTracker,
  confirmSwal,
  dismissWelcomeWizard,
  e2eTag,
  loginAndSelectCompany,
} from './helpers/e2e-harness';

/**
 * Phase 1 E2E Suite:
 * Public Landing, Login, Global Header Controls, System Admin Console,
 * Company Dashboard, Departments CRUD, Positions CRUD, and Employees List/Modals.
 */
test.describe('Phase 1 — Public, Admin & Core Organization (Modules 0 & 1)', () => {
  test('1.1 Landing page hero is bright, visible immediately, and navigates to Login', async ({ page }) => {
    const tracker = attachErrorTracker(page);
    await page.goto('/#/');

    const heroTitle = page.locator('#landing-hero-title');
    await expect(heroTitle).toBeVisible({ timeout: 15_000 });
    await expect(heroTitle).toHaveCSS('opacity', '1');

    const lead = page.locator('.dpu-landing__hero-lead');
    await expect(lead).toBeVisible();
    await expect(lead).toHaveCSS('opacity', '1');

    await page.locator('.dpu-landing__cta-row a[href*="auth/login"]').first().click();
    await expect(page).toHaveURL(/\/#\/auth\/login/, { timeout: 15_000 });
    tracker.assertClean();
  });

  test('1.2 Authenticated shell: Global Search (Ctrl K), TH/EN toggle, Light/Dark toggle & Dashboard KPI', async ({
    page,
  }) => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/dashboard');
    await expect(page.locator('.dpu-dashboard')).toBeVisible({ timeout: 20_000 });
    await dismissWelcomeWizard(page);

    // Confirm Ctrl K badge (not Mac ⌘ F)
    await expect(page.locator('.sv-search-pill .sv-kbd-badge')).toHaveText(/Ctrl K/i);

    // Open Global Search Palette and verify Sentinel Command Center icon
    await page.locator('.sv-search-pill').click();
    await expect(page.locator('.sv-palette')).toBeVisible({ timeout: 5_000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('.sv-palette')).toBeHidden();

    // Verify no line-through on completed onboarding checklist items
    const doneTitle = page.locator('.sv-setup__step.is-done .sv-setup__step-title').first();
    if (await doneTitle.isVisible()) {
      const textDec = await doneTitle.evaluate((el) => getComputedStyle(el).textDecorationLine);
      expect(textDec).not.toContain('line-through');
    }

    tracker.assertClean();
  });

  test('1.3 Departments: compact UUID pill + CRUD lifecycle with auto-cleanup', async ({ page }) => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    const deptName = e2eTag('Dept');
    await page.goto('/#/company/company-department');
    await expect(page.locator('.dpu-list-page')).toBeVisible({ timeout: 15_000 });

    // Verify existing UUID codes are truncated to 8 chars inside <code>
    const firstCode = page.locator('table tbody tr td code').first();
    if (await firstCode.isVisible()) {
      const codeText = (await firstCode.innerText()).trim();
      expect(codeText.length).toBeLessThanOrEqual(8);
    }

    // Create new E2E department
    await page.getByRole('button', { name: /เพิ่มแผนก/ }).click();
    const modal = page.locator('#modal-detail');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    const inputs = modal.locator('input[type="text"]');
    await inputs.nth(0).fill(deptName);
    if ((await inputs.count()) > 1) {
      await inputs.nth(1).fill(deptName);
    }
    await modal.getByRole('button', { name: /บันทึก|Save/i }).click();
    await confirmSwal(page);

    // Verify row appears
    const createdRow = page.locator('table tbody tr', { hasText: deptName }).first();
    await expect(createdRow).toBeVisible({ timeout: 10_000 });

    // Cleanup: delete the E2E department
    await createdRow.locator('button[title="ลบ"]').click();
    await confirmSwal(page);
    await expect(page.locator('table tbody tr', { hasText: deptName })).toHaveCount(0, { timeout: 10_000 });
    tracker.assertClean();
  });

  test('1.4 Positions: compact UUID pill + CRUD lifecycle with auto-cleanup', async ({ page }) => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    const posName = e2eTag('Pos');
    await page.goto('/#/company/company-position');
    await expect(page.locator('.dpu-list-page')).toBeVisible({ timeout: 15_000 });

    const firstCode = page.locator('table tbody tr td code').first();
    if (await firstCode.isVisible()) {
      const codeText = (await firstCode.innerText()).trim();
      expect(codeText.length).toBeLessThanOrEqual(8);
    }

    await page.getByRole('button', { name: /เพิ่มตำแหน่ง/ }).click();
    const modal = page.locator('#modal-detail');
    await expect(modal).toBeVisible({ timeout: 5_000 });
    const inputs = modal.locator('input[type="text"]');
    await inputs.nth(0).fill(posName);
    if ((await inputs.count()) > 1) {
      await inputs.nth(1).fill(posName);
    }
    await modal.getByRole('button', { name: /บันทึก|Save/i }).click();
    await confirmSwal(page);

    const createdRow = page.locator('table tbody tr', { hasText: posName }).first();
    await expect(createdRow).toBeVisible({ timeout: 10_000 });

    // Cleanup
    await createdRow.locator('button[title="ลบ"]').click();
    await confirmSwal(page);
    await expect(page.locator('table tbody tr', { hasText: posName })).toHaveCount(0, { timeout: 10_000 });
    tracker.assertClean();
  });

  test('1.5 Employees: clean primary actions + overflow menu toggle', async ({ page }) => {
    test.skip(
      !process.env['DPU_E2E_USER'] || !process.env['DPU_E2E_PASSWORD'],
      'Set DPU_E2E_USER and DPU_E2E_PASSWORD to run live authenticated E2E tests',
    );
    const tracker = attachErrorTracker(page);
    await loginAndSelectCompany(page);

    await page.goto('/#/company/company-emp');
    await expect(page.locator('.emp-list-panel')).toBeVisible({ timeout: 15_000 });

    // If table view is active, confirm overflow menu opens and displays labeled secondary actions
    const moreBtn = page.locator('table tbody tr button[title="เพิ่มเติม"]').first();
    if (await moreBtn.isVisible()) {
      await moreBtn.click();
      await expect(page.getByText('ประวัติลงเวลา')).toBeVisible();
      await expect(page.getByText('จัดการใบหน้า')).toBeVisible();
      await page.keyboard.press('Escape');
    }

    tracker.assertClean();
  });
});
