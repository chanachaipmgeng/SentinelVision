import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, CanActivateChild, Router } from '@angular/router';
import { TokenService } from './token.service';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate, CanActivateChild {
  constructor(private router: Router, private tokenService: TokenService) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    return this.allow(route);
  }

  canActivateChild(route: ActivatedRouteSnapshot): boolean {
    return this.allow(route);
  }

  private allow(route: ActivatedRouteSnapshot): boolean {
    if (!this.tokenService.getToken()) {
      this.router.navigate(['/auth/login']);
      return false;
    }
    const role = String(this.tokenService.getUser()?.member?.role ?? '');
    const isSystem = role === '99' || role === 'ADMIN_SYSTEM';
    let snap: ActivatedRouteSnapshot | null = route;
    let need = '';
    while (snap) {
      if (snap.data?.['area']) {
        need = snap.data['area'];
        break;
      }
      snap = snap.parent;
    }
    if (need === 'admin' && !isSystem) {
      this.router.navigate(['/auth/login']);
      return false;
    }
    if (need === 'company' && isSystem) {
      this.router.navigate(['/admin/member-manage']);
      return false;
    }
    return true;
  }
}
