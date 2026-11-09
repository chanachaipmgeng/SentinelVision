import { test, expect } from '@playwright/test';

/**
 * Login + health smoke against the nginx gateway (default :8880).
 * Requires a running stack for health + login page; optional credentials for a real sign-in.
 */
test.describe('DPU smoke (:8880)', () => {
  test('GET /health returns ok', async ({ request }) => {
    const res = await request.get('/health');
    expect(res.status(), `GET /health → ${res.status()}`).toBe(200);
    const body = await res.text();
    // nginx /health is plain "ok" or JSON from the API depending on route; accept either shape.
    expect(body.length).toBeGreaterThan(0);
  });

  test('login page shows username / password form', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.locator('#signin-username')).toBeVisible();
    await expect(page.locator('#signin-password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.getByRole('heading', { name: /SentinelVision/i })).toBeVisible();
  });

  test('live login reaches an authenticated shell', async ({ page }) => {
    const user = process.env.DPU_E2E_USER;
    const pass = process.env.DPU_E2E_PASSWORD;
    test.skip(!user || !pass, 'set DPU_E2E_USER and DPU_E2E_PASSWORD for live login');

    await page.goto('/auth/login');
    await page.locator('#signin-username').fill(user!);
    await page.locator('#signin-password').fill(pass!);
    await page.locator('button[type="submit"]').click();

    // Company admin → company home; super-admin (role 99) → /admin/member-manage.
    await expect(page).toHaveURL(/\/(company|admin)\//, { timeout: 20_000 });
  });
});
