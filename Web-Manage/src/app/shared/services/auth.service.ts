import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { finalize, map, shareReplay, tap } from 'rxjs/operators';
import { UserModel } from '../user-auth.model';
import { KioskSession, TokenService } from './token.service';
import { isRecord, pickString } from '../utils/type-guards';

export interface RefreshedTokens {
  accessToken: string;
  refreshToken: string;
  csrfToken?: string;
}

const SSO_TXN_KEY = 'dpu-sso-txn';
const CSRF_HEADER = 'X-CSRF-Token';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  apiBaseUrl = "/auth";
  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
  ) {
  }

  private withCreds(extra?: Record<string, string>) {
    const headers: Record<string, string> = { ...(extra || {}) };
    const csrf = this.tokenService.getCsrfToken();
    if (csrf) {
      headers[CSRF_HEADER] = csrf;
    }
    return {
      withCredentials: true,
      headers: new HttpHeaders(headers),
    };
  }

  login(username: string, password: string, totpCode?: string) {
    const body: Record<string, string> = {
      username: username,
      password: password,
    };
    if (totpCode && totpCode.trim()) {
      body['totpCode'] = totpCode.trim();
    }
    return this.http.post<UserModel>(this.apiBaseUrl + '/login', body, { withCredentials: true }).pipe(
      tap((res) => this.applyMemberSession(res)),
    );
  }

  /** Identify system-admin face → greeting challenge (no session). */
  identifyWithFace(frames: Blob[]) {
    const form = new FormData();
    frames.forEach((blob, i) => {
      form.append('frames', blob, `frame-${i}.jpg`);
    });
    return this.http.post<{
      challengeToken: string;
      displayName: string;
      picture?: string | null;
    }>(this.apiBaseUrl + '/login/face/identify', form, { withCredentials: true });
  }

  /** Confirm face login after blink: challengeToken + frames + optional TOTP. */
  loginWithFace(frames: Blob[], totpCode?: string, challengeToken?: string) {
    const form = new FormData();
    frames.forEach((blob, i) => {
      form.append('frames', blob, `frame-${i}.jpg`);
    });
    if (challengeToken && challengeToken.trim()) {
      form.append('challengeToken', challengeToken.trim());
    }
    if (totpCode && totpCode.trim()) {
      form.append('totpCode', totpCode.trim());
    }
    return this.http
      .post<UserModel>(this.apiBaseUrl + '/login/face', form, { withCredentials: true })
      .pipe(tap((res) => this.applyMemberSession(res)));
  }

  /** Cookie-based refresh for member SPA sessions (requires CSRF double-submit). */
  refreshFromCookie(): Observable<RefreshedTokens> {
    return this.http
      .post<Record<string, unknown>>(this.apiBaseUrl + '/refresh-token', {}, this.withCreds())
      .pipe(
        map((res) => this.normalizeTokens(res)),
        tap((tokens) => {
          this.tokenService.saveToken(tokens.accessToken);
          if (tokens.csrfToken) {
            this.tokenService.saveCsrfToken(tokens.csrfToken);
          }
        }),
      );
  }

  refreshToken(token: string) {
    // Legacy body refresh (kiosk / API clients). Prefer refreshFromCookie for members.
    return this.http.post<Record<string, unknown>>(
      this.apiBaseUrl + '/refresh-token',
      { refreshToken: token },
      { withCredentials: true }
    );
  }

  /** Server-side logout: revokes bearer + refresh cookie/family and clears auth cookies. */
  logout(refreshToken: string | null) {
    const body: { refreshToken?: string } = {};
    if (refreshToken) {
      body.refreshToken = refreshToken;
    }
    return this.http.post<Record<string, unknown>>(this.apiBaseUrl + '/logout', body, this.withCreds());
  }

  /** Exchange a one-time pairing code for a device-scoped kiosk session. */
  kioskPair(pairingCode: string): Observable<KioskSession> {
    return this.http.post<KioskSession>(this.apiBaseUrl + '/kiosk/pair', { pairingCode });
  }

  kioskRefresh(refreshToken: string) {
    return this.http.post<Record<string, unknown>>(this.apiBaseUrl + '/kiosk/refresh', { refreshToken });
  }

  private inflightRefresh?: Observable<RefreshedTokens>;

  /**
   * Rotate the current session's refresh token; normalises member and kiosk responses.
   * Single-flight: refresh tokens are one-shot server-side, so concurrent callers (interceptor
   * + kiosk WebSocket `token_expiring`) must share one request or the second would be flagged
   * as reuse and revoke the whole session.
   */
  refreshSession(refreshToken: string | null, kiosk: boolean): Observable<RefreshedTokens> {
    if (this.inflightRefresh) {
      return this.inflightRefresh;
    }
    let call: Observable<Record<string, unknown>>;
    if (kiosk) {
      if (!refreshToken) {
        return throwError(() => new Error('Kiosk refresh token required'));
      }
      call = this.kioskRefresh(refreshToken);
    } else if (refreshToken) {
      call = this.refreshToken(refreshToken);
    } else {
      call = this.http.post<Record<string, unknown>>(this.apiBaseUrl + '/refresh-token', {}, this.withCreds());
    }
    this.inflightRefresh = call.pipe(
      map((res) => this.normalizeTokens(res)),
      tap((tokens) => {
        this.tokenService.saveToken(tokens.accessToken);
        if (tokens.refreshToken) {
          this.tokenService.saveRefreshToken(tokens.refreshToken);
        }
        if (tokens.csrfToken) {
          this.tokenService.saveCsrfToken(tokens.csrfToken);
        }
      }),
      finalize(() => {
        this.inflightRefresh = undefined;
      }),
      shareReplay(1),
    );
    return this.inflightRefresh;
  }

  sendResetPassword(email: string) {
    return this.http.post<{ ok: boolean; resetToken?: string }>(
      this.apiBaseUrl + '/send-reset-password',
      { email },
      { withCredentials: true }
    );
  }

  resetPassword(token: string, newPassword: string) {
    return this.http.post<{ ok: boolean }>(
      this.apiBaseUrl + '/reset-password',
      { token, newPassword },
      { withCredentials: true }
    );
  }

  // ---- Enterprise SSO (OIDC Authorization Code + PKCE) -------------------------------------
  // /start returns the IdP authorize URL plus an opaque `txn` (holds nonce + PKCE verifier).
  // The browser keeps `txn` in sessionStorage and hands it back with the code on /callback.

  ssoStatus() {
    return this.http.get<SsoStatus>(this.apiBaseUrl + '/sso/oidc/status');
  }

  ssoStart(companyId?: string, returnTo?: string) {
    const body: { companyId?: string; returnTo?: string } = {};
    if (companyId) body.companyId = companyId;
    if (returnTo) body.returnTo = returnTo;
    return this.http.post<SsoStart>(this.apiBaseUrl + '/sso/oidc/start', body);
  }

  ssoCallback(code: string, state: string, txn: string) {
    return this.http
      .post<UserModel & { returnTo?: string }>(
        this.apiBaseUrl + '/sso/oidc/callback',
        { code, state, txn },
        { withCredentials: true }
      )
      .pipe(tap((res) => this.applyMemberSession(res)));
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

  applyMemberSession(res: UserModel | Record<string, unknown>): void {
    if (!res) return;
    const access = pickString(
      isRecord(res) ? res : {},
      'accessToken',
      'access_token',
    );
    if (access) {
      this.tokenService.saveToken(access);
    }
    const csrf = isRecord(res) ? res['csrfToken'] : undefined;
    if (typeof csrf === 'string' && csrf) {
      this.tokenService.saveCsrfToken(csrf);
    }
    // Refresh stays in httpOnly cookie — never write it to storage.
    this.tokenService.saveUser(res);
  }

  private normalizeTokens(res: Record<string, unknown>): RefreshedTokens {
    const accessToken = pickString(res, 'deviceToken', 'accessToken', 'access_token');
    const refreshToken = pickString(
      res,
      'deviceRefreshToken',
      'refreshToken',
      'refresh_token',
    );
    const csrfRaw = res['csrfToken'];
  return {
      accessToken,
      refreshToken,
      csrfToken: typeof csrfRaw === 'string' ? csrfRaw : undefined,
    };
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
