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
  | 'muster';

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
        { section: 'zones', label: 'โซนประตู & ปลดล็อก', icon: 'ri-door-lock-line', route: '/company/access-control/zones' },
        { section: 'logs', label: 'ประวัติการผ่านประตู', icon: 'ri-file-list-3-line', route: '/company/access-control/logs' },
        { section: 'settings', label: 'ตั้งค่า Access & IoT Relay', icon: 'ri-settings-3-line', route: '/company/access-control/settings' },
      ];
    case 'WATCHLIST':
      return [
        { section: 'identities', label: 'บัญชี Blacklist / POI / VIP', icon: 'ri-shield-user-line', route: '/company/watchlist/identities' },
        { section: 'incidents', label: 'แจ้งเตือนเหตุการณ์ (Incident Alerts)', icon: 'ri-alarm-warning-line', route: '/company/watchlist/incidents' },
        { section: 'settings', label: 'ตั้งค่าแจ้งเตือน & SIEM', icon: 'ri-settings-4-line', route: '/company/watchlist/settings' },
      ];
    case 'VISITOR':
      return [
        { section: 'passes', label: 'บัตรผู้มาติดต่อ (Visitor Pass)', icon: 'ri-user-shared-line', route: '/company/visitors/passes' },
        { section: 'muster-roll', label: 'เช็คยอดคนในอาคาร (Muster Roll)', icon: 'ri-broadcast-line', route: '/company/visitors/muster-roll' },
        { section: 'settings', label: 'ตั้งค่าผู้มาติดต่อ & PDPA', icon: 'ri-shield-check-line', route: '/company/visitors/settings' },
      ];
    case 'EVENTS':
      return [
        { section: 'campaigns', label: 'แคมเปญ & ผู้ร่วมงาน', icon: 'ri-ticket-2-line', route: '/company/events/campaigns' },
        { section: 'checkins', label: 'สถิติเช็คอินสด & Booth Dwell', icon: 'ri-bar-chart-grouped-line', route: '/company/events/checkins' },
        { section: 'settings', label: 'ตั้งค่างานอีเวนต์', icon: 'ri-settings-3-line', route: '/company/events/settings' },
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
    if (accessSection === 'logs') return 'Access Control / ประวัติการผ่านประตู';
    if (accessSection === 'settings') return 'Access Control / ตั้งค่า';
    return 'Access Control / โซนประตู';
  }
  if (workspace === 'WATCHLIST') {
    const ws = normalizeWatchlistSection(section);
    if (ws === 'incidents') return 'Watchlist & VIP / แจ้งเตือนเหตุการณ์ (Incident Alerts)';
    if (ws === 'settings') return 'Watchlist & VIP / ตั้งค่าแจ้งเตือนความปลอดภัย & SIEM';
    return 'Watchlist & VIP / บัญชีเฝ้าระวัง Blacklist · POI · VIP';
  }
  if (workspace === 'VISITOR') {
    const vs = normalizeVisitorSection(section);
    if (vs === 'muster-roll') return 'Visitor & อาคาร / เช็คยอดคนในอาคาร (Muster Roll)';
    if (vs === 'settings') return 'Visitor & อาคาร / ตั้งค่าผู้มาติดต่อ & PDPA';
    return 'Visitor & อาคาร / บัตรผ่านใบหน้าชั่วคราว (Visitor Pass)';
  }
  if (workspace === 'EVENTS') {
    const es = normalizeEventsSection(section);
    if (es === 'checkins') return 'Events & สัมมนา / สถิติเช็คอินสด & เวลาแวะบูธ (Booth Dwell)';
    if (es === 'settings') return 'Events & สัมมนา / ตั้งค่างานอีเวนต์';
    return 'Events & สัมมนา / แคมเปญ & ลงทะเบียนผู้ร่วมงาน';
  }
  return workspace;
}
