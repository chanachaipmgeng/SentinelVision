import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
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
@Injectable({ providedIn: 'root' })
export class SentinelApiService {
  constructor(private http: HttpClient) {}

  private base(companyId: string): string {
    return `/sentinel/company/${companyId}`;
  }

  getOverview(companyId: string): Observable<SentinelOverview> {
    return this.http.get<SentinelOverview>(`${this.base(companyId)}/overview`);
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

  triggerZone(companyId: string, zoneId: string, reason: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.base(companyId)}/zones/${zoneId}/trigger`, { reason });
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
}
