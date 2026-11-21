import { expect, Page } from '@playwright/test';

export interface ErrorTracker {
  pageErrors: string[];
  consoleErrors: string[];
  httpErrors: string[];
  assertClean: () => void;
}

/**
 * Generates a deterministic E2E-prefixed name so test data is easy to identify and clean up.
 */
export function e2eTag(label: string): string {
  const short = Date.now().toString(36).slice(-5);
  return `E2E-${label}-${short}`;
}

/**
 * Attaches listeners to capture uncaught page errors, console errors, and unexpected HTTP 4xx/5xx responses.
 */
export function attachErrorTracker(page: Page): ErrorTracker {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const httpErrors: string[] = [];

  page.on('pageerror', (err) => {
    pageErrors.push(err.message || String(err));
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const txt = msg.text();
      // Ignore benign third-party tile/font load hiccups in offline sandboxes
      if (txt.includes('tile.openstreetmap.org') || txt.includes('fonts.gstatic.com')) {
        return;
      }
      consoleErrors.push(txt);
    }
  });

  page.on('response', (res) => {
    const status = res.status();
    const url = res.url();
    if (status >= 400 && url.startsWith('http://localhost')) {
      httpErrors.push(`${res.request().method()} ${status} ${url}`);
    }
  });

  return {
    pageErrors,
    consoleErrors,
    httpErrors,
    assertClean: () => {
      expect(pageErrors, `Uncaught page errors: ${pageErrors.join(' | ')}`).toEqual([]);
      expect(httpErrors, `Unexpected HTTP 4xx/5xx: ${httpErrors.join(' | ')}`).toEqual([]);
    },
  };
}

/**
 * Dismisses the first-visit Welcome Wizard overlay if present.
 */
export async function dismissWelcomeWizard(page: Page): Promise<void> {
  const wizard = page.locator('.sv-welcome-backdrop');
  if (await wizard.isVisible({ timeout: 2_000 }).catch(() => false)) {
    const closeBtn = wizard.locator('button').first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await wizard.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => undefined);
  }
}

/**
 * Clicks through SweetAlert v1 confirmation and follow-up success dialogs cleanly.
 */
export async function confirmSwal(page: Page): Promise<void> {
  const btn = page.locator('.swal-button--confirm');
  if (await btn.isVisible({ timeout: 4_000 }).catch(() => false)) {
    await btn.click();
    await page.waitForTimeout(300);
  }
  // Dismiss follow-up "สำเร็จ" alert if shown
  if (await btn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await btn.click();
    await page.waitForTimeout(200);
  }
}

/**
 * Signs in via /#/auth/login using DPU_E2E_USER / DPU_E2E_PASSWORD and selects the target company (default: DPUATT).
 */
export async function loginAndSelectCompany(
  page: Page,
  companyCode = process.env['DPU_E2E_COMPANY'] || 'DPUATT',
): Promise<{ token: string; companyId: string }> {
  const user = process.env['DPU_E2E_USER'];
  const pass = process.env['DPU_E2E_PASSWORD'];
  if (!user || !pass) {
    throw new Error('Set DPU_E2E_USER and DPU_E2E_PASSWORD to run authenticated E2E tests.');
  }

  await page.goto('/#/auth/login');
  await expect(page.locator('#signin-username')).toBeVisible({ timeout: 20_000 });
  await page.locator('#signin-username').fill(user);
  await page.locator('#signin-password').fill(pass);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/(company|admin)\//, { timeout: 20_000 });

  // If landed on /admin/*, navigate to company management and enter the target company console.
  if (page.url().includes('/admin/')) {
    await page.goto('/#/admin/manage-companys');
    const companyRow = page.locator('table tbody tr', { hasText: companyCode }).first();
    await expect(companyRow).toBeVisible({ timeout: 15_000 });
    await companyRow.locator('a').first().click();
    await expect(page).toHaveURL(/\/company\//, { timeout: 15_000 });
  }

  const creds = await page.evaluate(() => {
    const token =
      localStorage.getItem('access_token') ||
      localStorage.getItem('token') ||
      sessionStorage.getItem('access_token') ||
      '';
    let companyId = '';
    try {
      const raw = localStorage.getItem('selectCompany') || localStorage.getItem('selectedCompany') || '';
      if (raw) {
        const parsed = JSON.parse(raw);
        companyId = parsed?.companyId || '';
      }
    } catch {
      // ignore parse errors
    }
    return { token, companyId };
  });

  return creds;
}
