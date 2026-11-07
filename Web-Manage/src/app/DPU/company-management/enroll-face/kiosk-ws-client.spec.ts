import {
  KIOSK_WS_OPEN,
  buildKioskSession,
  canSendKioskFrame,
  kioskWsSessionAction,
} from './kiosk-ws-client';

describe('kiosk-ws-client', () => {
  describe('buildKioskSession', () => {
    it('always sends type/companyId/token', () => {
      expect(buildKioskSession({ companyId: 'c1', token: 'tok' })).toEqual({
        type: 'session',
        companyId: 'c1',
        token: 'tok',
      });
    });

    it('keeps a null token so the server can answer invalid_session explicitly', () => {
      expect(buildKioskSession({ companyId: 'c1', token: null })['token']).toBeNull();
    });

    it('only adds coordinates when both are present', () => {
      expect(buildKioskSession({ companyId: 'c1', token: 't', latitude: 13.7, longitude: 100.5 })).toEqual(
        jasmine.objectContaining({ latitude: 13.7, longitude: 100.5 }),
      );
      const half = buildKioskSession({ companyId: 'c1', token: 't', latitude: 13.7 });
      expect('latitude' in half).toBeFalse();
      expect('longitude' in half).toBeFalse();
    });

    it('treats 0 as a real coordinate (not missing)', () => {
      const zero = buildKioskSession({ companyId: 'c1', token: 't', latitude: 0, longitude: 0 });
      expect(zero['latitude']).toBe(0);
      expect(zero['longitude']).toBe(0);
    });
  });

  describe('kioskWsSessionAction', () => {
    it('acknowledges session_ok', () => {
      expect(kioskWsSessionAction({ type: 'session_ok' })).toBe('session_ok');
    });

    it('rotates on token_expiring', () => {
      expect(kioskWsSessionAction({ type: 'token_expiring' })).toBe('refresh_token');
    });

    it('flags invalid_session errors', () => {
      expect(kioskWsSessionAction({ type: 'error', code: 'invalid_session' })).toBe('invalid_session');
    });

    it('rotates on token_expired code or expired/revoked detail (no intent)', () => {
      expect(kioskWsSessionAction({ type: 'error', code: 'token_expired' })).toBe('refresh_token');
      expect(kioskWsSessionAction({ type: 'error', detail: 'Token has expired' })).toBe('refresh_token');
      expect(kioskWsSessionAction({ type: 'error', detail: 'Kiosk device token has been REVOKED' })).toBe(
        'refresh_token',
      );
    });

    it('ignores per-intent errors even when they mention expiry', () => {
      expect(kioskWsSessionAction({ type: 'error', intent: 'identify', detail: 'expired' })).toBe('none');
      expect(kioskWsSessionAction({ type: 'error', intent: 'detect' })).toBe('none');
    });

    it('ignores everything else and tolerates garbage', () => {
      expect(kioskWsSessionAction({ type: 'detected' })).toBe('none');
      expect(kioskWsSessionAction({ type: 'identified', memberId: 'x' })).toBe('none');
      expect(kioskWsSessionAction({ type: 'error', detail: 'no face found' })).toBe('none');
      expect(kioskWsSessionAction(null)).toBe('none');
      expect(kioskWsSessionAction(undefined)).toBe('none');
      expect(kioskWsSessionAction('session_ok')).toBe('none');
    });
  });

  describe('canSendKioskFrame', () => {
    it('refuses everything while the socket is not open', () => {
      expect(canSendKioskFrame('session', true, 0)).toBeFalse();
      expect(canSendKioskFrame('session', true, 3)).toBeFalse();
      expect(canSendKioskFrame('detect', true, null)).toBeFalse();
      expect(canSendKioskFrame('detect', true, undefined)).toBeFalse();
    });

    it('lets only `session` through before session_ok', () => {
      expect(canSendKioskFrame('session', false, KIOSK_WS_OPEN)).toBeTrue();
      expect(canSendKioskFrame('detect', false, KIOSK_WS_OPEN)).toBeFalse();
      expect(canSendKioskFrame('identify', false, KIOSK_WS_OPEN)).toBeFalse();
      expect(canSendKioskFrame(undefined, false, KIOSK_WS_OPEN)).toBeFalse();
    });

    it('lets every frame through after session_ok', () => {
      expect(canSendKioskFrame('detect', true, KIOSK_WS_OPEN)).toBeTrue();
      expect(canSendKioskFrame('checkin', true, KIOSK_WS_OPEN)).toBeTrue();
    });
  });
});
