/**
 * Build the kiosk WebSocket URL for `/face/ws/kiosk`.
 *
 * Uses `baseUrl` when set (prod nginx same-origin uses ''); otherwise falls back
 * to the current page origin. Always clears search/hash.
 */
export function buildKioskWsUrl(
  baseUrl: string,
  location: { protocol: string; host: string; origin: string } = window.location,
): string {
  const base = baseUrl || `${location.protocol}//${location.host}`;
  const url = new URL(base, location.origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/face/ws/kiosk';
  url.search = '';
  url.hash = '';
  return url.toString();
}

/** pace.js strips WebSocket.OPEN — compare readyState to these literals. */
export const WS_CONNECTING = 0;
export const WS_OPEN = 1;
