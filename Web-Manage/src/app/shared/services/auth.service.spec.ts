import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';

import { AuthService, RefreshedTokens, SsoStart } from './auth.service';
import { TokenService } from './token.service';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;
  let tokens: TokenService;

  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    TestBed.configureTestingModule({
    imports: [],
    providers: [
        AuthService,
        TokenService,
        { provide: Router, useValue: { navigate: () => undefined } },
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
    ]
});
    service = TestBed.inject(AuthService);
    tokens = TestBed.inject(TokenService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    sessionStorage.clear();
    localStorage.clear();
  });

  describe('login', () => {
    it('posts username/password and applies memory session without storing refresh', () => {
      service.login('alice', 'pw', '   ').subscribe();
      const req = http.expectOne('/auth/login');
      expect(req.request.method).toBe('POST');
      expect(req.request.withCredentials).toBeTrue();
      expect(req.request.body).toEqual({ username: 'alice', password: 'pw' });
      req.flush({
        accessToken: 'a',
        refreshToken: 'r',
        csrfToken: 'c',
        member: { username: 'alice', status: 1 },
      });
      expect(tokens.getToken()).toBe('a');
      expect(tokens.getCsrfToken()).toBe('c');
      expect(tokens.getRefreshToken()).toBeNull();
      expect(localStorage.getItem('auth-refreshtoken')).toBeNull();
    });

    it('trims and forwards the TOTP code', () => {
      service.login('alice', 'pw', ' 123456 ').subscribe();
      const req = http.expectOne('/auth/login');
      expect(req.request.body.totpCode).toBe('123456');
      req.flush({ accessToken: 'a', member: {} });
    });
  });

  describe('logout / kiosk endpoints', () => {
    it('sends CSRF and tolerates a missing refresh body', () => {
      tokens.saveCsrfToken('csrf-1');
      service.logout(null).subscribe();
      const req = http.expectOne('/auth/logout');
      expect(req.request.body.refreshToken).toBeUndefined();
      expect(req.request.withCredentials).toBeTrue();
      expect(req.request.headers.get('X-CSRF-Token')).toBe('csrf-1');
      req.flush({ ok: true });
    });

    it('kioskPair exchanges a pairing code', () => {
      service.kioskPair('ABCD-1234').subscribe((s) => expect(s.deviceToken).toBe('dt'));
      const req = http.expectOne('/auth/kiosk/pair');
      expect(req.request.body).toEqual({ pairingCode: 'ABCD-1234' });
      req.flush({ deviceToken: 'dt', deviceRefreshToken: 'dr', deviceId: 'd', companyId: 'c' });
    });
  });

  describe('refreshSession', () => {
    it('uses cookie+CSRF when no body refresh is provided', () => {
      tokens.saveCsrfToken('csrf-x');
      let out: RefreshedTokens | undefined;
      service.refreshSession(null, false).subscribe((t) => (out = t));
      const req = http.expectOne('/auth/refresh-token');
      expect(req.request.body).toEqual({});
      expect(req.request.headers.get('X-CSRF-Token')).toBe('csrf-x');
      req.flush({ accessToken: 'A', csrfToken: 'csrf-y' });
      expect(out?.accessToken).toBe('A');
      expect(tokens.getToken()).toBe('A');
      expect(tokens.getCsrfToken()).toBe('csrf-y');
    });

    it('normalises a member refresh response', () => {
      let out: RefreshedTokens | undefined;
      service.refreshSession('ref', false).subscribe((t) => (out = t));
      const req = http.expectOne('/auth/refresh-token');
      expect(req.request.body).toEqual({ refreshToken: 'ref' });
      req.flush({ accessToken: 'A', refreshToken: 'R' });
      expect(out).toEqual({ accessToken: 'A', refreshToken: 'R', csrfToken: undefined });
    });

    it('normalises a kiosk refresh response', () => {
      let out: RefreshedTokens | undefined;
      service.refreshSession('dev-ref', true).subscribe((t) => (out = t));
      const req = http.expectOne('/auth/kiosk/refresh');
      expect(req.request.body).toEqual({ refreshToken: 'dev-ref' });
      req.flush({ deviceToken: 'DT', deviceRefreshToken: 'DR', deviceId: 'd', companyId: 'c' });
      expect(out?.accessToken).toBe('DT');
      expect(out?.refreshToken).toBe('DR');
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

    it('does not expose register()', () => {
      expect((service as unknown).register).toBeUndefined();
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
