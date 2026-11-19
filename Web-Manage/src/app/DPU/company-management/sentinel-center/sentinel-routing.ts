/** Legacy ?tab= values → dedicated module routes. */
export const LEGACY_TAB_REDIRECTS: Record<string, string> = {
  command: '/company/scan-hub',
  watchlist: '/company/watchlist/identities',
  access: '/company/access-control/zones',
  visitors: '/company/visitors/passes',
  events: '/company/events/campaigns',
  muster: '/company/visitors/muster-roll',
};

export type SentinelTab =
  | 'command'
  | 'watchlist'
  | 'access'
  | 'access-logs'
  | 'access-settings'
  | 'visitors'
  | 'events'
  | 'muster'
  | 'graph';

/** Access Control `:section` values under `/company/access-control/:section`. */
export type AccessControlSection = 'zones' | 'logs' | 'settings';

/** Watchlist `:section` values under `/company/watchlist/:section`. */
export type WatchlistSection = 'identities' | 'incidents' | 'settings';

/** Visitor `:section` values under `/company/visitors/:section`. */
export type VisitorSection = 'passes' | 'muster-roll' | 'settings';

/** Events `:section` values under `/company/events/:section`. */
export type EventsSection = 'campaigns' | 'checkins' | 'settings';

export interface WorkspaceSubNavItem {
  section: string;
  label: string;
  icon: string;
  route: string;
}

export function normalizeAccessSection(
  section: string | null | undefined,
): AccessControlSection {
  if (section === 'logs' || section === 'settings') return section;
  return 'zones';
}

export function normalizeWatchlistSection(
  section: string | null | undefined,
): WatchlistSection {
  if (section === 'incidents' || section === 'settings') return section;
  return 'identities';
}

export function normalizeVisitorSection(
  section: string | null | undefined,
): VisitorSection {
  if (section === 'muster-roll' || section === 'settings') return section;
  return 'passes';
}

export function normalizeEventsSection(
  section: string | null | undefined,
): EventsSection {
  if (section === 'checkins' || section === 'settings') return section;
  return 'campaigns';
}

/** Sub-navigation pills for module-scoped workspaces. */
export function workspaceSubNav(
  workspace: string | null | undefined,
): WorkspaceSubNavItem[] {
  switch (workspace) {
    case 'ACCESS_CONTROL':
      return [
        { section: 'zones', label: 'sentinel.subnav.zones', icon: 'ri-door-lock-line', route: '/company/access-control/zones' },
        { section: 'logs', label: 'sentinel.subnav.accessLogs', icon: 'ri-file-list-3-line', route: '/company/access-control/logs' },
        { section: 'settings', label: 'sentinel.subnav.accessSettings', icon: 'ri-settings-3-line', route: '/company/access-control/settings' },
      ];
    case 'WATCHLIST':
      return [
        { section: 'identities', label: 'sentinel.subnav.watchlist', icon: 'ri-shield-user-line', route: '/company/watchlist/identities' },
        { section: 'incidents', label: 'sentinel.subnav.incidents', icon: 'ri-alarm-warning-line', route: '/company/watchlist/incidents' },
        { section: 'settings', label: 'sentinel.subnav.watchlistSettings', icon: 'ri-settings-4-line', route: '/company/watchlist/settings' },
      ];
    case 'VISITOR':
      return [
        { section: 'passes', label: 'sentinel.subnav.visitors', icon: 'ri-user-shared-line', route: '/company/visitors/passes' },
        { section: 'muster-roll', label: 'sentinel.subnav.musterRoll', icon: 'ri-broadcast-line', route: '/company/visitors/muster-roll' },
        { section: 'settings', label: 'sentinel.subnav.visitorSettings', icon: 'ri-shield-check-line', route: '/company/visitors/settings' },
      ];
    case 'EVENTS':
      return [
        { section: 'campaigns', label: 'sentinel.subnav.events', icon: 'ri-ticket-2-line', route: '/company/events/campaigns' },
        { section: 'checkins', label: 'sentinel.subnav.eventCheckins', icon: 'ri-bar-chart-grouped-line', route: '/company/events/checkins' },
        { section: 'settings', label: 'sentinel.subnav.eventSettings', icon: 'ri-settings-3-line', route: '/company/events/settings' },
      ];
    default:
      return [];
  }
}

/** Map `/company/{module}/:section` → active sentinel tab. */
export function tabFromModuleSection(
  workspace: string | null | undefined,
  section: string | null | undefined,
): SentinelTab | null {
  if (!workspace) return null;
  switch (workspace) {
    case 'ACCESS_CONTROL': {
      const accessSection = normalizeAccessSection(section);
      if (accessSection === 'logs') return 'access-logs';
      if (accessSection === 'settings') return 'access-settings';
      return 'access';
    }
    case 'WATCHLIST':
      return 'watchlist';
    case 'VISITOR':
      return section === 'muster-roll' ? 'muster' : 'visitors';
    case 'EVENTS':
      return 'events';
    default:
      return null;
  }
}

export function labelForWorkspace(workspace: string, section: string | null): string {
  if (workspace === 'ACCESS_CONTROL') {
    const accessSection = normalizeAccessSection(section);
    if (accessSection === 'logs') return 'Access Control • Logs';
    if (accessSection === 'settings') return 'Access Control • Settings';
    return 'Access Control • Zones';
  }
  if (workspace === 'WATCHLIST') {
    const ws = normalizeWatchlistSection(section);
    if (ws === 'incidents') return 'Watchlist & VIP • Incidents';
    if (ws === 'settings') return 'Watchlist & VIP • Settings';
    return 'Watchlist & VIP • Identities';
  }
  if (workspace === 'VISITOR') {
    const vs = normalizeVisitorSection(section);
    if (vs === 'muster-roll') return 'Visitor • Muster Roll';
    if (vs === 'settings') return 'Visitor • Settings';
    return 'Visitor • Passes';
  }
  if (workspace === 'EVENTS') {
    const es = normalizeEventsSection(section);
    if (es === 'checkins') return 'Events • Live Check-ins';
    if (es === 'settings') return 'Events • Settings';
    return 'Events • Campaigns';
  }
  return workspace;
}
