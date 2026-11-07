import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampService } from '../../services/timestamp.service';
import { ApprovalInboxItem, ApprovalService } from '../../services/approval.service';
import swal from 'sweetalert';

@Component({
  selector: 'app-approval-inbox',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule, RouterModule],
  templateUrl: './approval-inbox.component.html',
  styleUrls: ['./approval-inbox.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class ApprovalInboxComponent implements OnInit {
  companyId = '';
  loading = false;
  actionBusy = false;
  items: ApprovalInboxItem[] = [];
  selected?: ApprovalInboxItem;
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
    this.filtered = !q
      ? [...this.items]
      : this.items.filter((x) => this.haystack(x).includes(q));
    if (!this.filtered.length) {
      this.selected = undefined;
      return;
    }
    const preferred =
      (preferKey && this.filtered.find((x) => this.selectedKey(x) === preferKey)) ||
      (this.selected && this.filtered.find((x) => this.selectedKey(x) === this.selectedKey(this.selected)));
    this.selected = preferred || this.filtered[0];
  }

  select(item: ApprovalInboxItem): void {
    this.selected = item;
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
