import {
  buildScanRoute,
  isAccessChrome,
  isAttendanceChrome,
  isEventChrome,
  isVisitorChrome,
  isWatchlistChrome,
  parseStationModeParam,
  resolveStationRouteContext,
  shouldEnableDoorRelay,
  stationModeRequiresGps,
  stationModeTitle,
  stationModeToSlug,
} from './scan-station-mode';

describe('scan-station-mode', () => {
  describe('parseStationModeParam', () => {
    it('maps URL slugs to station modes', () => {
      expect(parseStationModeParam('attendance')).toBe('ATTENDANCE');
      expect(parseStationModeParam('access-control')).toBe('ACCESS_CONTROL');
      expect(parseStationModeParam('watchlist')).toBe('WATCHLIST_MONITOR');
      expect(parseStationModeParam('visitor')).toBe('VISITOR_CHECKIN');
      expect(parseStationModeParam('event')).toBe('EVENT_CHECKIN');
      expect(parseStationModeParam('unified-hybrid')).toBe('UNIFIED_HYBRID');
    });

    it('accepts raw enums and aliases', () => {
      expect(parseStationModeParam('ACCESS_CONTROL')).toBe('ACCESS_CONTROL');
      expect(parseStationModeParam('watchlist_monitor')).toBe('WATCHLIST_MONITOR');
      expect(parseStationModeParam('hybrid')).toBe('UNIFIED_HYBRID');
    });

    it('defaults unknown / empty to ATTENDANCE', () => {
      expect(parseStationModeParam('')).toBe('ATTENDANCE');
      expect(parseStationModeParam(null)).toBe('ATTENDANCE');
      expect(parseStationModeParam('nope')).toBe('ATTENDANCE');
    });
  });

  describe('resolveStationRouteContext (SPA scan mode reactivity)', () => {
    it('resolves access-control with zone query', () => {
      const ctx = resolveStationRouteContext('access-control', 'zone-1', null);
      expect(ctx.stationMode).toBe('ACCESS_CONTROL');
      expect(ctx.zoneId).toBe('zone-1');
      expect(ctx.eventId).toBeNull();
      expect(ctx.routeHadMode).toBeTrue();
      expect(isAccessChrome(ctx.stationMode)).toBeTrue();
      expect(isWatchlistChrome(ctx.stationMode)).toBeFalse();
      expect(stationModeTitle(ctx.stationMode)).toBe('station.access');
    });

    it('updates mode when navigating access → watchlist → visitor → event', () => {
      // Regression for UI blocker #1: snapshot-only resolve left Access Control chrome stuck.
      const sequence = ['access-control', 'watchlist', 'visitor', 'event'] as const;
      const modes = sequence.map((slug) => resolveStationRouteContext(slug, null, null).stationMode);
      expect(modes).toEqual([
        'ACCESS_CONTROL',
        'WATCHLIST_MONITOR',
        'VISITOR_CHECKIN',
        'EVENT_CHECKIN',
      ]);
      expect(isAccessChrome(modes[0])).toBeTrue();
      expect(isWatchlistChrome(modes[1])).toBeTrue();
      expect(isVisitorChrome(modes[2])).toBeTrue();
      expect(isEventChrome(modes[3])).toBeTrue();
      // Each step must flip chrome — not remain ACCESS_CONTROL after leaving access.
      expect(isAccessChrome(modes[1])).toBeFalse();
      expect(isAccessChrome(modes[2])).toBeFalse();
      expect(isAccessChrome(modes[3])).toBeFalse();
    });

    it('treats timestamp-face (no :stationMode) as attendance without routeHadMode', () => {
      const ctx = resolveStationRouteContext(null, null, null);
      expect(ctx.stationMode).toBe('ATTENDANCE');
      expect(ctx.routeHadMode).toBeFalse();
      expect(isAttendanceChrome(ctx.stationMode)).toBeTrue();
    });

    it('clears zone/event when query drops them on mode change', () => {
      const access = resolveStationRouteContext('access-control', 'z1', null);
      const watchlist = resolveStationRouteContext('watchlist', null, null);
      expect(access.zoneId).toBe('z1');
      expect(watchlist.zoneId).toBeNull();
      expect(watchlist.stationMode).not.toBe(access.stationMode);
    });
  });

  describe('buildScanRoute', () => {
    it('builds path + optional query', () => {
      expect(buildScanRoute('ATTENDANCE')).toBe('/company/scan/attendance');
      expect(buildScanRoute('ACCESS_CONTROL', { zoneId: 'z1' })).toBe(
        '/company/scan/access-control?zoneId=z1',
      );
      expect(buildScanRoute('EVENT_CHECKIN', { eventId: 'e9' })).toBe(
        '/company/scan/event?eventId=e9',
      );
      expect(buildScanRoute('UNIFIED_HYBRID', { zoneId: 'z1', eventId: 'e9' })).toBe(
        '/company/scan/unified-hybrid?zoneId=z1&eventId=e9',
      );
    });

    it('round-trips slug helpers', () => {
      expect(stationModeToSlug('WATCHLIST_MONITOR')).toBe('watchlist');
      expect(parseStationModeParam(stationModeToSlug('VISITOR_CHECKIN'))).toBe('VISITOR_CHECKIN');
    });
  });

  describe('chrome / gps / door helpers', () => {
    it('attendance chrome covers hybrid', () => {
      expect(isAttendanceChrome('ATTENDANCE')).toBeTrue();
      expect(isAttendanceChrome('UNIFIED_HYBRID')).toBeTrue();
      expect(isAccessChrome('UNIFIED_HYBRID')).toBeTrue();
      expect(isAccessChrome('ATTENDANCE')).toBeFalse();
    });

    it('requires GPS only for attendance-like modes', () => {
      expect(stationModeRequiresGps('ATTENDANCE')).toBeTrue();
      expect(stationModeRequiresGps('UNIFIED_HYBRID')).toBeTrue();
      expect(stationModeRequiresGps('ACCESS_CONTROL')).toBeFalse();
      expect(stationModeRequiresGps('WATCHLIST_MONITOR')).toBeFalse();
    });

    it('enables door relay for hybrid/access or attendance flag', () => {
      expect(shouldEnableDoorRelay('UNIFIED_HYBRID', false)).toBeTrue();
      expect(shouldEnableDoorRelay('ACCESS_CONTROL', false)).toBeTrue();
      expect(shouldEnableDoorRelay('ATTENDANCE', false)).toBeFalse();
      expect(shouldEnableDoorRelay('ATTENDANCE', true)).toBeTrue();
      expect(shouldEnableDoorRelay('WATCHLIST_MONITOR', true)).toBeFalse();
    });
  });
});
