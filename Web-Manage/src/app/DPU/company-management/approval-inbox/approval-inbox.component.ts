import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampService } from '../../services/timestamp.service';
import { ApprovalInboxItem, ApprovalService } from '../../services/approval.service';
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
  TIMESTAMP: 'ri-map-pin-warning-line',
  REGULARIZATION: 'ri-time-line',
  OT: 'ri-timer-flash-line',
};

@Component({
  selector: 'app-approval-inbox',
  standalone: true,
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
  encapsulation: ViewEncapsulation.None,
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

  get pendingCount(): number {
    return this.items.length;
  }

  constructor(
    private approvals: ApprovalService,
    private timestamps: TimestampService,
    private token: TokenService
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    this.kpis = this.buildKpis();
  }

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    const keep = this.selectedKey(this.selected);
    this.approvals.inbox(this.companyId, 'PENDING').subscribe({
      next: (res) => {
        this.items = res.items || [];
        this.applyFilter(keep);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        swal('Error', 'โหลดกล่องอนุมัติไม่สำเร็จ', 'error');
      },
    });
  }

  applyFilter(preferKey?: string): void {
    const q = (this._searchTerm || '').trim().toLowerCase();
    const kind = this.kindFilter;
    this.filtered = this.items.filter(
      (x) => (!kind || x.kind === kind) && (!q || this.haystack(x).includes(q))
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

  onKpiClick(key: string): void {
    this.setKind(key === 'ALL' || key === this.kindFilter ? '' : key);
  }

  applySavedView(filters: Partial<ApprovalInboxViewFilters> | null): void {
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
      content: { element: 'input', attributes: { placeholder: 'เหตุผล (ถ้ามี)' } } as any,
      icon: 'warning',
      dangerMode: true,
      buttons: ['ยกเลิก', 'ไม่อนุมัติ'],
    }).then((reason: any) => {
      if (reason === null || reason === false) return;
      const rejectReason = typeof reason === 'string' ? reason : 'ไม่อนุมัติ';
      this.decide(item, false, rejectReason);
    });
  }

  private decide(item: ApprovalInboxItem, approve: boolean, rejectReason?: string): void {
    if (this.actionBusy || !this.companyId) return;
    this.actionBusy = true;
    const body = { approve, rejectReason };
    let req;
    if (item.kind === 'LEAVE' && item.leaveId) {
      req = this.approvals.decideLeave(this.companyId, item.leaveId, body);
    } else if (item.kind === 'REGULARIZATION' && item.requestId) {
      req = this.approvals.decideRegularization(this.companyId, item.requestId, body);
    } else if (item.kind === 'OT' && item.requestId) {
      req = this.approvals.decideOt(this.companyId, item.requestId, body);
    } else if (item.kind === 'TIMESTAMP' && item.timestampId) {
      // JWT sets approvedBy server-side — do not send client memberId.
      req = this.timestamps.approve(this.companyId, item.timestampId, {
        approve,
        rejectReason,
      });
    } else {
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
