import { HTTP_INTERCEPTORS, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpHandler, HttpRequest } from '@angular/common/http';

import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService, RefreshedTokens } from './auth.service';
import { environment } from '../../../environments/environment';


const TOKEN_HEADER_KEY = 'Authorization';    // for Node.js Expre
/** Endpoints that must never trigger a refresh / retry loop. */
const NO_REFRESH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/kiosk/pair', '/auth/kiosk/refresh'];

@Injectable()
export class HttpRequestInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);
  constructor(private tokenService: TokenService, private authService: AuthService) { }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (req.url.startsWith("./")) {
      return next.handle(req);
    } else {
      let authReq = req;
      const fullUrl = req.url.startsWith("http") ? req.url : environment.baseUrl + req.url;
      const raw = this.tokenService.getToken();
      const token = raw ? (raw.startsWith("Bearer ") ? raw : "Bearer " + raw) : null;
      if (token) {
        authReq = this.addTokenHeader(req, token ,fullUrl);
      }else{
        const overideReq = {
          url: fullUrl,
        };
        authReq = req.clone(overideReq);
      }
      return next.handle(authReq).pipe(catchError(error => {
        // A kiosk device token gets 403 for anything outside the kiosk scope; refreshing
        // cannot fix that, so only 401 triggers a rotation for kiosk sessions.
        const refreshable =
          error instanceof HttpErrorResponse &&
          (error.status === 401 || (error.status === 403 && !this.tokenService.isKioskSession()));
        if (refreshable && !NO_REFRESH_PATHS.some((p) => fullUrl.includes(p))) {
          return this.handle403Error(authReq, next ,fullUrl);
        }
        return throwError(() => error);
      }));
    }

  }

  private handle403Error(request: HttpRequest<any>, next: HttpHandler , fullUrl : string) {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      const token = this.tokenService.getRefreshToken();

      if (token)
        // Refresh tokens rotate server-side: the old one is revoked once this call succeeds.
        return this.authService
          .refreshSession(token.replace("Bearer ", ""), this.tokenService.isKioskSession())
          .pipe(
          switchMap((tokens: RefreshedTokens) => {
            this.isRefreshing = false;

            this.tokenService.saveToken(tokens.accessToken);
            if (tokens.refreshToken) {
              this.tokenService.saveRefreshToken(tokens.refreshToken);
            }
            this.refreshTokenSubject.next(tokens.accessToken);

            return next.handle(this.addTokenHeader(request, 'Bearer ' + tokens.accessToken ,fullUrl));
          }),
          catchError((err) => {
            this.isRefreshing = false;

            this.tokenService.signOut();
            return throwError(() => err);
          })
        );
      this.isRefreshing = false;
      this.tokenService.signOut();
      return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Session expired', url: fullUrl }));
    }

    return this.refreshTokenSubject.pipe(
      filter(token => token !== null),
      take(1),
      switchMap((token) => next.handle(this.addTokenHeader(request, 'Bearer ' + token ,fullUrl)))
    );
  }



  private addTokenHeader(request: HttpRequest<any>, token: string ,fullUrl :string) {
    /* for Spring Boot back-end */
    // return request.clone({ headers: request.headers.set(TOKEN_HEADER_KEY, 'Bearer ' + token) });

    /* for Node.js Express back-end */
    const value = token.startsWith('Bearer ') ? token : 'Bearer ' + token;
    return request.clone({ headers: request.headers.set(TOKEN_HEADER_KEY, value) , url : fullUrl });
  }
}
