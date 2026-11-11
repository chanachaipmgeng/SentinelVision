import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  HrEmployeeShiftRow,
  HrHoliday,
  HrKioskDevice,
  HrLeave,
  HrObservabilitySummary,
  HrPdpaSummary,
  HrShiftsResponse,
  HrDepartmentShiftRow,
  NotifyOutboxRow,
} from './hr-schedule.models';
import { defaultNotifySettings, defaultRetentionSettings } from './hr-schedule.helpers';

type RetentionSettings = ReturnType<typeof defaultRetentionSettings>;
type NotifySettings = ReturnType<typeof defaultNotifySettings>;
type ConsentPolicy = ReturnType<typeof import('./hr-schedule.helpers').defaultConsentPolicy>;

/** All HttpClient paths used by HR Schedule tabs. */
@Injectable({ providedIn: 'root' })
export class HrScheduleApiService {
  constructor(private http: HttpClient) {}

  // --- Shifts ---
  getShifts(companyId: string): Observable<HrShiftsResponse> {
    return this.http.get<HrShiftsResponse>(`/hr/company/${companyId}/shifts`);
  }

  createShift(companyId: string, body: Record<string, unknown>): Observable<HrShiftsResponse> {
    return this.http.post<HrShiftsResponse>(`/hr/company/${companyId}/shifts`, body);
  }

  deleteShift(companyId: string, shiftId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`/hr/company/${companyId}/shifts/${shiftId}`);
  }

  assignShift(
    companyId: string,
    body: { departmentId?: string; company_employeeId?: string; shiftId: string | null },
  ): Observable<Record<string, unknown>> {
    return this.http.put<Record<string, unknown>>(`/hr/company/${companyId}/assign-shift`, body);
  }

  // --- Lookups ---
  getDepartments(companyId: string): Observable<HrDepartmentShiftRow[]> {
    return this.http.get<HrDepartmentShiftRow[]>(`/departments/company/${companyId}`);
  }

  getEmployees(companyId: string): Observable<HrEmployeeShiftRow[]> {
    return this.http.get<HrEmployeeShiftRow[]>(`/employees/company/${companyId}`);
  }

  // --- Leaves ---
  getLeaves(companyId: string): Observable<HrLeave[] | { items?: HrLeave[] }> {
    return this.http.get<HrLeave[] | { items?: HrLeave[] }>(`/hr/company/${companyId}/leaves`);
  }

  createLeave(companyId: string, body: Record<string, unknown>): Observable<HrLeave> {
    return this.http.post<HrLeave>(`/hr/company/${companyId}/leaves`, body);
  }

  approveLeave(companyId: string, leaveId: string, status: number): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/hr/company/${companyId}/leaves/${leaveId}/approval`, { status });
  }

  // --- Holidays ---
  getHolidays(companyId: string): Observable<HrHoliday[]> {
    return this.http.get<HrHoliday[]>(`/hr/company/${companyId}/holidays`);
  }

  createHoliday(companyId: string, body: Record<string, unknown>): Observable<HrHoliday> {
    return this.http.post<HrHoliday>(`/hr/company/${companyId}/holidays`, body);
  }

  deleteHoliday(companyId: string, holidayId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`/hr/company/${companyId}/holidays/${holidayId}`);
  }

  applyThaiHolidayPreset(companyId: string, year: number): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/hr/company/${companyId}/holidays/thai-preset`, { year });
  }

  importHolidays(companyId: string, form: FormData): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/hr/company/${companyId}/holidays/import`, form);
  }

  // --- PDPA ---
  getPdpaSummary(companyId: string): Observable<HrPdpaSummary> {
    return this.http.get<HrPdpaSummary>(`/hr/company/${companyId}/pdpa-summary`);
  }

  getConsentPolicy(companyId: string): Observable<ConsentPolicy> {
    return this.http.get<ConsentPolicy>(`/hr/company/${companyId}/pdpa/consent-policy`);
  }

  putConsentPolicy(companyId: string, body: ConsentPolicy): Observable<ConsentPolicy> {
    return this.http.put<ConsentPolicy>(`/hr/company/${companyId}/pdpa/consent-policy`, body);
  }

  getRetention(companyId: string): Observable<RetentionSettings> {
    return this.http.get<RetentionSettings>(`/hr/company/${companyId}/pdpa/retention`);
  }

  putRetention(companyId: string, body: RetentionSettings): Observable<RetentionSettings> {
    return this.http.put<RetentionSettings>(`/hr/company/${companyId}/pdpa/retention`, body);
  }

  grantBiometricConsent(companyId: string, memberId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/hr/company/${companyId}/members/${memberId}/biometric-consent`, {});
  }

  revokeBiometricConsent(companyId: string, memberId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`/hr/company/${companyId}/members/${memberId}/biometric-consent`);
  }

  exportDsar(companyId: string, memberId: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`/hr/company/${companyId}/members/${memberId}/dsar-export`);
  }

  // --- Kiosk ---
  getKioskDevices(companyId: string): Observable<HrKioskDevice[]> {
    return this.http.get<HrKioskDevice[]>(`/hr/company/${companyId}/kiosk-devices`);
  }

  createKioskDevice(companyId: string, name: string): Observable<HrKioskDevice> {
    return this.http.post<HrKioskDevice>(`/hr/company/${companyId}/kiosk-devices`, { name });
  }

  reissueKioskPairingCode(companyId: string, deviceId: string): Observable<HrKioskDevice> {
    return this.http.post<HrKioskDevice>(`/hr/company/${companyId}/kiosk-devices/${deviceId}/pairing-code`, {});
  }

  revokeKioskDevice(companyId: string, deviceId: string): Observable<Record<string, unknown>> {
    return this.http.delete<Record<string, unknown>>(`/hr/company/${companyId}/kiosk-devices/${deviceId}`);
  }

  // --- MFA ---
  getMfaStatus(): Observable<{ username?: string; totpEnabled?: boolean }> {
    return this.http.get<{ username?: string; totpEnabled?: boolean }>(`/auth/mfa/status`);
  }

  setupMfa(): Observable<{ secret?: string; otpauthUri?: string }> {
    return this.http.post<{ secret?: string; otpauthUri?: string }>(`/auth/mfa/setup`, {});
  }

  enableMfa(code: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/auth/mfa/enable`, { code });
  }

  disableMfa(): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/auth/mfa/disable`, {});
  }

  // --- Observability / webhooks ---
  getObservabilitySummary(): Observable<HrObservabilitySummary> {
    return this.http.get<HrObservabilitySummary>(`/system/observability-summary`);
  }

  getNotifySettings(companyId: string): Observable<NotifySettings> {
    return this.http.get<NotifySettings>(`/notifications/company/${companyId}/settings`);
  }

  putNotifySettings(companyId: string, body: NotifySettings): Observable<NotifySettings> {
    return this.http.put<NotifySettings>(`/notifications/company/${companyId}/settings`, body);
  }

  getOutbox(companyId: string): Observable<NotifyOutboxRow[]> {
    return this.http.get<NotifyOutboxRow[]>(`/notifications/company/${companyId}/outbox`);
  }

  sendTestWebhook(companyId: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/notifications/company/${companyId}/test`, {});
  }
}
