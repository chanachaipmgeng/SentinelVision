import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { KioskSession, TokenService } from './token.service';

const KIOSK: KioskSession = {
  deviceToken: 'dev-access',
  deviceRefreshToken: 'dev-refresh',
  deviceId: 'd1',
  companyId: 'c1',
  deviceName: 'Gate 1',
  locationId: null,
  expiresIn: 3600,
};

describe('TokenService', () => {
  let service: TokenService;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    TestBed.configureTestingModule({ providers: [TokenService, { provide: Router, useValue: router }] });
    service = TestBed.inject(TokenService);
  });

  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  describe('member session', () => {
    it('stores access and refresh tokens in localStorage', () => {
      service.saveToken('acc');
      service.saveRefreshToken('ref');
      expect(service.getToken()).toBe('acc');
      expect(service.getRefreshToken()).toBe('ref');
      expect(service.isKioskSession()).toBeFalse();
      expect(window.sessionStorage.length).toBe(0);
    });

    it('returns null tokens and an empty user when nothing is stored', () => {
      expect(service.getToken()).toBeNull();
      expect(service.getRefreshToken()).toBeNull();
      expect(service.getUser().access_token).toBe('');
      expect(service.getSelectCompany()).toBeTruthy();
    });

    it('keeps the cached user object in sync when the access token rotates', () => {
      service.saveUser({ access_token: 'old', token_type: 'bearer', member: { username: 'u' } });
      service.saveToken('new');
      expect(service.getUser().access_token).toBe('new');
      expect(service.getUser().member.username).toBe('u');
    });

    it('signOut clears everything and navigates to the login page', () => {
      service.saveToken('acc');
      service.saveRefreshToken('ref');
      service.saveUser({ access_token: 'acc' });
      service.signOut();
      expect(service.getToken()).toBeNull();
      expect(window.localStorage.length).toBe(0);
      expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
    });
  });

  describe('kiosk session', () => {
    it('lives in sessionStorage and wins over any member token', () => {
      service.saveToken('member-acc');
      service.saveRefreshToken('member-ref');
      service.saveKioskSession(KIOSK);
      expect(service.isKioskSession()).toBeTrue();
      expect(service.getToken()).toBe('dev-access');
      expect(service.getRefreshToken()).toBe('dev-refresh');
      // a kiosk tablet never also holds an admin session
      expect(window.localStorage.getItem('auth-token')).toBeNull();
      expect(window.localStorage.getItem('auth-refreshtoken')).toBeNull();
      expect(window.localStorage.getItem('auth-user')).toBeNull();
    });

    it('routes saveToken/saveRefreshToken to the kiosk session while paired', () => {
      service.saveKioskSession(KIOSK);
      service.saveToken('dev-access-2');
      expect(service.getToken()).toBe('dev-access-2');
      expect(service.getKioskSession()?.deviceRefreshToken).toBe('dev-refresh');
      service.saveRefreshToken('dev-refresh-2');
      expect(service.getRefreshToken()).toBe('dev-refresh-2');
      expect(service.getKioskSession()?.deviceToken).toBe('dev-access-2');
      expect(window.localStorage.getItem('auth-token')).toBeNull();
    });

    it('updateKioskTokens is a no-op without a session', () => {
      service.updateKioskTokens('x', 'y');
      expect(service.getKioskSession()).toBeNull();
      expect(service.getToken()).toBeNull();
    });

    it('drops a corrupted or token-less kiosk session', () => {
      window.sessionStorage.setItem('kiosk-session', '{not json');
      expect(service.getKioskSession()).toBeNull();
      expect(window.sessionStorage.getItem('kiosk-session')).toBeNull();
      window.sessionStorage.setItem('kiosk-session', JSON.stringify({ deviceId: 'd1' }));
      expect(service.getKioskSession()).toBeNull();
      expect(service.isKioskSession()).toBeFalse();
    });

    it('signOut from a kiosk session goes back to pairing', () => {
      service.saveKioskSession(KIOSK);
      service.signOut();
      expect(service.isKioskSession()).toBeFalse();
      expect(router.navigate).toHaveBeenCalledWith(['/kiosk/pair']);
    });

    it('clearKioskSession leaves member storage alone', () => {
      service.saveUserData(JSON.stringify({ username: 'u' }));
      service.saveKioskSession(KIOSK);
      service.clearKioskSession();
      expect(service.isKioskSession()).toBeFalse();
      expect(service.getUserData().username).toBe('u');
    });
  });
});
