import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RbacRoleInfo {
  code: string;
  label: string;
  description: string;
  permissions: string[];
}

export interface MemberRoleAssignmentItem {
  assignmentId: string;
  memberId: string;
  memberName?: string;
  memberEmail?: string;
  companyId: string | null;
  roleCode: string;
  roleLabel?: string;
  departmentId: string | null;
  departmentName?: string | null;
  locationId: string | null;
  locationName?: string | null;
  createdAt?: string;
}

@Injectable({ providedIn: 'root' })
export class RbacService {
  constructor(private http: HttpClient) {}

  getRoles(): Observable<{ roles: RbacRoleInfo[]; permissions: string[] }> {
    return this.http.get<{ roles: RbacRoleInfo[]; permissions: string[] }>('/rbac/roles');
  }

  listAssignments(companyId: string): Observable<{ items: MemberRoleAssignmentItem[]; total: number }> {
    return this.http.get<{ items: MemberRoleAssignmentItem[]; total: number }>(
      `/rbac/company/${companyId}/assignments`
    );
  }

  createAssignment(
    companyId: string,
    body: {
      memberId: string;
      roleCode: string;
      departmentId?: string | null;
      locationId?: string | null;
    }
  ): Observable<MemberRoleAssignmentItem> {
    return this.http.post<MemberRoleAssignmentItem>(`/rbac/company/${companyId}/assignments`, body);
  }

  deleteAssignment(companyId: string, assignmentId: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(
      `/rbac/company/${companyId}/assignments/${assignmentId}`
    );
  }
}
