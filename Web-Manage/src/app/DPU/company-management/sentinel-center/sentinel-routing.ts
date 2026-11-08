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

export function normalizeAccessSection(
  section: string | null | undefined,
): AccessControlSection {
  if (section === 'logs' || section === 'settings') return section;
  return 'zones';
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
  const sectionLabel = section ? ` / ${section}` : '';
  switch (workspace) {
    case 'WATCHLIST':
      return `Watchlist${sectionLabel}`;
    case 'VISITOR':
      return `Visitor${sectionLabel}`;
    case 'EVENTS':
      return `Events${sectionLabel}`;
    default:
      return workspace;
  }
}
