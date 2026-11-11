import { test, expect } from '@playwright/test';
import { buildKioskSession } from '../src/app/DPU/company-management/enroll-face/ws/kiosk-ws-client';

/**
 * Kiosk WebSocket handshake against a running gateway (default :8880).
 * Requires DPU_E2E_USER / DPU_E2E_PASSWORD (seed: admin / Password123!).
 * Does not open the camera or send face frames.
 */
test.describe('Kiosk WS session (:8880)', () => {
  test('session with JWT yields session_ok; other first message is refused', async ({
    request,
    page,
  }) => {
    const user = process.env.DPU_E2E_USER;
    const pass = process.env.DPU_E2E_PASSWORD;
    test.skip(!user || !pass, 'set DPU_E2E_USER and DPU_E2E_PASSWORD for kiosk session');

    const login = await request.post('/auth/login', {
      data: { username: user, password: pass },
    });
    expect(login.status(), `POST /auth/login → ${login.status()}`).toBe(200);
    const body = await login.json();
    const token: string = body.accessToken || body.access_token;
    const companyId: string =
      body.member?.companyId ||
      body.member?.company_id ||
      process.env.DPU_E2E_COMPANY_ID ||
      '11111111-1111-1111-1111-111111111111';
    expect(token, 'login must return an access token').toBeTruthy();

    const origin = new URL(page.url() === 'about:blank' ? (process.env.DPU_BASE_URL || 'http://localhost:8880') : page.url()).origin;
    const wsUrl = origin.replace(/^http/, 'ws') + '/face/ws/kiosk';

    // First message must be session — anything else closes with error.
    const refused = await page.evaluate(async (url) => {
      return await new Promise<{ type?: string; code?: string; closed: boolean }>((resolve, reject) => {
        const ws = new WebSocket(url);
        const timer = setTimeout(() => {
          ws.close();
          reject(new Error('timeout waiting for unauthenticated refusal'));
        }, 10_000);
        ws.onopen = () => ws.send(JSON.stringify({ type: 'ping' }));
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(String(ev.data));
            clearTimeout(timer);
            ws.close();
            resolve({ type: msg.type, code: msg.code, closed: true });
          } catch (err) {
            clearTimeout(timer);
            reject(err);
          }
        };
        ws.onerror = () => {
          clearTimeout(timer);
          reject(new Error('websocket error before refusal'));
        };
      });
    }, wsUrl);
    expect(refused.type).toBe('error');
    expect(refused.code).toMatch(/unauthenticated|invalid_session|auth_timeout/);

    // Authenticated session → session_ok.
    const sessionPayload = buildKioskSession({ companyId, token });
    const ok = await page.evaluate(
      async ({ url, payload }) => {
        return await new Promise<{ type?: string }>((resolve, reject) => {
          const ws = new WebSocket(url);
          const timer = setTimeout(() => {
            ws.close();
            reject(new Error('timeout waiting for session_ok'));
          }, 15_000);
          ws.onopen = () => ws.send(JSON.stringify(payload));
          ws.onmessage = (ev) => {
            try {
              const msg = JSON.parse(String(ev.data));
              clearTimeout(timer);
              ws.close();
              resolve({ type: msg.type });
            } catch (err) {
              clearTimeout(timer);
              reject(err);
            }
          };
          ws.onerror = () => {
            clearTimeout(timer);
            reject(new Error('websocket error before session_ok'));
          };
        });
      },
      { url: wsUrl, payload: sessionPayload },
    );
    expect(ok.type).toBe('session_ok');
  });
});
