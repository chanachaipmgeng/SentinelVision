/** Kiosk WebSocket session payload. */
export function buildKioskSession(opts: {
  companyId: string;
  token: string | null;
  latitude?: number;
  longitude?: number;
}): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    type: 'session',
    companyId: opts.companyId,
    token: opts.token,
  };
  if (opts.latitude != null && opts.longitude != null) {
    payload['latitude'] = opts.latitude;
    payload['longitude'] = opts.longitude;
  }
  return payload;
}
