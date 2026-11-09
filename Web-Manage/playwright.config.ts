import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke against a running stack (default gateway :8880).
 *
 *   DPU_BASE_URL=http://localhost:8880 npm run test:e2e:smoke
 *
 * Optional live login: DPU_E2E_USER / DPU_E2E_PASSWORD (never commit these).
 */
const baseURL = process.env.DPU_BASE_URL || 'http://localhost:8880';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,
  use: {
    baseURL,
    trace: 'on-first-retry',
    ...devices['Desktop Chrome'],
  },
});
