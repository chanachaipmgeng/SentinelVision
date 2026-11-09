export type SettingsSectionId =
  | 'notifications'
  | 'security'
  | 'retention'
  | 'incident-sla'
  | 'scan-actions'
  | 'devices'
  | 'shifts';

export interface SettingsSection {
  id: SettingsSectionId;
  labelKey: string;
  hintKey: string;
  icon: string;
  /** RBAC code from `GET /auth/me/permissions`; rail item hidden when missing. */
  permission: string;
  /** Full-page editor for this section (toolbar "open" button). */
  deepLink?: string;
  deepLinkKey?: string;
}

export interface SettingsLinkCard {
  path: string;
  labelKey: string;
  hintKey: string;
  icon: string;
}

export const SHIFT_LINK_CARDS: readonly SettingsLinkCard[] = [
  {
    path: '/company/hr-schedule/shifts',
    labelKey: 'settingsHub.shifts.shifts',
    hintKey: 'settingsHub.shifts.shifts.hint',
    icon: 'ri-time-line',
  },
  {
    path: '/company/hr-schedule/leaves',
    labelKey: 'settingsHub.shifts.leaves',
    hintKey: 'settingsHub.shifts.leaves.hint',
    icon: 'ri-calendar-check-line',
  },
  {
    path: '/company/hr-schedule/holidays',
    labelKey: 'settingsHub.shifts.holidays',
    hintKey: 'settingsHub.shifts.holidays.hint',
    icon: 'ri-calendar-event-line',
  },
];

export const DEFAULT_SETTINGS_SECTION: SettingsSectionId = 'notifications';

export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
  {
    id: 'notifications',
    labelKey: 'settingsHub.section.notifications',
    hintKey: 'settingsHub.section.notifications.hint',
    icon: 'ri-notification-3-line',
    permission: 'notifications.manage',
    deepLink: '/company/notification-center',
    deepLinkKey: 'settingsHub.open.notificationCenter',
  },
  {
    id: 'security',
    labelKey: 'settingsHub.section.security',
    hintKey: 'settingsHub.section.security.hint',
    icon: 'ri-shield-keyhole-line',
    permission: 'company.settings',
    deepLink: '/company/profile-security',
    deepLinkKey: 'settingsHub.open.profileSecurity',
  },
  {
    id: 'retention',
    labelKey: 'settingsHub.section.retention',
    hintKey: 'settingsHub.section.retention.hint',
    icon: 'ri-database-2-line',
    permission: 'company.settings',
    deepLink: '/company/hr-schedule/pdpa',
    deepLinkKey: 'settingsHub.open.hrSchedule',
  },
  {
    id: 'incident-sla',
    labelKey: 'settingsHub.section.incidentSla',
    hintKey: 'settingsHub.section.incidentSla.hint',
    icon: 'ri-timer-flash-line',
    permission: 'company.settings',
    deepLink: '/company/access-control/logs',
    deepLinkKey: 'settingsHub.open.accessLogs',
  },
  {
    id: 'scan-actions',
    labelKey: 'settingsHub.section.scanActions',
    hintKey: 'settingsHub.section.scanActions.hint',
    icon: 'ri-radar-line',
    permission: 'company.settings',
    deepLink: '/company/scan-hub',
    deepLinkKey: 'settingsHub.open.scanHub',
  },
  {
    id: 'devices',
    labelKey: 'settingsHub.section.devices',
    hintKey: 'settingsHub.section.devices.hint',
    icon: 'ri-tablet-line',
    permission: 'devices.manage',
    deepLink: '/company/devices',
    deepLinkKey: 'settingsHub.open.devices',
  },
  {
    id: 'shifts',
    labelKey: 'settingsHub.section.shifts',
    hintKey: 'settingsHub.section.shifts.hint',
    icon: 'ri-time-line',
    permission: 'hr.shifts',
  },
];

export function visibleSettingsSections(
  hasPermission: (code: string) => boolean,
  sections: readonly SettingsSection[] = SETTINGS_SECTIONS,
): SettingsSection[] {
  return sections.filter((s) => hasPermission(s.permission));
}

/**
 * Section to render for a requested `:section` param. Returns `null` when the
 * caller can see no section at all.
 */
export function resolveSettingsSection(
  requested: string | null | undefined,
  visible: readonly SettingsSection[],
): SettingsSectionId | null {
  if (!visible.length) return null;
  const hit = visible.find((s) => s.id === requested);
  if (hit) return hit.id;
  const fallback = visible.find((s) => s.id === DEFAULT_SETTINGS_SECTION);
  return (fallback ?? visible[0]).id;
}
