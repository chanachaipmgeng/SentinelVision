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
  | 'visitors'
  | 'events'
  | 'muster';

/** Map `/company/{module}/:section` → active sentinel tab. */
export function tabFromModuleSection(
  workspace: string | null | undefined,
  section: string | null | undefined,
): SentinelTab | null {
  if (!workspace) return null;
  switch (workspace) {
    case 'ACCESS_CONTROL':
      return 'access';
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
  const sectionLabel = section ? ` / ${section}` : '';
  switch (workspace) {
    case 'ACCESS_CONTROL':
      return `Access Control${sectionLabel}`;
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
