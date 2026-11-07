import { Injectable } from "@angular/core";
import { Router } from "@angular/router";

import { jwtDecode } from "jwt-decode";
import { ProfileModel, UserModel } from "../user-auth.model";
import { UserProfileModel } from "../../DPU/models/user.model";
import { CompanyModel } from "../../DPU/models/company.model";
// import jwt_decode from "jwt-decode";

const TOKEN_KEY = 'auth-token';
const REFRESHTOKEN_KEY = 'auth-refreshtoken';
const USER_KEY = 'auth-user';
const USER_DATA_KEY = 'auth-user-data';
const COMPANY = 'company';
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
  constructor(private router: Router) { }

  /** Clear every credential and go back to the right entry point (login or kiosk pairing). */
  signOut(): void {
    const wasKiosk = this.isKioskSession();
    this.clearSession();
    this.router.navigate([wasKiosk ? '/kiosk/pair' : '/auth/login']);
  }

  /** Drop all stored credentials without navigating (used by logout flows). */
  clearSession(): void {
    window.sessionStorage.removeItem(KIOSK_SESSION_KEY);
    window.localStorage.clear();
    localStorage.clear();
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
  // Member (admin) session
  // ---------------------------------------------------------------------------
  public saveToken(token: string): void {
    if (this.isKioskSession()) {
      this.updateKioskTokens(token);
      return;
    }
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.setItem(TOKEN_KEY, token);

    const user = this.getUser();
    if (user.access_token) {
      this.saveUser({ ...user, access_token: token });
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
    return window.localStorage.getItem(TOKEN_KEY);
  }

  public saveRefreshToken(token: string): void {
    if (this.isKioskSession()) {
      this.updateKioskTokens(this.getKioskSession()!.deviceToken, token);
      return;
    }
    window.localStorage.removeItem(REFRESHTOKEN_KEY);
    window.localStorage.setItem(REFRESHTOKEN_KEY, token);
  }

  public getRefreshToken(): string | null {
    const kiosk = this.getKioskSession();
    if (kiosk) {
      return kiosk.deviceRefreshToken || null;
    }
    return window.localStorage.getItem(REFRESHTOKEN_KEY);
  }

  public saveUser(user: any): void {
    window.localStorage.removeItem(USER_KEY);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  public saveUserData(user: string): void {
    window.localStorage.removeItem(USER_DATA_KEY);
    window.localStorage.setItem(USER_DATA_KEY, user);
  }

  public getUserData(): UserProfileModel {
    // return window.localStorage.getItem(USER_DATA_KEY);
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

}
