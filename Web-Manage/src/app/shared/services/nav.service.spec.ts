import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { NavService } from './nav.service';
import { TokenService } from './token.service';

describe('NavService', () => {
  let service: NavService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        NavService,
        { provide: Router, useValue: { events: { subscribe: () => ({}) } } },
        { provide: TokenService, useValue: {} },
      ],
    });
    service = TestBed.inject(NavService);
  });

  it('builds a sectioned company menu without duplicate sentinel-center links', () => {
    const menu = service.getCompanyMenu();
    const paths = menu
      .flatMap((m) => [m.path, ...(m.children || []).map((c) => c.path)])
      .filter(Boolean) as string[];

    expect(paths.filter((p) => p === '/company/sentinel-center').length).toBe(0);
    expect(paths).toContain('/company/scan-hub');
    expect(paths).toContain('/company/scan/attendance');
    expect(paths).toContain('/company/access-control/zones');
    expect(paths).toContain('/company/watchlist/identities');
    expect(paths).toContain('/company/visitors/passes');
    expect(paths).toContain('/company/events/campaigns');
    expect(paths).toContain('/company/audit-log');
    expect(paths).toContain('/company/notification-center');
    expect(paths).toContain('/company/approval-inbox');
    expect(paths).toContain('/company/reports');
    expect(paths).toContain('/company/self-service');
    expect(paths).toContain('/company/profile-security');
  });

  it('always keeps COMMAND, CORE, and GOVERNANCE when filtering', () => {
    const filtered = service.filterCompanyMenuByModules(service.getCompanyMenu(), [
      'ATTENDANCE',
    ]);
    const moduleIds = new Set(
      filtered.map((m) => m.moduleId).filter(Boolean)
    );

    expect(moduleIds.has('COMMAND')).toBeTrue();
    expect(moduleIds.has('CORE')).toBeTrue();
    expect(moduleIds.has('GOVERNANCE')).toBeTrue();
    expect(moduleIds.has('ATTENDANCE')).toBeTrue();
    expect(moduleIds.has('WATCHLIST')).toBeFalse();
    expect(moduleIds.has('ACCESS_CONTROL')).toBeFalse();
    expect(moduleIds.has('VISITOR')).toBeFalse();
    expect(moduleIds.has('EVENTS')).toBeFalse();
  });

  it('hides toggleable modules that are not enabled', () => {
    const filtered = service.filterCompanyMenuByModules(service.getCompanyMenu(), [
      'WATCHLIST',
      'EVENTS',
    ]);
    const paths = filtered
      .flatMap((m) => [m.path, ...(m.children || []).map((c) => c.path)])
      .filter(Boolean) as string[];

    expect(paths).toContain('/company/watchlist/identities');
    expect(paths).toContain('/company/events/campaigns');
    expect(paths).not.toContain('/company/scan/attendance');
    expect(paths).not.toContain('/company/access-control/zones');
    expect(paths).not.toContain('/company/visitors/passes');
  });

  it('defaults to all toggleable modules when enabledModules is null', () => {
    const filtered = service.filterCompanyMenuByModules(service.getCompanyMenu(), null);
    const moduleIds = new Set(filtered.map((m) => m.moduleId).filter(Boolean));
    expect(moduleIds.has('ATTENDANCE')).toBeTrue();
    expect(moduleIds.has('ACCESS_CONTROL')).toBeTrue();
    expect(moduleIds.has('WATCHLIST')).toBeTrue();
    expect(moduleIds.has('VISITOR')).toBeTrue();
    expect(moduleIds.has('EVENTS')).toBeTrue();
  });

  it('soft-hides self-service for HR_ADMIN / company admin roles', () => {
    const allowAll = () => true;
    const asEmployee = service.filterMenuByPermissions(
      service.getCompanyMenu(),
      allowAll,
      []
    );
    const empPaths = asEmployee
      .flatMap((m) => [m.path, ...(m.children || []).map((c) => c.path)])
      .filter(Boolean) as string[];
    expect(empPaths).toContain('/company/self-service');

    const asAdmin = service.filterMenuByPermissions(
      service.getCompanyMenu(),
      allowAll,
      ['HR_ADMIN']
    );
    const adminPaths = asAdmin
      .flatMap((m) => [m.path, ...(m.children || []).map((c) => c.path)])
      .filter(Boolean) as string[];
    expect(adminPaths).not.toContain('/company/self-service');
    expect(adminPaths).toContain('/company/approval-inbox');
  });
});
