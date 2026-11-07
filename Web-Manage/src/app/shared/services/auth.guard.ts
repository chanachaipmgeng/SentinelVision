import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Router,
  UrlTree,
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';

const KIOSK_ROUTE = '/company/timestamp-face';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {

  constructor(
    private router: Router,
    private tokenService: TokenService,
    private authService: AuthService,
  ) { }

  /**
   * Kiosk devices authenticate through the pairing screen (`/kiosk/pair`), never through a
   * token in the URL. A kiosk session may only open the kiosk route itself.
   */
  private redirectFor(url: string): string {
    return (url || '').startsWith(KIOSK_ROUTE) ? '/kiosk/pair' : '/auth/login';
  }

  private allow(state: RouterStateSnapshot): boolean {
    const url = state?.url || '';
    if (url == '/') {
      this.router.navigate(['/admin/member-manage']);
    }
    return true;
  }

  private deny(state: RouterStateSnapshot): boolean {
    this.router.navigate([this.redirectFor(state?.url || '')]);
    return false;
  }

  private check(state: RouterStateSnapshot): boolean | Observable<boolean | UrlTree> {
    const url = state?.url || '';
    if (this.tokenService.isKioskSession()) {
      if (url.startsWith(KIOSK_ROUTE)) {
        return true;
      }
      this.router.navigate([KIOSK_ROUTE]);
      return false;
    }
    if (this.tokenService.getToken()) {
      return this.allow(state);
    }
    // Access token is memory-only: try httpOnly refresh cookie once before bouncing to login.
    if (this.tokenService.getCsrfToken() || this.tokenService.getUser()?.member?.memberId) {
      return this.authService.refreshFromCookie().pipe(
        map(() => this.allow(state)),
        catchError(() => {
          this.deny(state);
          return of(false);
        }),
      );
    }
    return this.deny(state);
  }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return this.check(state);
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return this.check(state);
  }
}
