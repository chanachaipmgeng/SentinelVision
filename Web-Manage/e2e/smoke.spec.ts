import { test, expect } from '@playwright/test';

test('login page renders', async ({ page }) => {
  const base = process.env.DPU_BASE_URL || 'http://localhost/';
  await page.goto(base);
  await expect(page.locator('body')).toBeVisible();
});
