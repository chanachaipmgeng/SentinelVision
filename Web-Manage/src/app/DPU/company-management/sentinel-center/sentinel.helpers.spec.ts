import {
  buildZoneAllowedIdentityTypes,
  filterEventAttendeeItems,
  filterVisitorItems,
  filterWatchlistItems,
} from './sentinel.helpers';
import { tabFromModuleSection } from './sentinel-routing';

describe('sentinel.helpers', () => {
  const identities = [
    { identityType: 'BLACKLIST', fullName: 'A' },
    { identityType: 'VIP', fullName: 'B' },
    { identityType: 'VISITOR', fullName: 'C' },
    { identityType: 'EVENT_ATTENDEE', fullName: 'D' },
    { identityType: 'POI', fullName: 'E' },
  ];

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
});

describe('sentinel-routing', () => {
  it('tabFromModuleSection maps workspaces', () => {
    expect(tabFromModuleSection('ACCESS_CONTROL', 'zones')).toBe('access');
    expect(tabFromModuleSection('WATCHLIST', 'identities')).toBe('watchlist');
    expect(tabFromModuleSection('VISITOR', 'passes')).toBe('visitors');
    expect(tabFromModuleSection('VISITOR', 'muster-roll')).toBe('muster');
    expect(tabFromModuleSection('EVENTS', 'campaigns')).toBe('events');
    expect(tabFromModuleSection(null, null)).toBeNull();
  });
});
