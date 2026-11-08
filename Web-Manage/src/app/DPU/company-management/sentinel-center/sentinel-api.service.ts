import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/** All `/sentinel/company/{id}/*` HttpClient paths. */
@Injectable({ providedIn: 'root' })
export class SentinelApiService {
  constructor(private http: HttpClient) {}

  private base(companyId: string): string {
    return `/sentinel/company/${companyId}`;
  }

  getOverview(companyId: string): Observable<any> {
    return this.http.get(`${this.base(companyId)}/overview`);
  }

  getIdentities(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.base(companyId)}/identities`);
  }

  createIdentity(companyId: string, body: unknown): Observable<any> {
    return this.http.post<any>(`${this.base(companyId)}/identities`, body);
  }

  enrollIdentityFace(companyId: string, identityId: string, file: File): Observable<any> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post(`${this.base(companyId)}/identities/${identityId}/enroll-face`, fd);
  }

  deleteIdentity(companyId: string, identityId: string): Observable<any> {
    return this.http.delete(`${this.base(companyId)}/identities/${identityId}`);
  }

  getZones(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.base(companyId)}/zones`);
  }

  createZone(companyId: string, body: unknown): Observable<any> {
    return this.http.post(`${this.base(companyId)}/zones`, body);
  }

  triggerZone(companyId: string, zoneId: string, reason: string): Observable<any> {
    return this.http.post(`${this.base(companyId)}/zones/${zoneId}/trigger`, { reason });
  }

  deleteZone(companyId: string, zoneId: string): Observable<any> {
    return this.http.delete(`${this.base(companyId)}/zones/${zoneId}`);
  }

  getEvents(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.base(companyId)}/events`);
  }

  createEvent(companyId: string, body: unknown): Observable<any> {
    return this.http.post(`${this.base(companyId)}/events`, body);
  }

  deleteEvent(companyId: string, eventId: string): Observable<any> {
    return this.http.delete(`${this.base(companyId)}/events/${eventId}`);
  }

  getIncidents(
    companyId: string,
    severity?: string,
    status?: string
  ): Observable<any[]> {
    const params: string[] = [];
    if (severity) params.push(`severity=${encodeURIComponent(severity)}`);
    if (status) params.push(`status=${encodeURIComponent(status)}`);
    const q = params.length ? `?${params.join('&')}` : '';
    return this.http.get<any[]>(`${this.base(companyId)}/incidents${q}`);
  }

  acknowledgeIncident(companyId: string, incidentId: string): Observable<any> {
    return this.http.post(`${this.base(companyId)}/incidents/${incidentId}/acknowledge`, {});
  }

  assignIncident(
    companyId: string,
    incidentId: string,
    body: { assignedTo?: string } = {}
  ): Observable<any> {
    return this.http.post(`${this.base(companyId)}/incidents/${incidentId}/assign`, body);
  }

  closeIncident(companyId: string, incidentId: string): Observable<any> {
    return this.http.post(`${this.base(companyId)}/incidents/${incidentId}/close`, {});
  }

  getEdgeSync(companyId: string): Observable<any> {
    return this.http.get(`${this.base(companyId)}/edge-sync`);
  }

  unifiedScan(companyId: string, formData: FormData): Observable<any> {
    return this.http.post(`${this.base(companyId)}/scan`, formData);
  }
}
