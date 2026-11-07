import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Router
} from '@angular/router';
import { TokenService } from './token.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {

  constructor(private router: Router, private tokenService: TokenService) { }

  private tryHydrateKioskToken(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    const qToken =
      route.queryParams?.['kioskToken'] ||
      this.extractQueryParam(state?.url || '', 'kioskToken');
    if (!qToken) {
      return false;
    }
    try {
      const parts = String(qToken).split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload?.typ === 'kiosk' && payload?.companyId) {
          this.tokenService.saveToken(String(qToken));
          this.tokenService.saveSelectCompany({
            companyId: String(payload.companyId),
            companyName: 'Kiosk Device',
          } as any);
          return true;
        }
      }
    } catch {
      // Ignore malformed token
    }
    return false;
  }

  private extractQueryParam(url: string, key: string): string | null {
    const qIdx = url.indexOf('?');
    if (qIdx < 0) return null;
    const params = new URLSearchParams(url.slice(qIdx + 1));
    return params.get(key);
  }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    this.tryHydrateKioskToken(route, state);
    if (this.tokenService.getToken()) {
      if (state.url == '/') {
        this.router.navigate(['/admin/member-manage']);
      }
      return true;
    }
    this.router.navigate(['/auth/login']);
    return false;
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    this.tryHydrateKioskToken(route, state);
    if (this.tokenService.getToken()) {
      return true;
    }
    this.router.navigate(['/auth/login']);
    return false;
  }
}
