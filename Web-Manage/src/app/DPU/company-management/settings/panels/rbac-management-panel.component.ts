import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { SharedModule } from '../../../../shared/shared.module';
import { TokenService } from '../../../../shared/services/token.service';
import {
  MemberRoleAssignmentItem,
  RbacRoleInfo,
  RbacService,
} from '../../../services/rbac.service';

interface SimpleOption {
  id: string;
  label: string;
}

@Component({
  selector: 'app-rbac-management-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  template: `
    <div class="space-y-4">
      <!-- Assign Role Form -->
      <div class="box modern-card glass">
        <div class="box-header flex items-center justify-between">
          <h6 class="box-title mb-0">{{ 'rbacPanel.assignTitle' | translate }}</h6>
        </div>
        <div class="box-body">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label class="form-label text-xs">{{ 'rbacPanel.member' | translate }}</label>
              <select class="form-control" [(ngModel)]="form.memberId">
                <option value="">-- {{ 'Select' | translate }} --</option>
                <option *ngFor="let m of members" [value]="m.id">{{ m.label }}</option>
              </select>
            </div>
            <div>
              <label class="form-label text-xs">{{ 'rbacPanel.role' | translate }}</label>
              <select class="form-control" [(ngModel)]="form.roleCode">
                <option *ngFor="let r of roles" [value]="r.code">
                  {{ r.label }} ({{ r.code }})
                </option>
              </select>
            </div>
            <div>
              <label class="form-label text-xs">{{ 'rbacPanel.departmentScope' | translate }}</label>
              <select class="form-control" [(ngModel)]="form.departmentId">
                <option value="">{{ 'rbacPanel.allCompany' | translate }}</option>
                <option *ngFor="let d of departments" [value]="d.id">{{ d.label }}</option>
              </select>
            </div>
            <div>
              <label class="form-label text-xs">{{ 'rbacPanel.branchScope' | translate }}</label>
              <select class="form-control" [(ngModel)]="form.locationId">
                <option value="">{{ 'rbacPanel.allBranches' | translate }}</option>
                <option *ngFor="let l of locations" [value]="l.id">{{ l.label }}</option>
              </select>
            </div>
          </div>
          <div class="mt-3 flex justify-end">
            <button
              type="button"
              class="ti-btn ti-btn-primary modern-btn"
              [disabled]="saving || !form.memberId || !form.roleCode"
              (click)="assignRole()"
            >
              <i class="ri-user-add-line"></i> {{ 'rbacPanel.assignBtn' | translate }}
            </button>
          </div>
        </div>
      </div>

      <!-- Current Assignments -->
      <div class="box modern-card glass">
        <div class="box-header flex items-center justify-between">
          <h6 class="box-title mb-0">{{ 'rbacPanel.assignmentsTitle' | translate }} ({{ assignments.length }})</h6>
        </div>
        <div class="box-body">
          <div *ngIf="loading" class="text-xs text-dpu-muted py-3">{{ 'Loading...' | translate }}</div>
          <div *ngIf="!loading && !assignments.length" class="text-xs text-dpu-muted py-3">
            {{ 'No data' | translate }}
          </div>
          <div *ngIf="!loading && assignments.length" class="table-responsive">
            <table class="table whitespace-nowrap min-w-full text-xs">
              <thead>
                <tr>
                  <th>{{ 'rbacPanel.member' | translate }}</th>
                  <th>{{ 'rbacPanel.role' | translate }}</th>
                  <th>{{ 'rbacPanel.departmentScope' | translate }}</th>
                  <th>{{ 'rbacPanel.branchScope' | translate }}</th>
                  <th class="text-end">{{ 'Action' | translate }}</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let a of assignments">
                  <td>
                    <div class="font-medium">{{ a.memberName || a.memberId }}</div>
                    <div class="text-[11px] text-dpu-muted" *ngIf="a.memberEmail">{{ a.memberEmail }}</div>
                  </td>
                  <td>
                    <span class="badge bg-primary/15 text-primary">{{ a.roleLabel || a.roleCode }}</span>
                  </td>
                  <td>{{ a.departmentName || ('rbacPanel.allCompany' | translate) }}</td>
                  <td>{{ a.locationName || ('rbacPanel.allBranches' | translate) }}</td>
                  <td class="text-end">
                    <button
                      type="button"
                      class="ti-btn ti-btn-outline-danger !py-1 !px-2 text-xs"
                      [disabled]="saving"
                      (click)="revoke(a)"
                    >
                      <i class="ri-delete-bin-line"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Role & Permission Matrix -->
      <div class="box modern-card glass">
        <div class="box-header">
          <h6 class="box-title mb-0">{{ 'rbacPanel.matrixTitle' | translate }}</h6>
        </div>
        <div class="box-body space-y-3">
          <div *ngFor="let r of roles" class="p-3 rounded-lg border border-white/10">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div>
                <strong class="text-sm">{{ r.label }}</strong>
                <span class="ms-2 text-xs text-dpu-muted">({{ r.code }})</span>
              </div>
              <span class="text-xs text-dpu-muted">{{ r.permissions.length }} permissions</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                *ngFor="let p of r.permissions"
                class="px-2 py-0.5 rounded text-[11px] bg-slate-500/15 border border-slate-400/20"
              >
                {{ p }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class RbacManagementPanelComponent implements OnInit {
  @Output() statusFlash = new EventEmitter<string>();

  companyId = '';
  loading = false;
  saving = false;
  roles: RbacRoleInfo[] = [];
  assignments: MemberRoleAssignmentItem[] = [];
  members: SimpleOption[] = [];
  departments: SimpleOption[] = [];
  locations: SimpleOption[] = [];

  form = {
    memberId: '',
    roleCode: 'MANAGER',
    departmentId: '',
    locationId: '',
  };

  constructor(
    private rbac: RbacService,
    private http: HttpClient,
    private token: TokenService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    if (!this.companyId) return;
    this.loading = true;
    forkJoin({
      roles: this.rbac.getRoles().pipe(catchError(() => of({ roles: [], permissions: [] }))),
      assignments: this.rbac.listAssignments(this.companyId).pipe(catchError(() => of({ items: [], total: 0 }))),
      employees: this.http.get<unknown[]>(`/employees/company/${this.companyId}`).pipe(catchError(() => of([]))),
      departments: this.http.get<unknown[]>(`/departments/company/${this.companyId}`).pipe(catchError(() => of([]))),
      locations: this.http.get<unknown[]>(`/company-locations/company/${this.companyId}`).pipe(catchError(() => of([]))),
    }).subscribe({
      next: (res) => {
        this.loading = false;
        this.roles = res.roles.roles || [];
        this.assignments = res.assignments.items || [];

        const empList = Array.isArray(res.employees) ? res.employees : [];
        const seenMembers = new Set<string>();
        this.members = [];
        for (const raw of empList as Record<string, unknown>[]) {
          const m = (raw['member'] as Record<string, unknown>) || raw;
          const mid = String(m['memberId'] || raw['memberId'] || '');
          if (!mid || seenMembers.has(mid)) continue;
          seenMembers.add(mid);
          const name = `${String(m['firstName'] || '')} ${String(m['lastName'] || '')}`.trim() || String(m['username'] || mid);
          this.members.push({ id: mid, label: name });
        }

        const deptList = Array.isArray(res.departments) ? res.departments : [];
        this.departments = (deptList as Record<string, unknown>[]).map((d) => ({
          id: String(d['departmentId'] || ''),
          label: String(d['departmentName'] || d['thName'] || d['engName'] || ''),
        })).filter((d) => d.id);

        const locList = Array.isArray(res.locations) ? res.locations : [];
        this.locations = (locList as Record<string, unknown>[]).map((l) => ({
          id: String(l['locationId'] || ''),
          label: String(l['locationName'] || ''),
        })).filter((l) => l.id);
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  assignRole(): void {
    if (!this.companyId || !this.form.memberId || !this.form.roleCode || this.saving) return;
    this.saving = true;
    this.rbac
      .createAssignment(this.companyId, {
        memberId: this.form.memberId,
        roleCode: this.form.roleCode,
        departmentId: this.form.departmentId || null,
        locationId: this.form.locationId || null,
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.statusFlash.emit('Assigned');
          this.loadAll();
        },
        error: () => {
          this.saving = false;
        },
      });
  }

  revoke(item: MemberRoleAssignmentItem): void {
    if (!this.companyId || this.saving) return;
    this.saving = true;
    this.rbac.deleteAssignment(this.companyId, item.assignmentId).subscribe({
      next: () => {
        this.saving = false;
        this.statusFlash.emit('Revoked');
        this.loadAll();
      },
      error: () => {
        this.saving = false;
      },
    });
  }
}
