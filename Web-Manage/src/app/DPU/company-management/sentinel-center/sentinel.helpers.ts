import { SentinelIdentity, SentinelIncident } from './sentinel.models';

export function filterWatchlistItems(identities: SentinelIdentity[]): SentinelIdentity[] {
  return (identities || []).filter((i) =>
    !!i.identityType && ['BLACKLIST', 'POI', 'VIP'].includes(i.identityType),
  );
}

export function filterVisitorItems(identities: SentinelIdentity[]): SentinelIdentity[] {
  return (identities || []).filter((i) => i.identityType === 'VISITOR');
}

export function filterEventAttendeeItems(identities: SentinelIdentity[]): SentinelIdentity[] {
  return (identities || []).filter((i) => i.identityType === 'EVENT_ATTENDEE');
}

/** Build allowedIdentityTypes from zone form checkboxes. */
export function buildZoneAllowedIdentityTypes(form: {
  allowEmployee?: boolean;
  allowVip?: boolean;
  allowVisitor?: boolean;
}): string[] {
  const allowed: string[] = [];
  if (form.allowEmployee) allowed.push('EMPLOYEE');
  if (form.allowVip) allowed.push('VIP');
  if (form.allowVisitor) allowed.push('VISITOR');
  return allowed;
}

export function defaultScanForm(): {
  stationMode: string;
  zoneId: string;
  eventId: string;
  totpOrPin: string;
} {
  return {
    stationMode: 'ACCESS_CONTROL',
    zoneId: '',
    eventId: '',
    totpOrPin: '',
  };
}

export function defaultWatchlistForm(): {
  identityType: string;
  severity: string;
  fullName: string;
  documentRef: string;
  organization: string;
  alertNote: string;
} {
  return {
    identityType: 'BLACKLIST',
    severity: 'CRITICAL',
    fullName: '',
    documentRef: '',
    organization: '',
    alertNote: '',
  };
}

export function defaultVisitorForm(): {
  identityType: string;
  severity: string;
  fullName: string;
  organization: string;
  phoneNumber: string;
  visitPurpose: string;
  expiresAt: string;
} {
  return {
    identityType: 'VISITOR',
    severity: 'LOW',
    fullName: '',
    organization: '',
    phoneNumber: '',
    visitPurpose: '',
    expiresAt: '',
  };
}

export function defaultAttendeeForm(): {
  identityType: string;
  severity: string;
  eventId: string;
  fullName: string;
  seatNumber: string;
} {
  return {
    identityType: 'EVENT_ATTENDEE',
    severity: 'LOW',
    eventId: '',
    fullName: '',
    seatNumber: '',
  };
}

export function defaultZoneForm(): {
  name: string;
  code: string;
  stationMode: string;
  scheduleStart: string;
  scheduleEnd: string;
  allowEmployee: boolean;
  allowVip: boolean;
  allowVisitor: boolean;
  require2FA: boolean;
  relayWebhookUrl: string;
} {
  return {
    name: '',
    code: 'GATE-01',
    stationMode: 'ACCESS_CONTROL',
    scheduleStart: '07:00',
    scheduleEnd: '20:00',
    allowEmployee: true,
    allowVip: true,
    allowVisitor: true,
    require2FA: false,
    relayWebhookUrl: '',
  };
}

export function defaultEventForm(): {
  name: string;
  locationName: string;
  capacity: number;
  welcomeMessage: string;
} {
  return {
    name: '',
    locationName: 'Main Auditorium',
    capacity: 200,
    welcomeMessage: '',
  };
}

export function firstFileFromInput(event: Event): File | null {
  const input = event.target as HTMLInputElement;
  return input.files && input.files.length > 0 ? input.files[0] : null;
}

/** Deep-link to live Access Control scan for a zone (reuses scan-station-mode helpers). */
export function accessZoneScanRoute(zoneId: string | null | undefined): string {
  const id = (zoneId || '').trim();
  if (!id) return '/company/scan/access-control';
  return `/company/scan/access-control?zoneId=${encodeURIComponent(id)}`;
}

/** Client-side zone filter for incident rows (when API zoneId not used). */
export function filterIncidentsByZone(
  incidents: SentinelIncident[] | null | undefined,
  zoneId: string | null | undefined,
): SentinelIncident[] {
  const rows = incidents || [];
  const id = (zoneId || '').trim();
  if (!id) return rows;
  return rows.filter((inc) => String(inc?.zoneId || '') === id);
}

/** Export SentinelIncident rows as UTF-8 BOM CSV for Excel/SIEM review. */
export function downloadIncidentsCsv(
  incidents: SentinelIncident[] | null | undefined,
  filenamePrefix: string,
): void {
  const list = incidents || [];
  if (!list.length) return;
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const header = [
    'OccurredAt',
    'Subject',
    'IdentityType',
    'Zone',
    'EventType',
    'Severity',
    'Status',
    'Confidence',
    'ActionTaken',
  ].join(',');
  const rows = list.map((i) =>
    [
      esc(i.occurredAt),
      esc(i.subjectName || 'Unknown'),
      esc(i.identityType || ''),
      esc(i.zoneName || ''),
      esc(i.eventType || ''),
      esc(i.severity || ''),
      esc(i.status || 'OPEN'),
      esc(i.confidencePercent ?? ''),
      esc(i.actionTaken || ''),
    ].join(',')
  );
  const blob = new Blob(['\uFEFF' + [header, ...rows].join('\r\n')], {
    type: 'text/csv;charset=utf-8;',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filenamePrefix}-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
