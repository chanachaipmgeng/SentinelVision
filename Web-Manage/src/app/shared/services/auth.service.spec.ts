import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { AuthService, RefreshedTokens, SsoStart } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule], providers: [AuthService] });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
  });

  describe('login', () => {
    it('posts username/password and omits totpCode when blank', () => {
      service.login('alice', 'pw', '   ').subscribe();
      const req = http.expectOne('/auth/login');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ username: 'alice', password: 'pw' });
      req.flush({ accessToken: 'a', refreshToken: 'r' });
    });

    it('trims and forwards the TOTP code', () => {
      service.login('alice', 'pw', ' 123456 ').subscribe();
      const req = http.expectOne('/auth/login');
      expect(req.request.body.totpCode).toBe('123456');
      req.flush({});
    });
  });

  describe('logout / kiosk endpoints', () => {
    it('sends the refresh token and tolerates a missing one', () => {
      service.logout('ref').subscribe();
      expect(http.expectOne('/auth/logout').request.body).toEqual({ refreshToken: 'ref' });
      service.logout(null).subscribe();
      const second = http.expectOne('/auth/logout');
      expect(second.request.body.refreshToken).toBeUndefined();
    });

    it('kioskPair exchanges a pairing code', () => {
      service.kioskPair('ABCD-1234').subscribe((s) => expect(s.deviceToken).toBe('dt'));
      const req = http.expectOne('/auth/kiosk/pair');
      expect(req.request.body).toEqual({ pairingCode: 'ABCD-1234' });
      req.flush({ deviceToken: 'dt', deviceRefreshToken: 'dr', deviceId: 'd', companyId: 'c' });
    });
  });

  describe('refreshSession', () => {
    it('normalises a member refresh response', () => {
      let out: RefreshedTokens | undefined;
      service.refreshSession('ref', false).subscribe((t) => (out = t));
      const req = http.expectOne('/auth/refresh-token');
      expect(req.request.body).toEqual({ refreshToken: 'ref' });
      req.flush({ accessToken: 'A', refreshToken: 'R' });
      expect(out).toEqual({ accessToken: 'A', refreshToken: 'R' });
    });

    it('accepts legacy snake_case member fields', () => {
      let out: RefreshedTokens | undefined;
      service.refreshSession('ref', false).subscribe((t) => (out = t));
      http.expectOne('/auth/refresh-token').flush({ access_token: 'A2', refresh_token: 'R2' });
      expect(out).toEqual({ accessToken: 'A2', refreshToken: 'R2' });
    });

    it('normalises a kiosk refresh response', () => {
      let out: RefreshedTokens | undefined;
      service.refreshSession('dev-ref', true).subscribe((t) => (out = t));
      const req = http.expectOne('/auth/kiosk/refresh');
      expect(req.request.body).toEqual({ refreshToken: 'dev-ref' });
      req.flush({ deviceToken: 'DT', deviceRefreshToken: 'DR', deviceId: 'd', companyId: 'c' });
      expect(out).toEqual({ accessToken: 'DT', refreshToken: 'DR' });
    });

    it('is single-flight: concurrent callers share one HTTP request', () => {
      const results: RefreshedTokens[] = [];
      service.refreshSession('ref', true).subscribe((t) => results.push(t));
      service.refreshSession('ref', true).subscribe((t) => results.push(t));
      service.refreshSession('ref', true).subscribe((t) => results.push(t));
      const req = http.expectOne('/auth/kiosk/refresh');
      http.expectNone('/auth/refresh-token');
      req.flush({ deviceToken: 'DT', deviceRefreshToken: 'DR' });
      expect(results.length).toBe(3);
      expect(results.every((r) => r.accessToken === 'DT' && r.refreshToken === 'DR')).toBeTrue();
    });

    it('starts a new request once the previous one completed', () => {
      service.refreshSession('r1', false).subscribe();
      http.expectOne('/auth/refresh-token').flush({ accessToken: 'A', refreshToken: 'R' });
      service.refreshSession('r2', false).subscribe();
      const second = http.expectOne('/auth/refresh-token');
      expect(second.request.body).toEqual({ refreshToken: 'r2' });
      second.flush({ accessToken: 'A', refreshToken: 'R' });
    });

    it('propagates failures to every waiter and clears the in-flight slot', () => {
      const errors: number[] = [];
      service.refreshSession('r', false).subscribe({ error: (e) => errors.push(e.status) });
      service.refreshSession('r', false).subscribe({ error: (e) => errors.push(e.status) });
      http.expectOne('/auth/refresh-token').flush({ detail: 'reuse' }, { status: 401, statusText: 'Unauthorized' });
      expect(errors).toEqual([401, 401]);
      service.refreshSession('r', false).subscribe({ error: () => undefined });
      http.expectOne('/auth/refresh-token').flush({}, { status: 401, statusText: 'Unauthorized' });
    });
  });

  describe('SSO transaction', () => {
    const start: SsoStart = { authorizeUrl: 'https://idp/authorize', state: 's1', txn: 't1', expiresIn: 300 };

    it('round-trips state/txn through sessionStorage and is single-use', () => {
      service.saveSsoTransaction(start);
      expect(service.takeSsoTransaction()).toEqual({ state: 's1', txn: 't1' });
      expect(service.takeSsoTransaction()).toBeNull();
    });

    it('rejects incomplete or corrupt transactions', () => {
      sessionStorage.setItem('dpu-sso-txn', JSON.stringify({ state: 's1' }));
      expect(service.takeSsoTransaction()).toBeNull();
      sessionStorage.setItem('dpu-sso-txn', '{broken');
      expect(service.takeSsoTransaction()).toBeNull();
      expect(sessionStorage.getItem('dpu-sso-txn')).toBeNull();
    });

    it('ssoStart only sends the fields that are set', () => {
      service.ssoStart(undefined, '/dashboard').subscribe();
      expect(http.expectOne('/auth/sso/oidc/start').request.body).toEqual({ returnTo: '/dashboard' });
      service.ssoStart('c1').subscribe();
      expect(http.expectOne('/auth/sso/oidc/start').request.body).toEqual({ companyId: 'c1' });
    });
  });
});
