import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, CanActivateChild, Router, RouterStateSnapshot } from '@angular/router';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { TokenService } from './token.service';
import { PermissionService } from './permission.service';

@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate, CanActivateChild {
  constructor(
    private router: Router,
    private tokenService: TokenService,
    private permissions: PermissionService,
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | boolean {
    return this.allow(route, state?.url || '');
  }

  canActivateChild(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> | boolean {
    return this.allow(route, state?.url || '');
  }

  private allow(route: ActivatedRouteSnapshot, url: string): Observable<boolean> | boolean {
    if (!this.tokenService.getToken()) {
      this.router.navigate(['/auth/login']);
      return false;
    }

    let snap: ActivatedRouteSnapshot | null = route;
    let area = '';
    let requiredPerm = '';
    while (snap) {
      if (snap.data?.['permission']) {
        requiredPerm = String(snap.data['permission']);
      }
      if (snap.data?.['area']) {
        area = snap.data['area'];
        break;
      }
      snap = snap.parent;
    }

    const companyId = this.tokenService.getSelectCompany()?.companyId
      ? String(this.tokenService.getSelectCompany().companyId)
      : null;

    // Admin area: system.admin only (server-driven when snapshot is warm).
    if (area === 'admin') {
      if (this.permissions.isSystemAdmin()) {
        return true;
      }
      return this.permissions.load(null).pipe(
        map((snapPerm) => {
          const ok =
            snapPerm.permissions.includes('system.admin') ||
            this.permissions.isSystemAdmin();
          if (!ok) {
            this.router.navigate(['/error/403']);
          }
          return ok;
        }),
        catchError(() => {
          this.router.navigate(['/auth/login']);
          return of(false);
        }),
      );
    }

    if (!requiredPerm && area === 'company') {
      requiredPerm = PermissionService.permissionForPath(url) || '';
    }

    if (requiredPerm) {
      return this.permissions.load(companyId).pipe(
        map(() => {
          const ok = this.permissions.has(requiredPerm);
          if (!ok) {
            this.router.navigate(['/error/403']);
          }
          return ok;
        }),
        catchError(() => {
          this.router.navigate(['/error/403']);
          return of(false);
        }),
      );
    }

    // Company pages without an explicit permission gate still warm up the snapshot.
    if (area === 'company' && companyId) {
      this.permissions.load(companyId).subscribe();
    }
    return true;
  }
}
