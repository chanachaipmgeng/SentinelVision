import { Injectable } from "@angular/core";
import { Router } from "@angular/router";

import { UserModel } from "../user-auth.model";
import { UserProfileModel } from "../../DPU/models/user.model";
import { CompanyModel } from "../../DPU/models/company.model";

const TOKEN_KEY = 'auth-token';
const REFRESHTOKEN_KEY = 'auth-refreshtoken';
const USER_KEY = 'auth-user';
const USER_DATA_KEY = 'auth-user-data';
const COMPANY = 'company';
const CSRF_COOKIE = 'dpu_csrf';
/** Kiosk device session lives in sessionStorage (per tab, never in a URL). */
const KIOSK_SESSION_KEY = 'kiosk-session';

export interface KioskSession {
  deviceToken: string;
  deviceRefreshToken: string;
  deviceId: string;
  companyId: string;
  deviceName?: string;
  locationId?: string | null;
  expiresIn?: number;
}

@Injectable({
  providedIn: "root",
})
export class TokenService {
  /** Member access token stays in memory only (E4) — never persisted to localStorage. */
  private accessTokenMemory: string | null = null;
  private csrfTokenMemory: string | null = null;

  constructor(private router: Router) {
    // Drop legacy persisted member tokens from earlier builds.
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
  }

  /** Clear every credential and go back to the right entry point (login or kiosk pairing). */
  signOut(): void {
    const wasKiosk = this.isKioskSession();
    this.clearSession();
    this.router.navigate([wasKiosk ? '/kiosk/pair' : '/auth/login']);
  }

  /** Drop all stored credentials without navigating (used by logout flows). */
  clearSession(): void {
    this.accessTokenMemory = null;
    this.csrfTokenMemory = null;
    window.sessionStorage.removeItem(KIOSK_SESSION_KEY);
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    window.localStorage.removeItem(USER_DATA_KEY);
    window.localStorage.removeItem(COMPANY);
  }

  // ---------------------------------------------------------------------------
  // Kiosk device session (one-time pairing code → device-scoped token pair)
  // ---------------------------------------------------------------------------
  public isKioskSession(): boolean {
    return !!this.getKioskSession();
  }

  public getKioskSession(): KioskSession | null {
    const raw = window.sessionStorage.getItem(KIOSK_SESSION_KEY);
    if (!raw) {
      return null;
    }
    try {
      const parsed = JSON.parse(raw) as KioskSession;
      return parsed?.deviceToken ? parsed : null;
    } catch {
      window.sessionStorage.removeItem(KIOSK_SESSION_KEY);
      return null;
    }
  }

  public saveKioskSession(session: KioskSession): void {
    // A kiosk tablet never also holds an admin session.
    this.accessTokenMemory = null;
    this.csrfTokenMemory = null;
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    window.sessionStorage.setItem(KIOSK_SESSION_KEY, JSON.stringify(session));
  }

  public updateKioskTokens(deviceToken: string, deviceRefreshToken?: string): void {
    const session = this.getKioskSession();
    if (!session) {
      return;
    }
    session.deviceToken = deviceToken;
    if (deviceRefreshToken) {
      session.deviceRefreshToken = deviceRefreshToken;
    }
    window.sessionStorage.setItem(KIOSK_SESSION_KEY, JSON.stringify(session));
  }

  public clearKioskSession(): void {
    window.sessionStorage.removeItem(KIOSK_SESSION_KEY);
  }

  // ---------------------------------------------------------------------------
  // Member (admin) session — access in memory; refresh via httpOnly cookie
  // ---------------------------------------------------------------------------
  public saveToken(token: string): void {
    if (this.isKioskSession()) {
      this.updateKioskTokens(token);
      return;
    }
    this.accessTokenMemory = token || null;
    window.localStorage.removeItem(TOKEN_KEY);
    const user = this.getUser();
    if (user.access_token) {
      this.saveUser({ ...user, access_token: token, accessToken: token });
    }
  }

  public getUser(): UserModel {
    const user = window.localStorage.getItem(USER_KEY);
    if (user) {
      return JSON.parse(user);
    }

    return new UserModel();
  }

  /** Bearer credential for the current session: kiosk device token or member access token. */
  public getToken(): string | null {
    const kiosk = this.getKioskSession();
    if (kiosk) {
      return kiosk.deviceToken;
    }
    return this.accessTokenMemory;
  }

  /**
   * Member refresh lives in an httpOnly cookie — returns null for browser sessions.
   * Kiosk still keeps a refresh token in sessionStorage.
   */
  public saveRefreshToken(token: string): void {
    if (this.isKioskSession()) {
      this.updateKioskTokens(this.getKioskSession()!.deviceToken, token);
      return;
    }
    // Intentionally not persisted (E4 httpOnly cookie owns the refresh token).
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
  }

  public getRefreshToken(): string | null {
    const kiosk = this.getKioskSession();
    if (kiosk) {
      return kiosk.deviceRefreshToken || null;
    }
    return null;
  }

  public saveCsrfToken(token: string | null | undefined): void {
    this.csrfTokenMemory = (token || '').trim() || null;
  }

  public getCsrfToken(): string | null {
    if (this.csrfTokenMemory) {
      return this.csrfTokenMemory;
    }
    return this.readCookie(CSRF_COOKIE);
  }

  public saveUser(user: any): void {
    // Never persist refresh/access tokens inside the cached user blob.
    const safe = { ...user };
    delete safe.refreshToken;
    delete safe.refresh_token;
    if (safe.accessToken) {
      this.accessTokenMemory = safe.accessToken;
    } else if (safe.access_token) {
      this.accessTokenMemory = safe.access_token;
    }
    delete safe.accessToken;
    delete safe.access_token;
    if (safe.csrfToken) {
      this.saveCsrfToken(safe.csrfToken);
      delete safe.csrfToken;
    }
    window.localStorage.removeItem(USER_KEY);
    window.localStorage.setItem(USER_KEY, JSON.stringify(safe));
  }

  public saveUserData(user: string): void {
    window.localStorage.removeItem(USER_DATA_KEY);
    window.localStorage.setItem(USER_DATA_KEY, user);
  }

  public getUserData(): UserProfileModel {
    const user = window.localStorage.getItem(USER_DATA_KEY);
    if (user) {
      return new UserProfileModel(JSON.parse(user));
    }

    return new UserProfileModel();
  }

  public saveSelectCompany(company: CompanyModel): void {
    window.localStorage.removeItem(COMPANY);
    window.localStorage.setItem(COMPANY, JSON.stringify(new CompanyModel(company)));
  }

  public getSelectCompany(): CompanyModel {
    const company = window.localStorage.getItem(COMPANY);
    if (company) {
      return new CompanyModel(JSON.parse(company));
    }
    return new CompanyModel();
  }

  private readCookie(name: string): string | null {
    if (typeof document === 'undefined') {
      return null;
    }
    const parts = document.cookie.split(';');
    for (const part of parts) {
      const [k, ...rest] = part.trim().split('=');
      if (k === name) {
        return decodeURIComponent(rest.join('=')) || null;
      }
    }
    return null;
  }

}
