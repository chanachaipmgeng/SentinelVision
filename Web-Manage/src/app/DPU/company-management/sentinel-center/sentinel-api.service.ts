import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {
  SentinelEdgeManifest,
  SentinelMusterPage,
  SentinelSiemSettings,
  SentinelBulkAckResult,
  SentinelBulkCloseResult,
  SentinelEventDwellReport,
  SentinelEventRule,
  SentinelIdentity,
  SentinelIncident,
  SentinelOverview,
  SentinelScanResult,
  SentinelZone,
} from './sentinel.models';

/** All `/sentinel/company/{id}/*` HttpClient paths. */
export interface SentinelGraphNode {
  id: string;
  name: string;
  category: number;
  symbolSize: number;
  meta: Record<string, unknown>;
}

export interface SentinelInvestigationGraph {
  categories: { name: string }[];
  nodes: SentinelGraphNode[];
  links: { source: string; target: string; relation: string }[];
  stats: {
    zones: number;
    cameras: number;
    identities: number;
    incidents: number;
    totalNodes: number;
    totalLinks: number;
  };
}

export interface ParkingOverviewData {
  totalSpots: number;
  occupiedSpots: number;
  availableSpots: number;
  occupancyRate: number;
  totalVehicles: number;
  activeVehicles: number;
  blacklistedVehicles: number;
  entriesToday: number;
  exitsToday: number;
  zoneBreakdown: Array<{
    zone: string;
    total: number;
    occupied: number;
    available: number;
    rate: number;
  }>;
  recentTransactions: ParkingTransactionItem[];
}

export interface ParkingSpotItem {
  spotId: string;
  companyId: string;
  spotCode: string;
  zone: string;
  floor?: string | null;
  spotType: string;
  isOccupied: boolean;
  occupiedVehicleId?: string | null;
  occupiedPlate?: string | null;
  occupiedSince?: string | null;
  status: string;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface VehicleItem {
  vehicleId: string;
  companyId: string;
  licensePlate: string;
  province?: string | null;
  vehicleType: string;
  brand?: string | null;
  model?: string | null;
  color?: string | null;
  ownerType: string;
  ownerName?: string | null;
  ownerContact?: string | null;
  companyEmployeeId?: string | null;
  identityId?: string | null;
  status: string;
  notes?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ParkingTransactionItem {
  transactionId: string;
  companyId: string;
  vehicleId?: string | null;
  spotId?: string | null;
  licensePlate: string;
  province?: string | null;
  entryTime: string;
  exitTime?: string | null;
  dwellMinutes?: number | null;
  gateIn?: string | null;
  gateOut?: string | null;
  entryConfidence?: number | null;
  exitConfidence?: number | null;
  entrySnapshotUrl?: string | null;
  exitSnapshotUrl?: string | null;
  authStatus: string;
  actionTaken: string;
  createdAt?: string | null;
}

export interface LprScanResult {
  transactionId: string;
  licensePlate: string;
  province?: string | null;
  direction: string;
  authStatus: string;
  actionTaken: string;
  barrierOpen: boolean;
  reason: string;
  gate: string;
  spotAllocated?: {
    spotId: string;
    spotCode: string;
    zone: string;
    floor?: string | null;
    spotType: string;
  } | null;
  dwellMinutes?: number | null;
  ownerInfo?: {
    ownerType: string;
    ownerName?: string | null;
    vehicleType: string;
    brand?: string | null;
    model?: string | null;
    color?: string | null;
  } | null;
  timestamp: string;
}

export interface RfidCardItem {
  cardId: string;
  companyId: string;
  cardNumber: string;
  facilityCode?: string | null;
  cardType: string;
  assignedType: string;
  companyEmployeeId?: string | null;
  identityId?: string | null;
  holderName?: string | null;
  cardStatus: string;
  issuedAt?: string | null;
  expiresAt?: string | null;
  lastSwipedAt?: string | null;
  lastDoor?: string | null;
  notes?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface RfidVerificationResult {
  granted: boolean;
  accessStatus: string;
  reason: string;
  cardId?: string;
  cardNumber: string;
  cardType?: string;
  assignedType?: string;
  holderName?: string | null;
  companyEmployeeId?: string | null;
  identityId?: string | null;
  doorName: string;
  timestamp: string;
}

@Injectable({ providedIn: 'root' })
export class SentinelApiService {
  constructor(private http: HttpClient) {}

  private base(companyId: string): string {
    return `/sentinel/company/${companyId}`;
  }

  getOverview(companyId: string): Observable<SentinelOverview> {
    return this.http.get<SentinelOverview>(`${this.base(companyId)}/overview`);
  }

  getInvestigationGraph(companyId: string, days = 7): Observable<SentinelInvestigationGraph> {
    return this.http.get<SentinelInvestigationGraph>(`${this.base(companyId)}/graph?days=${days}`);
  }

  getMuster(
    companyId: string,
    opts?: { limit?: number; offset?: number }
  ): Observable<SentinelMusterPage> {
    const limit = opts?.limit ?? 100;
    const offset = opts?.offset ?? 0;
    return this.http.get<SentinelMusterPage>(
      `${this.base(companyId)}/muster?limit=${limit}&offset=${offset}`
    );
  }

  getSiemSettings(companyId: string): Observable<SentinelSiemSettings> {
    return this.http.get<SentinelSiemSettings>(`${this.base(companyId)}/siem-settings`);
  }

  putSiemSettings(companyId: string, body: Record<string, unknown>): Observable<SentinelSiemSettings> {
    return this.http.put<SentinelSiemSettings>(`${this.base(companyId)}/siem-settings`, body);
  }

  testSiemSettings(companyId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/siem-settings/test`, {});
  }

  getIdentities(companyId: string): Observable<SentinelIdentity[]> {
    return this.http.get<SentinelIdentity[]>(`${this.base(companyId)}/identities`);
  }

  createIdentity(companyId: string, body: Record<string, unknown>): Observable<SentinelIdentity> {
    return this.http.post<SentinelIdentity>(`${this.base(companyId)}/identities`, body);
  }

  updateIdentity(
    companyId: string,
    identityId: string,
    body: Record<string, unknown>,
  ): Observable<SentinelIdentity> {
    return this.http.put<SentinelIdentity>(
      `${this.base(companyId)}/identities/${identityId}`,
      body,
    );
  }

  enrollIdentityFace(companyId: string, identityId: string, file: File): Observable<Record<string, unknown>> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/identities/${identityId}/enroll-face`, fd);
  }

  deleteIdentity(companyId: string, identityId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`${this.base(companyId)}/identities/${identityId}`);
  }

  getZones(companyId: string): Observable<SentinelZone[]> {
    return this.http.get<SentinelZone[]>(`${this.base(companyId)}/zones`);
  }

  createZone(companyId: string, body: Record<string, unknown>): Observable<SentinelZone> {
    return this.http.post<SentinelZone>(`${this.base(companyId)}/zones`, body);
  }

  updateZone(
    companyId: string,
    zoneId: string,
    body: Record<string, unknown>,
  ): Observable<SentinelZone> {
    return this.http.put<SentinelZone>(`${this.base(companyId)}/zones/${zoneId}`, body);
  }

  triggerZone(companyId: string, zoneId: string, reason: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/zones/${zoneId}/trigger`, { reason });
  }

  triggerFireAlarm(companyId: string, reason = 'Emergency Fire Alarm Fail-Safe'): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/fire-alarm`, { reason });
  }

  resetFireAlarm(companyId: string, reason = 'All clear — normal operation restored'): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/fire-alarm/reset`, { reason });
  }

  runHealthCheck(companyId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/health-check`, {});
  }

  reindexVectors(companyId: string, targetModel = 'buffalo_l-512d-norm-v2'): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/reindex-vectors`, { targetModel });
  }

  edgeUnlockZone(companyId: string, zoneId: string, body: Record<string, unknown> = {}): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/zones/${zoneId}/edge-unlock`, body);
  }

  deleteZone(companyId: string, zoneId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`${this.base(companyId)}/zones/${zoneId}`);
  }

  getEvents(companyId: string): Observable<SentinelEventRule[]> {
    return this.http.get<SentinelEventRule[]>(`${this.base(companyId)}/events`);
  }

  createEvent(companyId: string, body: Record<string, unknown>): Observable<SentinelEventRule> {
    return this.http.post<SentinelEventRule>(`${this.base(companyId)}/events`, body);
  }

  deleteEvent(companyId: string, eventId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`${this.base(companyId)}/events/${eventId}`);
  }

  updateEventRegistration(
    companyId: string,
    eventId: string,
    body: Record<string, unknown>,
  ): Observable<Record<string, unknown>> {
    return this.http.patch<Record<string, unknown>>(
      `${this.base(companyId)}/events/${eventId}/registration`,
      body,
    );
  }

  getEventRegistrations(
    companyId: string,
    eventId: string,
    limit = 50,
    offset = 0,
    search?: string,
  ): Observable<Record<string, unknown>> {
    let url = `${this.base(companyId)}/events/${eventId}/registrations?limit=${limit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    return this.http.get<Record<string, unknown>>(url);
  }

  exportEventRegistrationsUrl(companyId: string, eventId: string): string {
    return `${this.base(companyId)}/events/${eventId}/registrations/export`;
  }

  cancelEventRegistration(
    companyId: string,
    eventId: string,
    registrationId: string,
  ): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(
      `${this.base(companyId)}/events/${eventId}/registrations/${registrationId}/cancel`,
      {},
    );
  }

  getIncidents(
    companyId: string,
    severity?: string,
    status?: string,
    zoneId?: string
  ): Observable<SentinelIncident[]> {
    const params: string[] = [];
    if (severity) params.push(`severity=${encodeURIComponent(severity)}`);
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (zoneId) params.push(`zoneId=${encodeURIComponent(zoneId)}`);
    const q = params.length ? `?${params.join('&')}` : '';
    return this.http.get<SentinelIncident[]>(`${this.base(companyId)}/incidents${q}`);
  }

  acknowledgeIncident(companyId: string, incidentId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/incidents/${incidentId}/acknowledge`, {});
  }

  bulkAcknowledgeIncidents(companyId: string, incidentIds: string[]): Observable<SentinelBulkAckResult> {
    return this.http.post<SentinelBulkAckResult>(`${this.base(companyId)}/incidents/bulk-acknowledge`, {
      incidentIds,
    });
  }

  assignIncident(
    companyId: string,
    incidentId: string,
    body: { assignedTo?: string } = {}
  ): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/incidents/${incidentId}/assign`, body);
  }

  closeIncident(companyId: string, incidentId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/incidents/${incidentId}/close`, {});
  }

  bulkCloseIncidents(companyId: string, incidentIds: string[]): Observable<SentinelBulkCloseResult> {
    return this.http.post<SentinelBulkCloseResult>(`${this.base(companyId)}/incidents/bulk-close`, {
      incidentIds,
    });
  }

  getIncidentSlaSettings(companyId: string): Observable<{ incidentSlaMinutesHigh: number }> {
    return this.http.get<{ incidentSlaMinutesHigh: number }>(
      `${this.base(companyId)}/incident-sla-settings`,
    );
  }

  putIncidentSlaSettings(
    companyId: string,
    body: { incidentSlaMinutesHigh: number },
  ): Observable<{ incidentSlaMinutesHigh: number }> {
    return this.http.put<{ incidentSlaMinutesHigh: number }>(
      `${this.base(companyId)}/incident-sla-settings`,
      body,
    );
  }

  getEdgeSync(companyId: string): Observable<SentinelEdgeManifest> {
    return this.http.get<SentinelEdgeManifest>(`${this.base(companyId)}/edge-sync`);
  }

  unifiedScan(companyId: string, formData: FormData): Observable<SentinelScanResult> {
    return this.http.post<SentinelScanResult>(`${this.base(companyId)}/scan`, formData);
  }

  getEventDwell(companyId: string, eventId: string): Observable<SentinelEventDwellReport> {
    return this.http.get<SentinelEventDwellReport>(
      `/presence/company/${companyId}/events/${eventId}/dwell`,
    );
  }

  verifyAuditChain(companyId: string, limit = 500): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(
      `${this.base(companyId)}/audit-verify`,
      { params: { limit: String(limit) } },
    );
  }

  createVisitorInvite(
    companyId: string,
    body: {
      visitorName: string;
      hostName?: string;
      purpose?: string;
      validHours?: number;
      inviteTtlHours?: number;
    },
  ): Observable<{ inviteToken: string; invitePath: string; expiresAt: string }> {
    return this.http.post<{ inviteToken: string; invitePath: string; expiresAt: string }>(
      `${this.base(companyId)}/visitors/invite`,
      body,
    );
  }

  ocrVisitorDocument(
    companyId: string,
    formData: FormData,
  ): Observable<{ ok: boolean; companyId: string; document: Record<string, unknown> }> {
    return this.http.post<{ ok: boolean; companyId: string; document: Record<string, unknown> }>(
      `${this.base(companyId)}/visitors/ocr-document`,
      formData,
    );
  }

  getDrTopology(companyId: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base(companyId)}/dr/topology`);
  }

  checkInBreakoutRoom(
    companyId: string,
    eventId: string,
    body: { roomCode: string; capacity: number; subjectName: string },
  ): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(
      `${this.base(companyId)}/events/${eventId}/sessions/check-in`,
      body,
    );
  }

  askAssistant(
    companyId: string,
    message: string,
  ): Observable<{ reply: string; provider: string }> {
    return this.http
      .post(`${this.base(companyId)}/assistant/chat`, { question: message, message }, { responseType: 'text' })
      .pipe(
        map((raw) => {
          const chunks: string[] = [];
          let provider = 'sentinel-copilot';
          let currentEvent = '';
          for (const line of String(raw || '').split('\n')) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              try {
                const payload = JSON.parse(line.slice(5).trim());
                if (currentEvent === 'token' && typeof payload?.text === 'string') {
                  chunks.push(payload.text);
                } else if (currentEvent === 'done' && typeof payload?.provider === 'string') {
                  provider = payload.provider;
                } else if (typeof payload?.reply === 'string') {
                  chunks.push(payload.reply);
                }
              } catch {
                // ignore malformed SSE line
              }
            }
          }
          return { reply: chunks.join('').trim() || String(raw || '').trim(), provider };
        }),
      );
  }

  // =========================================================================
  // P3: Vehicle & Smart Parking APIs
  // =========================================================================

  getParkingOverview(companyId: string): Observable<ParkingOverviewData> {
    return this.http.get<ParkingOverviewData>(`${this.base(companyId)}/parking/overview`);
  }

  getParkingSpots(companyId: string, zone?: string, status?: string): Observable<ParkingSpotItem[]> {
    let url = `${this.base(companyId)}/parking/spots`;
    const params: string[] = [];
    if (zone) params.push(`zone=${encodeURIComponent(zone)}`);
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    return this.http.get<ParkingSpotItem[]>(url);
  }

  createParkingSpot(companyId: string, data: Partial<ParkingSpotItem>): Observable<ParkingSpotItem> {
    return this.http.post<ParkingSpotItem>(`${this.base(companyId)}/parking/spots`, data);
  }

  updateParkingSpot(companyId: string, spotId: string, data: Partial<ParkingSpotItem>): Observable<ParkingSpotItem> {
    return this.http.put<ParkingSpotItem>(`${this.base(companyId)}/parking/spots/${spotId}`, data);
  }

  deleteParkingSpot(companyId: string, spotId: string): Observable<{ success: boolean; spotId: string }> {
    return this.http.delete<{ success: boolean; spotId: string }>(`${this.base(companyId)}/parking/spots/${spotId}`);
  }

  getVehicles(
    companyId: string,
    query?: string,
    ownerType?: string,
    limit = 50,
    offset = 0,
  ): Observable<{ items: VehicleItem[]; total: number }> {
    let url = `${this.base(companyId)}/vehicles?limit=${limit}&offset=${offset}`;
    if (query) url += `&query=${encodeURIComponent(query)}`;
    if (ownerType) url += `&ownerType=${encodeURIComponent(ownerType)}`;
    return this.http.get<{ items: VehicleItem[]; total: number }>(url);
  }

  createVehicle(companyId: string, data: Partial<VehicleItem>): Observable<VehicleItem> {
    return this.http.post<VehicleItem>(`${this.base(companyId)}/vehicles`, data);
  }

  updateVehicle(companyId: string, vehicleId: string, data: Partial<VehicleItem>): Observable<VehicleItem> {
    return this.http.put<VehicleItem>(`${this.base(companyId)}/vehicles/${vehicleId}`, data);
  }

  deleteVehicle(companyId: string, vehicleId: string): Observable<{ success: boolean; vehicleId: string }> {
    return this.http.delete<{ success: boolean; vehicleId: string }>(`${this.base(companyId)}/vehicles/${vehicleId}`);
  }

  scanLprBarrier(companyId: string, data: Record<string, unknown>): Observable<LprScanResult> {
    return this.http.post<LprScanResult>(`${this.base(companyId)}/parking/lpr-scan`, data);
  }

  getParkingTransactions(
    companyId: string,
    licensePlate?: string,
    limit = 50,
    offset = 0,
  ): Observable<{ items: ParkingTransactionItem[]; total: number }> {
    let url = `${this.base(companyId)}/parking/transactions?limit=${limit}&offset=${offset}`;
    if (licensePlate) url += `&licensePlate=${encodeURIComponent(licensePlate)}`;
    return this.http.get<{ items: ParkingTransactionItem[]; total: number }>(url);
  }

  // =========================================================================
  // P3: RFID Physical Access Card APIs
  // =========================================================================

  getRfidCards(
    companyId: string,
    query?: string,
    cardStatus?: string,
    assignedType?: string,
    limit = 50,
    offset = 0,
  ): Observable<{ items: RfidCardItem[]; total: number }> {
    let url = `${this.base(companyId)}/rfid-cards?limit=${limit}&offset=${offset}`;
    if (query) url += `&query=${encodeURIComponent(query)}`;
    if (cardStatus) url += `&cardStatus=${encodeURIComponent(cardStatus)}`;
    if (assignedType) url += `&assignedType=${encodeURIComponent(assignedType)}`;
    return this.http.get<{ items: RfidCardItem[]; total: number }>(url);
  }

  issueRfidCard(companyId: string, data: Partial<RfidCardItem>): Observable<RfidCardItem> {
    return this.http.post<RfidCardItem>(`${this.base(companyId)}/rfid-cards`, data);
  }

  updateRfidCard(companyId: string, cardId: string, data: Partial<RfidCardItem>): Observable<RfidCardItem> {
    return this.http.put<RfidCardItem>(`${this.base(companyId)}/rfid-cards/${cardId}`, data);
  }

  updateRfidCardStatus(companyId: string, cardId: string, cardStatus: string, notes?: string): Observable<RfidCardItem> {
    return this.http.put<RfidCardItem>(`${this.base(companyId)}/rfid-cards/${cardId}/status`, { cardStatus, notes });
  }

  deleteRfidCard(companyId: string, cardId: string): Observable<{ success: boolean; cardId: string }> {
    return this.http.delete<{ success: boolean; cardId: string }>(`${this.base(companyId)}/rfid-cards/${cardId}`);
  }

  verifyRfidAccess(companyId: string, data: Record<string, unknown>): Observable<RfidVerificationResult> {
    return this.http.post<RfidVerificationResult>(`${this.base(companyId)}/access/verify-rfid`, data);
  }
}
