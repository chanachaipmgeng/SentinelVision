import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ApprovalHistoryEntry {
  level: number;
  roleLabel: string;
  approverMemberId?: string | null;
  approverName?: string;
  delegatedFromMemberId?: string | null;
  action: 'APPROVED' | 'REJECTED' | string;
  comment?: string | null;
  decidedAt?: string;
}

export interface ApprovalLevelConfig {
  level: number;
  role: string;
  label: string;
}

export interface ApprovalDelegationItem {
  delegationId: string;
  companyId: string;
  delegatorMemberId: string;
  delegatorName?: string;
  delegateMemberId: string;
  delegateName?: string;
  startDate: string;
  endDate: string;
  reason?: string;
  isActive: boolean;
  createdAt?: string;
}

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
  approvalLevel?: number;
  maxApprovalLevel?: number;
  currentLevelLabel?: string;
  approvalHistory?: ApprovalHistoryEntry[];
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

  getApprovalPolicy(companyId: string, requestType = 'ALL'): Observable<{ levels: ApprovalLevelConfig[] }> {
    return this.http.get<{ levels: ApprovalLevelConfig[] }>(
      `/hr/company/${companyId}/approval-policy`,
      { params: { request_type: requestType } }
    );
  }

  saveApprovalPolicy(
    companyId: string,
    body: { requestType?: string; levels: ApprovalLevelConfig[] }
  ): Observable<{ levels: ApprovalLevelConfig[] }> {
    return this.http.put<{ levels: ApprovalLevelConfig[] }>(
      `/hr/company/${companyId}/approval-policy`,
      body
    );
  }

  listDelegations(companyId: string): Observable<{ items: ApprovalDelegationItem[]; total: number }> {
    return this.http.get<{ items: ApprovalDelegationItem[]; total: number }>(
      `/hr/company/${companyId}/approval-delegations`
    );
  }

  createDelegation(
    companyId: string,
    body: { delegateMemberId: string; startDate: string; endDate: string; reason?: string }
  ): Observable<ApprovalDelegationItem> {
    return this.http.post<ApprovalDelegationItem>(
      `/hr/company/${companyId}/approval-delegations`,
      body
    );
  }

  deleteDelegation(companyId: string, delegationId: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(
      `/hr/company/${companyId}/approval-delegations/${delegationId}`
    );
  }
}
