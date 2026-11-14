import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { PermissionService } from '../../../shared/services/permission.service';
import { TimestampService } from '../../services/timestamp.service';
import {
  ApprovalDelegationItem,
  ApprovalInboxItem,
  ApprovalLevelConfig,
  ApprovalService,
} from '../../services/approval.service';
import { KpiGridComponent, KpiItem } from '../../../shared/components/kpi-grid/kpi-grid.component';
import { SavedViewsBarComponent } from '../../../shared/components/saved-views-bar/saved-views-bar.component';
import { SideDrawerComponent } from '../../../shared/components/side-drawer/side-drawer.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import swal from 'sweetalert';

interface ApprovalInboxViewFilters {
  q: string;
  kind: string;
}

const KIND_ICONS: Record<string, string> = {
  LEAVE: 'ri-calendar-event-line',
  TIMESTAMP: 'ri-map-pin-range-line',
  REGULARIZATION: 'ri-time-line',
  OT: 'ri-timer-flash-line',
};

@Component({
    selector: 'app-approval-inbox',
    imports: [
        CommonModule,
        FormsModule,
        SharedModule,
        RouterModule,
        KpiGridComponent,
        SavedViewsBarComponent,
        SideDrawerComponent,
        SkeletonLoaderComponent,
    ],
    templateUrl: './approval-inbox.component.html',
    styleUrls: ['./approval-inbox.component.css', '../../../shared/styles/dpu-filter-toolbar.css'],
    encapsulation: ViewEncapsulation.None
})
export class ApprovalInboxComponent implements OnInit {
  readonly kinds = ['LEAVE', 'TIMESTAMP', 'REGULARIZATION', 'OT'];

  companyId = '';
  loading = false;
  actionBusy = false;
  drawerOpen = false;
  items: ApprovalInboxItem[] = [];
  selected?: ApprovalInboxItem;
  kindFilter = '';
  locationFilter = '';
  kpis: KpiItem[] = [];
  savedFilters: ApprovalInboxViewFilters = { q: '', kind: '' };
  private _searchTerm = '';

  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this._searchTerm = val;
    this.applyFilter();
  }

  filtered: ApprovalInboxItem[] = [];
  selectedKeys = new Set<string>();

  showChainPanel = false;
  chainBusy = false;
  chainDepth = 1;
  approvalLevels: ApprovalLevelConfig[] = [];
  delegations: ApprovalDelegationItem[] = [];
  delegateMembers: { id: string; label: string }[] = [];
  delegationForm = {
    delegateMemberId: '',
    startDate: '',
    endDate: '',
    reason: '',
  };

  get pendingCount(): number {
    return this.items.length;
  }

  get selectedCount(): number {
    return this.selectedKeys.size;
  }

  get allFilteredSelected(): boolean {
    return this.filtered.length > 0 && this.filtered.every((item) => this.selectedKeys.has(this.selectedKey(item)));
  }

  constructor(
    private approvals: ApprovalService,
    private timestamps: TimestampService,
    private token: TokenService,
    private http: HttpClient,
    public permissions: PermissionService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    this.kpis = this.buildKpis();
  }

  ngOnInit(): void {
    this.reload();
    this.loadChainAndDelegations();
  }

  toggleChainPanel(): void {
    this.showChainPanel = !this.showChainPanel;
    if (this.showChainPanel) {
      this.loadChainAndDelegations();
    }
  }

  loadChainAndDelegations(): void {
    if (!this.companyId) return;
    forkJoin({
      policy: this.approvals.getApprovalPolicy(this.companyId).pipe(catchError(() => of({ levels: [] }))),
      delegations: this.approvals.listDelegations(this.companyId).pipe(catchError(() => of({ items: [], total: 0 }))),
      employees: this.http.get<unknown[]>(`/employees/company/${this.companyId}`).pipe(catchError(() => of([]))),
    }).subscribe({
      next: (res) => {
        this.approvalLevels = res.policy.levels || [];
        this.chainDepth = Math.max(1, Math.min(3, this.approvalLevels.length || 1));
        this.delegations = res.delegations.items || [];
        const seen = new Set<string>();
        this.delegateMembers = [];
        for (const raw of (Array.isArray(res.employees) ? res.employees : []) as Record<string, unknown>[]) {
          const m = (raw['member'] as Record<string, unknown>) || raw;
          const mid = String(m['memberId'] || raw['memberId'] || '');
          if (!mid || seen.has(mid)) continue;
          seen.add(mid);
          const name = `${String(m['firstName'] || '')} ${String(m['lastName'] || '')}`.trim() || String(m['username'] || mid);
          this.delegateMembers.push({ id: mid, label: name });
        }
      },
    });
  }

  saveChainDepth(): void {
    if (!this.companyId || this.chainBusy) return;
    const levels: ApprovalLevelConfig[] =
      this.chainDepth === 3
        ? [
            { level: 1, role: 'MANAGER', label: 'Line Manager' },
            { level: 2, role: 'MANAGER', label: 'Department Manager' },
            { level: 3, role: 'HR_ADMIN', label: 'HR Final' },
          ]
        : this.chainDepth === 2
          ? [
              { level: 1, role: 'MANAGER', label: 'Line Manager' },
              { level: 2, role: 'HR_ADMIN', label: 'HR Final' },
            ]
          : [{ level: 1, role: 'MANAGER', label: 'Line Manager' }];
    this.chainBusy = true;
    this.approvals.saveApprovalPolicy(this.companyId, { requestType: 'ALL', levels }).subscribe({
      next: (res) => {
        this.chainBusy = false;
        this.approvalLevels = res.levels || levels;
        swal('สำเร็จ', 'บันทึกสายอนุมัติแล้ว', 'success');
      },
      error: (err) => {
        this.chainBusy = false;
        swal('Error', err?.error?.detail || 'บันทึกสายอนุมัติไม่สำเร็จ', 'error');
      },
    });
  }

  addDelegation(): void {
    if (!this.companyId || this.chainBusy) return;
    if (!this.delegationForm.delegateMemberId || !this.delegationForm.startDate || !this.delegationForm.endDate) return;
    this.chainBusy = true;
    this.approvals.createDelegation(this.companyId, this.delegationForm).subscribe({
      next: () => {
        this.chainBusy = false;
        this.delegationForm = { delegateMemberId: '', startDate: '', endDate: '', reason: '' };
        swal('สำเร็จ', 'ตั้งค่าผู้อนุมัติแทนแล้ว', 'success');
        this.loadChainAndDelegations();
      },
      error: (err) => {
        this.chainBusy = false;
        swal('Error', err?.error?.detail || 'ตั้งค่าผู้อนุมัติแทนไม่สำเร็จ', 'error');
      },
    });
  }

  removeDelegation(d: ApprovalDelegationItem): void {
    if (!this.companyId || this.chainBusy) return;
    this.chainBusy = true;
    this.approvals.deleteDelegation(this.companyId, d.delegationId).subscribe({
      next: () => {
        this.chainBusy = false;
        this.loadChainAndDelegations();
      },
      error: (err) => {
        this.chainBusy = false;
        swal('Error', err?.error?.detail || 'ลบผู้อนุมัติแทนไม่สำเร็จ', 'error');
      },
    });
  }

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    const keep = this.selectedKey(this.selected);
    this.approvals.inbox(this.companyId, 'PENDING').subscribe({
      next: (res) => {
        this.items = res.items || [];
        this.selectedKeys.clear();
        this.applyFilter(keep);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดกล่องอนุมัติไม่สำเร็จ', 'error');
      },
    });
  }

  get locations(): string[] {
    const set = new Set<string>();
    for (const item of this.items) {
      if (item.locationName) set.add(item.locationName);
    }
    return Array.from(set).sort();
  }

  applyFilter(preferKey?: string): void {
    const q = (this._searchTerm || '').trim().toLowerCase();
    const kind = this.kindFilter;
    const loc = this.locationFilter;
    this.filtered = this.items.filter(
      (x) =>
        (!kind || x.kind === kind) &&
        (!loc || x.locationName === loc) &&
        (!q || this.haystack(x).includes(q))
    );
    this.kpis = this.buildKpis();
    this.savedFilters = { q: this._searchTerm || '', kind };
    const key = preferKey || this.selectedKey(this.selected);
    this.selected = key ? this.filtered.find((x) => this.selectedKey(x) === key) : undefined;
    if (!this.selected) this.drawerOpen = false;
  }

  select(item: ApprovalInboxItem): void {
    this.selected = item;
    this.drawerOpen = true;
  }

  setKind(kind: string): void {
    this.kindFilter = kind || '';
    this.applyFilter();
  }

  setLocation(loc: string): void {
    this.locationFilter = loc || '';
    this.applyFilter();
  }

  onKpiClick(key: string): void {
    this.setKind(key === 'ALL' || key === this.kindFilter ? '' : key);
  }

  applySavedView(raw: unknown): void {
    const filters = raw as Partial<ApprovalInboxViewFilters> | null;
    if (!filters) return;
    this.kindFilter = filters.kind || '';
    this._searchTerm = filters.q || '';
    this.applyFilter();
  }

  isSelected(item: ApprovalInboxItem): boolean {
    return this.selectedKey(this.selected) === this.selectedKey(item);
  }

  kindLabel(item: ApprovalInboxItem): string {
    switch (item.kind) {
      case 'LEAVE':
        return 'ลา';
      case 'TIMESTAMP':
        return 'นอกพื้นที่';
      case 'REGULARIZATION':
        return 'แก้เวลา';
      case 'OT':
        return 'OT';
      default:
        return item.kind || '—';
    }
  }

  approve(item: ApprovalInboxItem): void {
    this.decide(item, true);
  }

  reject(item: ApprovalInboxItem): void {
    swal({
      title: 'ไม่อนุมัติรายการนี้?',
      text: item.employeeName || '',
      content: { element: 'input', attributes: { placeholder: 'เหตุผล (ถ้ามี)' } },
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ไม่อนุมัติ'],
    }).then((reason: unknown) => {
      if (reason === null || reason === false) return;
      const rejectReason = typeof reason === 'string' ? reason : 'ไม่อนุมัติ';
      this.decide(item, false, rejectReason);
    });
  }

  isChecked(item: ApprovalInboxItem): boolean {
    return this.selectedKeys.has(this.selectedKey(item));
  }

  toggleCheck(item: ApprovalInboxItem, event: Event): void {
    event.stopPropagation();
    const key = this.selectedKey(item);
    if (!key) return;
    if ((event.target as HTMLInputElement).checked) {
      this.selectedKeys.add(key);
    } else {
      this.selectedKeys.delete(key);
    }
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.filtered.forEach((item) => {
        const key = this.selectedKey(item);
        if (key) this.selectedKeys.add(key);
      });
    } else {
      this.filtered.forEach((item) => this.selectedKeys.delete(this.selectedKey(item)));
    }
  }

  bulkApprove(): void {
    const targets = this.filtered.filter((item) => this.selectedKeys.has(this.selectedKey(item)));
    if (!targets.length || this.actionBusy || !this.companyId) return;
    swal({
      title: `อนุมัติทั้งหมด ${targets.length} รายการ?`,
      icon: 'info',
      buttons: ['ยกเลิก', 'อนุมัติทั้งหมด'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.runBulkDecision(targets, true);
    });
  }

  bulkReject(): void {
    const targets = this.filtered.filter((item) => this.selectedKeys.has(this.selectedKey(item)));
    if (!targets.length || this.actionBusy || !this.companyId) return;
    swal({
      title: `ไม่อนุมัติทั้งหมด ${targets.length} รายการ?`,
      content: { element: 'input', attributes: { placeholder: 'เหตุผล (ถ้ามี)' } },
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ไม่อนุมัติทั้งหมด'],
    }).then((reason: unknown) => {
      if (reason === null || reason === false) return;
      const rejectReason = typeof reason === 'string' && reason.trim() ? reason.trim() : 'ไม่อนุมัติ';
      this.runBulkDecision(targets, false, rejectReason);
    });
  }

  private runBulkDecision(targets: ApprovalInboxItem[], approve: boolean, rejectReason?: string): void {
    this.actionBusy = true;
    const calls: Observable<unknown>[] = targets.map((item) => {
      const req = this.buildDecisionRequest(item, approve, rejectReason);
      return req ? req.pipe(catchError(() => of({ __failed: true }))) : of({ __failed: true });
    });
    forkJoin(calls).subscribe({
      next: (results) => {
        this.actionBusy = false;
        const failed = results.filter((r) => (r as { __failed?: boolean })?.__failed).length;
        const succeeded = results.length - failed;
        if (failed === 0) {
          swal('สำเร็จ', `${approve ? 'อนุมัติ' : 'ไม่อนุมัติ'}แล้ว ${succeeded} รายการ`, 'success');
        } else {
          swal('แจ้งเตือน', `สำเร็จ ${succeeded} รายการ, ไม่สำเร็จ ${failed} รายการ`, 'warning');
        }
        this.reload();
      },
      error: () => {
        this.actionBusy = false;
        swal('Error', 'ดำเนินการแบบกลุ่มไม่สำเร็จ', 'error');
      },
    });
  }

  private buildDecisionRequest(item: ApprovalInboxItem, approve: boolean, rejectReason?: string): Observable<unknown> | null {
    const body = { approve, rejectReason };
    if (item.kind === 'LEAVE' && item.leaveId) {
      return this.approvals.decideLeave(this.companyId, item.leaveId, body);
    }
    if (item.kind === 'REGULARIZATION' && item.requestId) {
      return this.approvals.decideRegularization(this.companyId, item.requestId, body);
    }
    if (item.kind === 'OT' && item.requestId) {
      return this.approvals.decideOt(this.companyId, item.requestId, body);
    }
    if (item.kind === 'TIMESTAMP' && item.timestampId) {
      return this.timestamps.approve(this.companyId, item.timestampId, { approve, rejectReason });
    }
    return null;
  }

  private decide(item: ApprovalInboxItem, approve: boolean, rejectReason?: string): void {
    if (this.actionBusy || !this.companyId) return;
    this.actionBusy = true;
    const req = this.buildDecisionRequest(item, approve, rejectReason);
    if (!req) {
      this.actionBusy = false;
      swal('Error', 'ไม่รองรับประเภทนี้', 'error');
      return;
    }
    req.subscribe({
      next: () => {
        this.actionBusy = false;
        swal('สำเร็จ', approve ? 'อนุมัติแล้ว' : 'ไม่อนุมัติแล้ว', 'success');
        this.reload();
      },
      error: (err) => {
        this.actionBusy = false;
        const detail = err?.error?.detail || 'ดำเนินการไม่สำเร็จ';
        swal('Error', detail, 'error');
      },
    });
  }

  clearSearch(): void {
    this.searchTerm = '';
  }

  itemDelay(i: number): number {
    return Math.min(i, 8) * 40;
  }

  private buildKpis(): KpiItem[] {
    const count = (kind: string) => this.items.filter((x) => x.kind === kind).length;
    return [
      {
        key: 'ALL',
        label: 'listKit.approvalInbox.kpiAll',
        value: this.items.length,
        icon: 'ri-inbox-line',
        tone: 'brand',
      },
      ...this.kinds.map(
        (kind): KpiItem => ({
          key: kind,
          label: `listKit.approvalInbox.kind.${kind}`,
          value: count(kind),
          icon: KIND_ICONS[kind],
          tone: count(kind) ? 'warning' : 'muted',
        })
      ),
    ];
  }

  private selectedKey(item?: ApprovalInboxItem): string {
    if (!item) return '';
    return `${item.kind}:${item.leaveId || item.requestId || item.timestampId || ''}`;
  }

  private haystack(item: ApprovalInboxItem): string {
    return [
      item.kind,
      item.employeeName,
      item.employeeId,
      item.reason,
      item.note,
      item.locationName,
      item.workDate,
    ]
      .join(' ')
      .toLowerCase();
  }
}
