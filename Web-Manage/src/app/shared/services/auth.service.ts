import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { finalize, map, shareReplay } from 'rxjs/operators';
import { ProfileModel, UserModel } from '../user-auth.model';
import { KioskSession } from './token.service';

export interface RefreshedTokens {
  accessToken: string;
  refreshToken: string;
}

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

  /** Server-side logout: revokes the access token (header) and the refresh token (body). */
  logout(refreshToken: string | null) {
    return this.http.post<any>(this.apiBaseUrl + '/logout', {
      refreshToken: refreshToken || undefined,
    });
  }

  /** Exchange a one-time pairing code for a device-scoped kiosk session. */
  kioskPair(pairingCode: string): Observable<KioskSession> {
    return this.http.post<KioskSession>(this.apiBaseUrl + '/kiosk/pair', { pairingCode });
  }

  kioskRefresh(refreshToken: string) {
    return this.http.post<any>(this.apiBaseUrl + '/kiosk/refresh', { refreshToken });
  }

  private inflightRefresh?: Observable<RefreshedTokens>;

  /**
   * Rotate the current session's refresh token; normalises member and kiosk responses.
   * Single-flight: refresh tokens are one-shot server-side, so concurrent callers (interceptor
   * + kiosk WebSocket `token_expiring`) must share one request or the second would be flagged
   * as reuse and revoke the whole session.
   */
  refreshSession(refreshToken: string, kiosk: boolean): Observable<RefreshedTokens> {
    if (this.inflightRefresh) {
      return this.inflightRefresh;
    }
    const call = kiosk ? this.kioskRefresh(refreshToken) : this.refreshToken(refreshToken);
    this.inflightRefresh = call.pipe(
      map((res: any) => ({
        accessToken: res?.deviceToken || res?.accessToken || res?.access_token || '',
        refreshToken: res?.deviceRefreshToken || res?.refreshToken || res?.refresh_token || '',
      })),
      finalize(() => {
        this.inflightRefresh = undefined;
      }),
      shareReplay(1),
    );
    return this.inflightRefresh;
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
