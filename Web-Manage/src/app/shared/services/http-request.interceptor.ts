import { HTTP_INTERCEPTORS, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { HttpHandler, HttpRequest } from '@angular/common/http';

import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService, RefreshedTokens } from './auth.service';
import { environment } from '../../../environments/environment';


const TOKEN_HEADER_KEY = 'Authorization';
const CSRF_HEADER = 'X-CSRF-Token';
/** Endpoints that must never trigger a refresh / retry loop. */
const NO_REFRESH_PATHS = [
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/auth/kiosk/pair',
  '/auth/kiosk/refresh',
  '/auth/send-reset-password',
  '/auth/reset-password',
];

@Injectable()
export class HttpRequestInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<unknown> = new BehaviorSubject<unknown>(null);
  constructor(private tokenService: TokenService, private authService: AuthService) { }

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    if (req.url.startsWith("./")) {
      return next.handle(req);
    } else {
      let authReq = req;
      const fullUrl = req.url.startsWith("http") ? req.url : environment.baseUrl + req.url;
      const raw = this.tokenService.getToken();
      const token = raw ? (raw.startsWith("Bearer ") ? raw : "Bearer " + raw) : null;
      if (token) {
        authReq = this.addTokenHeader(req, token, fullUrl);
      } else {
        authReq = req.clone({
          url: fullUrl,
          withCredentials: req.withCredentials || this.needsCredentials(fullUrl),
        });
      }
      return next.handle(authReq).pipe(catchError(error => {
        // E4: rotate only on 401. Kiosk 403 (out of scope) must not trigger refresh.
        const refreshable =
          error instanceof HttpErrorResponse &&
          error.status === 401;
        if (refreshable && !NO_REFRESH_PATHS.some((p) => fullUrl.includes(p))) {
          return this.handle401Error(authReq, next, fullUrl);
        }
        return throwError(() => error);
      }));
    }

  }

  private needsCredentials(url: string): boolean {
    return url.includes('/auth/');
  }

  private handle401Error(request: HttpRequest<unknown>, next: HttpHandler, fullUrl: string) {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      const refresh = this.tokenService.getRefreshToken();
      const canCookieRefresh = !this.tokenService.isKioskSession();

      if (refresh || canCookieRefresh) {
        return this.authService
          .refreshSession(refresh, this.tokenService.isKioskSession())
          .pipe(
          switchMap((tokens: RefreshedTokens) => {
            this.isRefreshing = false;

            this.tokenService.saveToken(tokens.accessToken);
            if (tokens.refreshToken) {
              this.tokenService.saveRefreshToken(tokens.refreshToken);
            }
            if (tokens.csrfToken) {
              this.tokenService.saveCsrfToken(tokens.csrfToken);
            }
            this.refreshTokenSubject.next(tokens.accessToken);

            return next.handle(this.addTokenHeader(request, 'Bearer ' + tokens.accessToken, fullUrl));
          }),
          catchError((err) => {
            this.isRefreshing = false;

            this.tokenService.signOut();
            return throwError(() => err);
          })
        );
      }
      this.isRefreshing = false;
      this.tokenService.signOut();
      return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Session expired', url: fullUrl }));
    }

    return this.refreshTokenSubject.pipe(
      filter(token => token !== null),
      take(1),
      switchMap((token) => next.handle(this.addTokenHeader(request, 'Bearer ' + token, fullUrl)))
    );
  }



  private addTokenHeader(request: HttpRequest<unknown>, token: string, fullUrl: string) {
    const value = token.startsWith('Bearer ') ? token : 'Bearer ' + token;
    const headers: Record<string, string> = { [TOKEN_HEADER_KEY]: value };
    const csrf = this.tokenService.getCsrfToken();
    if (csrf && fullUrl.includes('/auth/')) {
      headers[CSRF_HEADER] = csrf;
    }
    return request.clone({
      setHeaders: headers,
      url: fullUrl,
      withCredentials: true,
    });
  }
}

export const httpInterceptorProviders = [
  { provide: HTTP_INTERCEPTORS, useClass: HttpRequestInterceptor, multi: true },
];
