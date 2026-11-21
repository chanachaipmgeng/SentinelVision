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
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : [['list'], ['html', { open: 'never' }]],
  timeout: 45_000,
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    launchOptions: {
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
      ],
    },
    ...devices['Desktop Chrome'],
  },
});
