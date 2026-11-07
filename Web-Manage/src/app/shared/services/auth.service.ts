import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ProfileModel, UserModel } from '../user-auth.model';

const SSO_TXN_KEY = 'dpu-sso-txn';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  apiBaseUrl = "/auth";
  constructor(
    private http: HttpClient,
  ) {
  }

  login(username: string, password: string, totpCode?: string) {
    const body: any = {
      username: username,
      password: password,
    };
    if (totpCode && totpCode.trim()) {
      body.totpCode = totpCode.trim();
    }
    return this.http.post<UserModel>(this.apiBaseUrl + '/login', body);
  }

  refreshToken(token: string) {
    return this.http.post<any>(this.apiBaseUrl + "/refresh-token", {
      "refreshToken": token
    });
  }

  register(body: UserModel) {
    return this.http.post<any>(this.apiBaseUrl + "/register", new ProfileModel());
  }

  // ---- Enterprise SSO (OIDC Authorization Code + PKCE) -------------------------------------
  // /start returns the IdP authorize URL plus an opaque `txn` (holds nonce + PKCE verifier).
  // The browser keeps `txn` in sessionStorage and hands it back with the code on /callback.

  ssoStatus() {
    return this.http.get<SsoStatus>(this.apiBaseUrl + '/sso/oidc/status');
  }

  ssoStart(companyId?: string, returnTo?: string) {
    const body: any = {};
    if (companyId) body.companyId = companyId;
    if (returnTo) body.returnTo = returnTo;
    return this.http.post<SsoStart>(this.apiBaseUrl + '/sso/oidc/start', body);
  }

  ssoCallback(code: string, state: string, txn: string) {
    return this.http.post<UserModel & { returnTo?: string }>(this.apiBaseUrl + '/sso/oidc/callback', {
      code,
      state,
      txn,
    });
  }

  saveSsoTransaction(start: SsoStart): void {
    sessionStorage.setItem(SSO_TXN_KEY, JSON.stringify({ state: start.state, txn: start.txn }));
  }

  takeSsoTransaction(): { state: string; txn: string } | null {
    const raw = sessionStorage.getItem(SSO_TXN_KEY);
    sessionStorage.removeItem(SSO_TXN_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return parsed?.state && parsed?.txn ? parsed : null;
    } catch {
      return null;
    }
  }

}

export interface SsoStatus {
  enabled: boolean;
  issuer?: string | null;
  flow?: string | null;
}

export interface SsoStart {
  authorizeUrl: string;
  state: string;
  txn: string;
  expiresIn: number;
}
