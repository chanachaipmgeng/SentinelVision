import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Router
} from '@angular/router';
import { TokenService } from './token.service';

const KIOSK_ROUTE = '/company/timestamp-face';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {

  constructor(private router: Router, private tokenService: TokenService) { }

  /**
   * Kiosk devices authenticate through the pairing screen (`/kiosk/pair`), never through a
   * token in the URL. A kiosk session may only open the kiosk route itself.
   */
  private redirectFor(url: string): string {
    return (url || '').startsWith(KIOSK_ROUTE) ? '/kiosk/pair' : '/auth/login';
  }

  private check(state: RouterStateSnapshot): boolean {
    const url = state?.url || '';
    if (this.tokenService.isKioskSession()) {
      if (url.startsWith(KIOSK_ROUTE)) {
        return true;
      }
      this.router.navigate([KIOSK_ROUTE]);
      return false;
    }
    if (this.tokenService.getToken()) {
      if (url == '/') {
        this.router.navigate(['/admin/member-manage']);
      }
      return true;
    }
    this.router.navigate([this.redirectFor(url)]);
    return false;
  }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return this.check(state);
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return this.check(state);
  }
}
