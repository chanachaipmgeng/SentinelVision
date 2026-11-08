import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/** All HttpClient paths used by HR Schedule tabs. */
@Injectable({ providedIn: 'root' })
export class HrScheduleApiService {
  constructor(private http: HttpClient) {}

  // --- Shifts ---
  getShifts(companyId: string): Observable<any> {
    return this.http.get<any>(`/hr/company/${companyId}/shifts`);
  }

  createShift(companyId: string, body: unknown): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/shifts`, body);
  }

  deleteShift(companyId: string, shiftId: string): Observable<any> {
    return this.http.delete(`/hr/company/${companyId}/shifts/${shiftId}`);
  }

  assignShift(
    companyId: string,
    body: { departmentId?: string; company_employeeId?: string; shiftId: string | null },
  ): Observable<any> {
    return this.http.put(`/hr/company/${companyId}/assign-shift`, body);
  }

  // --- Lookups ---
  getDepartments(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`/departments/company/${companyId}`);
  }

  getEmployees(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`/employees/company/${companyId}`);
  }

  // --- Leaves ---
  getLeaves(companyId: string): Observable<any> {
    return this.http.get<any>(`/hr/company/${companyId}/leaves`);
  }

  createLeave(companyId: string, body: unknown): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/leaves`, body);
  }

  approveLeave(companyId: string, leaveId: string, status: number): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/leaves/${leaveId}/approval`, { status });
  }

  // --- Holidays ---
  getHolidays(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`/hr/company/${companyId}/holidays`);
  }

  createHoliday(companyId: string, body: unknown): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/holidays`, body);
  }

  deleteHoliday(companyId: string, holidayId: string): Observable<any> {
    return this.http.delete(`/hr/company/${companyId}/holidays/${holidayId}`);
  }

  applyThaiHolidayPreset(companyId: string, year: number): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/holidays/thai-preset`, { year });
  }

  importHolidays(companyId: string, form: FormData): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/holidays/import`, form);
  }

  // --- PDPA ---
  getPdpaSummary(companyId: string): Observable<any> {
    return this.http.get<any>(`/hr/company/${companyId}/pdpa-summary`);
  }

  getConsentPolicy(companyId: string): Observable<any> {
    return this.http.get<any>(`/hr/company/${companyId}/pdpa/consent-policy`);
  }

  putConsentPolicy(companyId: string, body: unknown): Observable<any> {
    return this.http.put(`/hr/company/${companyId}/pdpa/consent-policy`, body);
  }

  getRetention(companyId: string): Observable<any> {
    return this.http.get<any>(`/hr/company/${companyId}/pdpa/retention`);
  }

  putRetention(companyId: string, body: unknown): Observable<any> {
    return this.http.put(`/hr/company/${companyId}/pdpa/retention`, body);
  }

  grantBiometricConsent(companyId: string, memberId: string): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/members/${memberId}/biometric-consent`, {});
  }

  revokeBiometricConsent(companyId: string, memberId: string): Observable<any> {
    return this.http.delete(`/hr/company/${companyId}/members/${memberId}/biometric-consent`);
  }

  exportDsar(companyId: string, memberId: string): Observable<any> {
    return this.http.get(`/hr/company/${companyId}/members/${memberId}/dsar-export`);
  }

  // --- Kiosk ---
  getKioskDevices(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`/hr/company/${companyId}/kiosk-devices`);
  }

  createKioskDevice(companyId: string, name: string): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/kiosk-devices`, { name });
  }

  reissueKioskPairingCode(companyId: string, deviceId: string): Observable<any> {
    return this.http.post(`/hr/company/${companyId}/kiosk-devices/${deviceId}/pairing-code`, {});
  }

  revokeKioskDevice(companyId: string, deviceId: string): Observable<any> {
    return this.http.delete(`/hr/company/${companyId}/kiosk-devices/${deviceId}`);
  }

  // --- MFA ---
  getMfaStatus(): Observable<any> {
    return this.http.get<any>(`/auth/mfa/status`);
  }

  setupMfa(): Observable<any> {
    return this.http.post(`/auth/mfa/setup`, {});
  }

  enableMfa(code: string): Observable<any> {
    return this.http.post(`/auth/mfa/enable`, { code });
  }

  disableMfa(): Observable<any> {
    return this.http.post(`/auth/mfa/disable`, {});
  }

  // --- Observability / webhooks ---
  getObservabilitySummary(): Observable<any> {
    return this.http.get<any>(`/system/observability-summary`);
  }

  getNotifySettings(companyId: string): Observable<any> {
    return this.http.get<any>(`/notifications/company/${companyId}/settings`);
  }

  putNotifySettings(companyId: string, body: unknown): Observable<any> {
    return this.http.put(`/notifications/company/${companyId}/settings`, body);
  }

  getOutbox(companyId: string): Observable<any[]> {
    return this.http.get<any[]>(`/notifications/company/${companyId}/outbox`);
  }

  sendTestWebhook(companyId: string): Observable<any> {
    return this.http.post(`/notifications/company/${companyId}/test`, {});
  }
}
