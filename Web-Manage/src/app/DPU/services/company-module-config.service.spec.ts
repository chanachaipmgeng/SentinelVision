import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import {
  ALWAYS_ON_MODULES,
  CompanyModuleConfigService,
  DEFAULT_COMPANY_MODULE_CONFIG,
} from './company-module-config.service';

describe('CompanyModuleConfigService', () => {
  let service: CompanyModuleConfigService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] });
    service = TestBed.inject(CompanyModuleConfigService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads and caches GET /sentinel/company/{id}/module-config', () => {
    let first: unknown;
    service.getModuleConfig('c1').subscribe((cfg) => (first = cfg));

    const req = http.expectOne('/sentinel/company/c1/module-config');
    expect(req.request.method).toBe('GET');
    req.flush({
      enabledModules: ['ATTENDANCE', 'WATCHLIST'],
      defaultStationMode: 'ATTENDANCE',
    });

    expect(first).toEqual(
      jasmine.objectContaining({
        enabledModules: ['ATTENDANCE', 'WATCHLIST'],
        alwaysOnModules: [...ALWAYS_ON_MODULES],
      })
    );

    let second: unknown;
    service.getModuleConfig('c1').subscribe((cfg) => (second = cfg));
    http.expectNone('/sentinel/company/c1/module-config');
    expect(second).toEqual(first);
  });

  it('falls back to defaults when the endpoint is unavailable', () => {
    let result: unknown;
    service.getModuleConfig('c-missing').subscribe((cfg) => (result = cfg));

    http.expectOne('/sentinel/company/c-missing/module-config').flush('missing', {
      status: 404,
      statusText: 'Not Found',
    });

    expect(result).toEqual(
      jasmine.objectContaining({
        enabledModules: DEFAULT_COMPANY_MODULE_CONFIG.enabledModules,
        alwaysOnModules: [...ALWAYS_ON_MODULES],
      })
    );
  });

  it('returns always-on + enabled modules from getEffectiveModules', () => {
    let modules: string[] | undefined;
    service.getEffectiveModules('c2').subscribe((m) => (modules = m));

    http.expectOne('/sentinel/company/c2/module-config').flush({
      enabledModules: ['EVENTS'],
    });

    expect(modules).toEqual(['CORE', 'GOVERNANCE', 'EVENTS']);
  });

  it('PUT updates cache', () => {
    let updated: unknown;
    service
      .updateModuleConfig('c3', { enabledModules: ['ATTENDANCE'] })
      .subscribe((cfg) => (updated = cfg));

    const req = http.expectOne('/sentinel/company/c3/module-config');
    expect(req.request.method).toBe('PUT');
    req.flush({ enabledModules: ['ATTENDANCE'] });

    expect(updated).toEqual(
      jasmine.objectContaining({ enabledModules: ['ATTENDANCE'] })
    );

    let cached: unknown;
    service.getModuleConfig('c3').subscribe((cfg) => (cached = cfg));
    http.expectNone('/sentinel/company/c3/module-config');
    expect(cached).toEqual(updated);
  });
});
