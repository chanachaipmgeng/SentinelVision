import {
  DEFAULT_COMPANY_MODULE_CONFIG,
} from '../../services/company-module-config.service';
import {
  buildHubLaunchLinks,
  buildHubModuleCards,
  buildModuleConfigPutBody,
  companyHomeScanHubLink,
  patchScanActionRule,
  toggleEnabledModule,
} from './scan-hub.helpers';

describe('scan-hub.helpers', () => {
  describe('toggleEnabledModule', () => {
    it('adds and removes toggleable modules in canonical order', () => {
      expect(toggleEnabledModule(['EVENTS'], 'ATTENDANCE', true)).toEqual([
        'ATTENDANCE',
        'EVENTS',
      ]);
      expect(toggleEnabledModule(['ATTENDANCE', 'EVENTS'], 'ATTENDANCE', false)).toEqual([
        'EVENTS',
      ]);
    });

    it('ignores unknown / duplicate noise', () => {
      expect(toggleEnabledModule(['CORE', 'ATTENDANCE', 'ATTENDANCE'] as any, 'WATCHLIST', true)).toEqual([
        'ATTENDANCE',
        'WATCHLIST',
      ]);
    });
  });

  describe('buildHubModuleCards / launch links', () => {
    it('marks enabled modules from config', () => {
      const cfg = {
        ...DEFAULT_COMPANY_MODULE_CONFIG,
        enabledModules: ['ATTENDANCE', 'WATCHLIST'] as const,
      };
      const cards = buildHubModuleCards({
        ...cfg,
        enabledModules: [...cfg.enabledModules],
      });
      expect(cards.find((c) => c.module === 'ATTENDANCE')?.enabled).toBeTrue();
      expect(cards.find((c) => c.module === 'WATCHLIST')?.enabled).toBeTrue();
      expect(cards.find((c) => c.module === 'EVENTS')?.enabled).toBeFalse();
    });

    it('builds launch links for enabled scanners and hybrid when both attendance+access', () => {
      const cfg = {
        ...DEFAULT_COMPANY_MODULE_CONFIG,
        enabledModules: ['ATTENDANCE', 'ACCESS_CONTROL'] as ('ATTENDANCE' | 'ACCESS_CONTROL')[],
        defaultZoneId: 'zone-1',
        scanActionRules: { ...DEFAULT_COMPANY_MODULE_CONFIG.scanActionRules },
      };
      const links = buildHubLaunchLinks(cfg);
      const modes = links.map((l) => l.stationMode);
      expect(modes).toContain('ATTENDANCE');
      expect(modes).toContain('ACCESS_CONTROL');
      expect(modes).toContain('UNIFIED_HYBRID');
      expect(links.find((l) => l.stationMode === 'ACCESS_CONTROL')?.route).toContain('zoneId=zone-1');
    });

    it('omits hybrid when only one of attendance/access is on (unless default)', () => {
      const cfg = {
        ...DEFAULT_COMPANY_MODULE_CONFIG,
        enabledModules: ['ATTENDANCE'] as ('ATTENDANCE')[],
        defaultStationMode: 'ATTENDANCE' as const,
        scanActionRules: { ...DEFAULT_COMPANY_MODULE_CONFIG.scanActionRules },
      };
      expect(buildHubLaunchLinks(cfg).map((l) => l.stationMode)).not.toContain('UNIFIED_HYBRID');

      const hybridDefault = {
        ...cfg,
        defaultStationMode: 'UNIFIED_HYBRID' as const,
      };
      expect(buildHubLaunchLinks(hybridDefault).map((l) => l.stationMode)).toContain('UNIFIED_HYBRID');
    });
  });

  describe('put body / rules / deep-link', () => {
    it('builds a PUT body from draft config', () => {
      const draft = {
        ...DEFAULT_COMPANY_MODULE_CONFIG,
        enabledModules: ['ATTENDANCE' as const],
        defaultStationMode: 'ACCESS_CONTROL' as const,
        defaultZoneId: 'z',
        defaultEventId: null,
        scanActionRules: {
          ...DEFAULT_COMPANY_MODULE_CONFIG.scanActionRules,
          enableDoorRelayOnAttendance: true,
        },
      };
      expect(buildModuleConfigPutBody(draft)).toEqual(
        jasmine.objectContaining({
          enabledModules: ['ATTENDANCE'],
          defaultStationMode: 'ACCESS_CONTROL',
          defaultZoneId: 'z',
          scanActionRules: jasmine.objectContaining({ enableDoorRelayOnAttendance: true }),
        }),
      );
    });

    it('patches scan action rules immutably', () => {
      const base = { ...DEFAULT_COMPANY_MODULE_CONFIG.scanActionRules };
      const next = patchScanActionRule(base, 'enableTtsVoice', false);
      expect(next.enableTtsVoice).toBeFalse();
      expect(base.enableTtsVoice).toBeTrue();
    });

    it('builds company-home deep links to the hub', () => {
      expect(companyHomeScanHubLink('c1')).toBe('/company/scan-hub');
      expect(companyHomeScanHubLink('c1', 'ATTENDANCE')).toBe('/company/scan-hub?launch=ATTENDANCE');
    });
  });
});
