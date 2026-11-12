import {
  accessZoneScanRoute,
  buildZoneAllowedIdentityTypes,
  filterEventAttendeeItems,
  filterIncidentsByZone,
  filterVisitorItems,
  filterWatchlistItems,
} from './sentinel.helpers';
import { SentinelIdentity } from './sentinel.models';
import { normalizeAccessSection, tabFromModuleSection } from './sentinel-routing';

describe('sentinel.helpers', () => {
  const identities = [
    { identityType: 'BLACKLIST', fullName: 'A' },
    { identityType: 'VIP', fullName: 'B' },
    { identityType: 'VISITOR', fullName: 'C' },
    { identityType: 'EVENT_ATTENDEE', fullName: 'D' },
    { identityType: 'POI', fullName: 'E' },
  ] as SentinelIdentity[];

  it('filters watchlist / visitor / attendee slices', () => {
    expect(filterWatchlistItems(identities).map((i) => i.fullName)).toEqual(['A', 'B', 'E']);
    expect(filterVisitorItems(identities).map((i) => i.fullName)).toEqual(['C']);
    expect(filterEventAttendeeItems(identities).map((i) => i.fullName)).toEqual(['D']);
  });

  it('buildZoneAllowedIdentityTypes from checkboxes', () => {
    expect(
      buildZoneAllowedIdentityTypes({
        allowEmployee: true,
        allowVip: false,
        allowVisitor: true,
      }),
    ).toEqual(['EMPLOYEE', 'VISITOR']);
  });

  it('accessZoneScanRoute deep-links with zoneId', () => {
    expect(accessZoneScanRoute('zone-1')).toBe('/company/scan/access-control?zoneId=zone-1');
    expect(accessZoneScanRoute('')).toBe('/company/scan/access-control');
    expect(accessZoneScanRoute(null)).toBe('/company/scan/access-control');
  });

  it('filterIncidentsByZone keeps matching zone rows', () => {
    const rows = [
      { incidentId: '1', zoneId: 'z1' },
      { incidentId: '2', zoneId: 'z2' },
      { incidentId: '3', zoneId: null },
    ];
    expect(filterIncidentsByZone(rows, 'z1').map((r) => r.incidentId)).toEqual(['1']);
    expect(filterIncidentsByZone(rows, '').length).toBe(3);
  });
});

describe('sentinel-routing', () => {
  it('tabFromModuleSection maps workspaces', () => {
    expect(tabFromModuleSection('ACCESS_CONTROL', 'zones')).toBe('access');
    expect(tabFromModuleSection('ACCESS_CONTROL', 'logs')).toBe('access-logs');
    expect(tabFromModuleSection('ACCESS_CONTROL', 'settings')).toBe('access-settings');
    expect(tabFromModuleSection('ACCESS_CONTROL', null)).toBe('access');
    expect(tabFromModuleSection('WATCHLIST', 'identities')).toBe('watchlist');
    expect(tabFromModuleSection('VISITOR', 'passes')).toBe('visitors');
    expect(tabFromModuleSection('VISITOR', 'muster-roll')).toBe('muster');
    expect(tabFromModuleSection('EVENTS', 'campaigns')).toBe('events');
    expect(tabFromModuleSection(null, null)).toBeNull();
  });

  it('normalizeAccessSection defaults unknown to zones', () => {
    expect(normalizeAccessSection('logs')).toBe('logs');
    expect(normalizeAccessSection('settings')).toBe('settings');
    expect(normalizeAccessSection('zones')).toBe('zones');
    expect(normalizeAccessSection('weird')).toBe('zones');
  });
});
