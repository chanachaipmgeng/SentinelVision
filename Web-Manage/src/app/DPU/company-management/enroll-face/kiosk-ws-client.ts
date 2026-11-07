/**
 * Pure helpers for the kiosk WebSocket session handshake (`/face/ws/kiosk`).
 *
 * Protocol recap: the client must send `session` first; the server answers `session_ok` and only
 * then accepts detect/identify/checkin frames (anything earlier is refused and the socket is
 * closed with 1008). Token problems arrive either as `token_expiring` (proactive rotation) or as
 * `error` frames; both are handled by rotating the device token and re-sending `session`.
 */

/** WebSocket.OPEN without touching the global (keeps these helpers trivially unit-testable). */
export const KIOSK_WS_OPEN = 1;

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

export type KioskWsSessionAction =
  /** Server acknowledged `session`; detect/identify/checkin frames may flow. */
  | 'session_ok'
  /** Token is about to expire or was rejected as expired/revoked: rotate it, then re-send `session`. */
  | 'refresh_token'
  /** Server rejected the session itself and will close the socket; mark the session down and rotate. */
  | 'invalid_session'
  /** Not a session/token frame (detections, identify results, …). */
  | 'none';

/** Classify a server frame with respect to the session/token lifecycle. */
export function kioskWsSessionAction(msg: unknown): KioskWsSessionAction {
  const m = (msg ?? {}) as { type?: unknown; code?: unknown; intent?: unknown; detail?: unknown };
  if (m.type === 'session_ok') {
    return 'session_ok';
  }
  if (m.type === 'token_expiring') {
    return 'refresh_token';
  }
  if (m.type === 'error' && m.code === 'invalid_session') {
    return 'invalid_session';
  }
  if (m.type === 'error' && !m.intent) {
    const detail = String(m.detail || '');
    if (m.code === 'token_expired' || /expired|revoked/i.test(detail)) {
      return 'refresh_token';
    }
  }
  return 'none';
}

/**
 * Whether a frame may be written to the socket right now: the socket must be open and, except
 * for `session` itself, the server must already have acknowledged the session.
 */
export function canSendKioskFrame(
  payloadType: unknown,
  sessionOk: boolean,
  readyState: number | null | undefined,
): boolean {
  if (readyState !== KIOSK_WS_OPEN) {
    return false;
  }
  return payloadType === 'session' || sessionOk;
}
