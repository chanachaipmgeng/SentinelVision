export interface SentinelZone {
  zoneId: string;
  name?: string;
  thName?: string;
  code?: string;
  stationMode?: string;
  scheduleStart?: string;
  scheduleEnd?: string;
  require2FA?: boolean;
  allowedIdentityTypes?: string[];
}

export interface SentinelIncident {
  incidentId: string;
  subjectName?: string | null;
  identityType?: string | null;
  eventType?: string | null;
  actionTaken?: string | null;
  zoneId?: string | null;
  zoneName?: string | null;
  confidencePercent?: number | null;
  occurredAt?: string | Date | null;
  status?: string | null;
  severity?: string | null;
  slaDueAt?: string | Date | null;
  acknowledgedAt?: string | Date | null;
  assignedAt?: string | Date | null;
  closedAt?: string | Date | null;
  snapshotUrl?: string | null;
  [key: string]: unknown;
}

export interface SentinelScanResult {
  decision?: string | null;
  accessGranted?: boolean | null;
  message?: string | null;
  subjectName?: string | null;
  identityType?: string | null;
  confidencePercent?: number | null;
  seatNumber?: string | null;
  alertNote?: string | null;
  [key: string]: unknown;
}

export interface SentinelBulkAckResult {
  acknowledgedCount?: number;
}

export interface SentinelBulkCloseResult {
  closedCount?: number;
}

export interface CameraEventClip {
  clipId?: string;
  durationMs?: number;
  downloadPath?: string;
}

export interface SentinelIdentity {
  identityId: string;
  subjectName?: string;
  fullName?: string;
  identityType?: string;
  severity?: string;
  organization?: string;
  phoneNumber?: string;
  visitPurpose?: string;
  expiresAt?: string | null;
  documentRef?: string;
  alertNote?: string;
  seatNumber?: string;
  eventId?: string;
  hasFace?: boolean;
  hasFaceEnrolled?: boolean;
}

export interface SentinelEventRule {
  eventId: string;
  name?: string;
  welcomeMessage?: string;
  locationName?: string;
  attendeeCount?: number;
  capacity?: number;
  checkedInCount?: number;
}

export interface SentinelOverviewSummary {
  blacklistAndPoiCount?: number;
  vipCount?: number;
  activeVisitorCount?: number;
  openIncidentCount?: number;
  activeZoneCount?: number;
  activeZonesCount?: number;
  liveEventsCount?: number;
  eventAttendeeCount?: number;
  buildingOccupancyCount?: number;
  unacknowledgedAlerts?: number;
}

export interface SentinelSiemSettings {
  siemWebhookUrl?: string;
  hasSiemWebhookSecret?: boolean;
}

export interface SentinelMusterRollItem {
  fullName?: string;
  category?: string;
  badgeCode?: string;
  zoneOrLocation?: string;
  source?: string;
  lastSeenAt?: string | Date | null;
}

export interface SentinelMusterPage {
  items?: SentinelMusterRollItem[];
  total?: number;
  workDate?: string;
  limit?: number;
  offset?: number;
}

export interface SentinelEdgeManifest {
  manifestVersion?: string;
  embeddingModel?: string;
  employeeVectorsCount?: number;
  sentinelVectorsCount?: number;
  totalActiveVectors?: number;
}

export interface SentinelOverview {
  openIncidents?: number;
  criticalIncidents?: number;
  zones?: number;
  summary?: SentinelOverviewSummary;
  musterRoll?: SentinelMusterRollItem[];
  musterMeta?: { total?: number; workDate?: string };
}
