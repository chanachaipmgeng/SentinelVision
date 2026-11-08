import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { TokenService } from './token.service';

export interface RbacRoleAssignment {
  role: string;
  companyId: string | null;
  departmentId: string | null;
  source: string;
}

export interface PermissionsSnapshot {
  memberId: string;
  companyId: string | null;
  roles: RbacRoleAssignment[];
  permissions: string[];
}

/**
 * Server-driven RBAC cache. Never trust role bits from localStorage alone —
 * refresh from ``GET /auth/me/permissions`` when the company context changes.
 */
@Injectable({ providedIn: 'root' })
export class PermissionService {
  private readonly snapshot$ = new BehaviorSubject<PermissionsSnapshot | null>(null);
  private loadedFor: string | null = null;

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
  ) {}

  /** Current permission codes (empty until loaded). */
  get permissions(): readonly string[] {
    return this.snapshot$.value?.permissions ?? [];
  }

  get roles(): readonly RbacRoleAssignment[] {
    return this.snapshot$.value?.roles ?? [];
  }

  watch(): Observable<PermissionsSnapshot | null> {
    return this.snapshot$.asObservable();
  }

  has(permission: string): boolean {
    const perms = this.snapshot$.value?.permissions;
    if (!perms) {
      // Bootstrap: allow system admin from member.role so admin area still works
      // before the first /me/permissions round-trip.
      const role = String(this.tokenService.getUser()?.member?.role ?? '');
      if (role === '99' || role === 'ADMIN_SYSTEM') {
        return true;
      }
      return false;
    }
    return perms.includes(permission) || perms.includes('system.admin');
  }

  hasAny(...permissions: string[]): boolean {
    return permissions.some((p) => this.has(p));
  }

  clear(): void {
    this.loadedFor = null;
    this.snapshot$.next(null);
  }

  /**
   * Load permissions for the given company (or platform-wide when omitted).
   * Dedupes identical in-flight company keys.
   */
  load(companyId?: string | null): Observable<PermissionsSnapshot> {
    const key = companyId || '__platform__';
    if (this.loadedFor === key && this.snapshot$.value) {
      return of(this.snapshot$.value);
    }
    const params: Record<string, string> = {};
    if (companyId) {
      params['companyId'] = companyId;
    }
    return this.http.get<PermissionsSnapshot>('/auth/me/permissions', { params }).pipe(
      tap((snap) => {
        this.loadedFor = key;
        this.snapshot$.next(snap);
      }),
      catchError(() => {
        this.loadedFor = null;
        const empty: PermissionsSnapshot = {
          memberId: '',
          companyId: companyId || null,
          roles: [],
          permissions: [],
        };
        this.snapshot$.next(empty);
        return of(empty);
      }),
    );
  }

  /** Convenience: reload for the company currently selected in TokenService. */
  loadForSelectedCompany(): Observable<PermissionsSnapshot> {
    const cid = this.tokenService.getSelectCompany()?.companyId;
    return this.load(cid ? String(cid) : null);
  }

  isSystemAdmin(): boolean {
    if (this.has('system.admin')) {
      return true;
    }
    const role = String(this.tokenService.getUser()?.member?.role ?? '');
    return role === '99' || role === 'ADMIN_SYSTEM';
  }

  /**
   * Company / HR admin for the current snapshot (or legacy member.role).
   * Used for soft-hiding employee-only nav (self-service) without blocking the route.
   */
  isCompanyAdmin(): boolean {
    const roles = this.roles.map((r) => String(r.role || '').toUpperCase());
    if (roles.includes('HR_ADMIN') || roles.includes('ADMIN_COMPANY')) {
      return true;
    }
    const legacy = String(this.tokenService.getUser()?.member?.role ?? '');
    return legacy === '1' || legacy === 'ADMIN_COMPANY';
  }

  /** Role codes for nav soft-hide (`Menu.hideForRoles`). */
  roleCodesForNav(): string[] {
    const codes = this.roles.map((r) => String(r.role || '')).filter(Boolean);
    if (this.isCompanyAdmin() && !codes.some((c) => /HR_ADMIN|ADMIN_COMPANY/i.test(c))) {
      codes.push('HR_ADMIN');
    }
    if (this.isSystemAdmin() && !codes.some((c) => /SYSTEM_ADMIN/i.test(c))) {
      codes.push('SYSTEM_ADMIN');
    }
    return codes;
  }

  /** Map a nav / route area to the permission that gates it. */
  static permissionForPath(path: string | undefined): string | null {
    if (!path) {
      return null;
    }
    if (path.startsWith('/admin')) {
      return 'system.admin';
    }
    if (path.includes('company-emp') || path.includes('company-department') || path.includes('company-position')) {
      if (path.includes('department')) return 'departments.read';
      if (path.includes('position')) return 'positions.read';
      return 'employees.read';
    }
    if (
      path.includes('timestamp') ||
      path.includes('warning-timestamp') ||
      path.includes('scan/attendance') ||
      path.includes('approval-inbox') ||
      path.includes('reports') ||
      path.includes('self-service')
    ) {
      if (path.includes('warning') || path.includes('approval-inbox')) return 'attendance.approve';
      return 'attendance.read';
    }
    if (path.includes('profile-security') || path.includes('devices') || path.includes('notification-center')) {
      return null;
    }
    if (path.includes('hr-schedule')) {
      return 'hr.shifts';
    }
    if (path.includes('company-location')) {
      return 'company.settings';
    }
    if (path.includes('audit-log')) {
      return 'audit.read';
    }
    if (path.includes('company-info')) {
      return 'company.read';
    }
    if (path.includes('access-control') || path.includes('watchlist') || path.includes('visitor') || path.includes('event')) {
      return 'sentinel.manage';
    }
    if (path.includes('scan-hub') || path.includes('dashboard')) {
      return 'company.read';
    }
    return null;
  }
}
