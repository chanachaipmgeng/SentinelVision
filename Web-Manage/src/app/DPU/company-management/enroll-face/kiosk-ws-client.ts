/**
 * Pure helpers for the kiosk WebSocket session handshake (`/face/ws/kiosk`).
 *
 * Protocol recap: the client must send `session` first; the server answers `session_ok` and only
 * then accepts detect/identify/checkin frames (anything earlier is refused and the socket is
 * closed with 1008). Token problems arrive either as `token_expiring` (proactive rotation) or as
 * `error` frames; both are handled by rotating the device token and re-sending `session`.
 *
 * Phase 3: session (and checkin) may carry `stationMode`, `zoneId`, `eventId` for modular scanners.
 */

/** WebSocket.OPEN without touching the global (keeps these helpers trivially unit-testable). */
export const KIOSK_WS_OPEN = 1;

export interface KioskSessionOpts {
  companyId: string;
  token: string | null;
  latitude?: number;
  longitude?: number;
  stationMode?: string | null;
  zoneId?: string | null;
  eventId?: string | null;
}

/** Kiosk WebSocket session payload. */
export function buildKioskSession(opts: KioskSessionOpts): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    type: 'session',
    companyId: opts.companyId,
    token: opts.token,
  };
  if (opts.latitude != null && opts.longitude != null) {
    payload['latitude'] = opts.latitude;
    payload['longitude'] = opts.longitude;
  }
  if (opts.stationMode) {
    payload['stationMode'] = opts.stationMode;
  }
  if (opts.zoneId) {
    payload['zoneId'] = opts.zoneId;
  }
  if (opts.eventId) {
    payload['eventId'] = opts.eventId;
  }
  return payload;
}

/** Optional modular fields merged into a `checkin` frame. */
export function buildKioskCheckinExtras(opts: {
  stationMode?: string | null;
  zoneId?: string | null;
  eventId?: string | null;
  enableDoorRelay?: boolean;
  totpOrPin?: string | null;
}): Record<string, unknown> {
  const extras: Record<string, unknown> = {};
  if (opts.stationMode) {
    extras['stationMode'] = opts.stationMode;
  }
  if (opts.zoneId) {
    extras['zoneId'] = opts.zoneId;
  }
  if (opts.eventId) {
    extras['eventId'] = opts.eventId;
  }
  if (opts.enableDoorRelay) {
    extras['enableDoorRelay'] = true;
  }
  if (opts.totpOrPin) {
    extras['totpOrPin'] = opts.totpOrPin;
  }
  return extras;
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
