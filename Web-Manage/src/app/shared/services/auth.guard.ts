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

const KIOSK_ROUTES = ['/company/timestamp-face', '/company/scan/'];

function isKioskAllowedPath(url: string): boolean {
  const path = url || '';
  return KIOSK_ROUTES.some((prefix) => path.startsWith(prefix));
}

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
   * token in the URL. A kiosk session may only open the kiosk / modular scan routes.
   */
  private redirectFor(url: string): string {
    return isKioskAllowedPath(url) ? '/kiosk/pair' : '/auth/login';
  }

  private allow(state: RouterStateSnapshot): boolean {
    const url = state?.url || '';
    if (url === '/' || url === '') {
      const role = String(this.tokenService.getUser()?.member?.role ?? '');
      const isSysAdmin = role === '99' || role.toUpperCase() === 'ADMIN_SYSTEM';
      this.router.navigate([isSysAdmin ? '/admin/home' : '/company/dashboard']);
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
      if (isKioskAllowedPath(url)) {
        return true;
      }
      this.router.navigate(['/company/timestamp-face']);
      return false;
    }
    if (this.tokenService.getToken()) {
      return this.allow(state);
    }
    // Access token is memory-only: try httpOnly refresh cookie once before bouncing to login.
    // Require CSRF (proves a prior cookie session) — do not refresh on a bare cached user blob.
    if (this.tokenService.getCsrfToken()) {
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
