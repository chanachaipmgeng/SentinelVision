import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ApprovalInboxItem {
  kind: 'LEAVE' | 'TIMESTAMP' | 'REGULARIZATION' | 'OT' | string;
  requestId?: string;
  leaveId?: string;
  timestampId?: string;
  company_employeeId?: string;
  employeeName?: string;
  employeeId?: string;
  status?: string | number;
  statusText?: string;
  approvalStatus?: string;
  reason?: string;
  note?: string;
  locationName?: string;
  workDate?: string;
  timestamp?: string;
  otMinutes?: number;
  createdAt?: string;
}

@Injectable({ providedIn: 'root' })
export class ApprovalService {
  constructor(private http: HttpClient) {}

  inbox(companyId: string, status = 'PENDING'): Observable<{ items: ApprovalInboxItem[]; total: number }> {
    return this.http.get<{ items: ApprovalInboxItem[]; total: number }>(
      `/hr/company/${companyId}/approvals`,
      { params: { status_filter: status } }
    );
  }

  decideLeave(companyId: string, leaveId: string, body: { approve: boolean; rejectReason?: string }) {
    return this.http.post(`/hr/company/${companyId}/leaves/${leaveId}/approval`, body);
  }

  decideRegularization(
    companyId: string,
    requestId: string,
    body: { approve: boolean; rejectReason?: string }
  ) {
    return this.http.post(`/hr/company/${companyId}/regularizations/${requestId}/approval`, body);
  }

  decideOt(companyId: string, requestId: string, body: { approve: boolean; rejectReason?: string }) {
    return this.http.post(`/hr/company/${companyId}/ot-approvals/${requestId}/approval`, body);
  }

  listPayrollPeriods(companyId: string) {
    return this.http.get<{ items: unknown[] }>(`/hr/company/${companyId}/payroll-periods`);
  }

  createPayrollPeriod(companyId: string, body: { name?: string; startDate: string; endDate: string }) {
    return this.http.post(`/hr/company/${companyId}/payroll-periods`, body);
  }

  closePayrollPeriod(companyId: string, periodId: string) {
    return this.http.post(`/hr/company/${companyId}/payroll-periods/${periodId}/close`, {});
  }
}
