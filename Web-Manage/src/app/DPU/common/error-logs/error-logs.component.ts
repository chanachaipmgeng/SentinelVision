import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  DataTableColumn,
  DataTableComponent,
  DataTableSortChange,
} from '../../../shared/components/data-table/data-table.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { SharedModule } from '../../../shared/shared.module';
import {
  SortDir,
  buildDataTableQuery,
  clampPageIndex,
  normalizePageEnvelope,
  PageEnvelope,
  toDataTableParams,
} from '../../../shared/utils/data-table-query';
import { apiErrorMessage } from '../../../shared/utils/http-error-body';
import swal from 'sweetalert';

interface ErrorLogRow {
  id: string;
  occurredAt: string | null;
  lastSeenAt: string | null;
  hitCount: number;
  source: string;
  statusCode: number;
  method: string | null;
  path: string | null;
  errorCode: string | null;
  message: string;
  exceptionType: string | null;
  requestId: string | null;
  traceId: string | null;
  companyId: string | null;
  actorMemberId: string | null;
  pageUrl: string | null;
  userAgent: string | null;
  ip: string | null;
  fingerprint: string;
  detail: unknown;
  resolvedAt: string | null;
  resolvedBy: string | null;
  stack?: string | null;
}

@Component({
  selector: 'app-error-logs',
  imports: [
    CommonModule,
    FormsModule,
    SharedModule,
    PageToolbarComponent,
    PillSearchComponent,
    DataTableComponent,
  ],
  templateUrl: './error-logs.component.html',
  styleUrls: [
    '../../../shared/styles/dpu-list-page.css',
    './error-logs.component.css',
  ],
  encapsulation: ViewEncapsulation.None,
})
export class ErrorLogsComponent implements OnInit, OnDestroy {
  rows: ErrorLogRow[] = [];
  total = 0;
  loading = false;
  pageIndex = 0;
  pageSize = 25;
  sortBy: string | null = 'lastSeenAt';
  sortDir: SortDir | null = 'desc';
  selected: ErrorLogRow | null = null;
  detailLoading = false;
  filters = {
    q: '',
    source: '',
    statusCode: '',
    resolved: 'open',
    dateFrom: '',
    dateTo: '',
  };
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  readonly columns: DataTableColumn<ErrorLogRow>[] = [
    {
      key: 'lastSeenAt',
      header: 'ล่าสุด',
      sortable: true,
      value: (r) => this.fmtTime(r.lastSeenAt),
    },
    {
      key: 'source',
      header: 'แหล่ง',
      sortable: true,
      value: (r) => (r.source === 'client' ? 'Frontend' : 'API'),
    },
    {
      key: 'statusCode',
      header: 'สถานะ',
      sortable: true,
    },
    {
      key: 'path',
      header: 'Path',
      sortable: true,
      value: (r) => [r.method, r.path].filter(Boolean).join(' '),
    },
    {
      key: 'message',
      header: 'ข้อความ',
      value: (r) => this.clip(r.message, 80),
    },
    {
      key: 'hitCount',
      header: 'ครั้ง',
      sortable: true,
    },
    {
      key: 'resolvedAt',
      header: 'สถานะแก้',
      value: (r) => (r.resolvedAt ? 'แก้แล้ว' : 'เปิดอยู่'),
    },
    {
      key: 'id',
      header: '',
      value: () => 'ดู',
    },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.reload();
  }

  ngOnDestroy(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  }

  setSearch(val: string): void {
    this.filters.q = val;
    this.pageIndex = 0;
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reload(), 250);
  }

  onPage(index: number): void {
    this.pageIndex = index;
    this.reload();
  }

  onSort(change: DataTableSortChange): void {
    this.sortBy = change.sortBy;
    this.sortDir = change.sortDir;
    this.pageIndex = 0;
    this.reload();
  }

  onCellClick(row: ErrorLogRow, column: DataTableColumn<ErrorLogRow>): void {
    if (column.key === 'id' || column.key === 'message' || column.key === 'path') {
      this.openDetail(row);
    }
  }

  reload(): void {
    this.loading = true;
    const query = buildDataTableQuery({
      pageIndex: this.pageIndex,
      pageSize: this.pageSize,
      q: this.filters.q,
      sortBy: this.sortBy,
      sortDir: this.sortDir || 'desc',
    });
    let params = new HttpParams({ fromObject: toDataTableParams(query) });
    params = params.set('paged', 'true');
    const f = this.filters;
    if (f.source) params = params.set('source', f.source);
    if (f.statusCode.trim()) params = params.set('statusCode', f.statusCode.trim());
    if (f.resolved === 'open') params = params.set('resolved', 'false');
    if (f.resolved === 'done') params = params.set('resolved', 'true');
    if (f.dateFrom) params = params.set('dateFrom', f.dateFrom);
    if (f.dateTo) params = params.set('dateTo', f.dateTo);

    this.http.get<PageEnvelope<ErrorLogRow> | ErrorLogRow[]>('/system/error-logs', { params }).subscribe({
      next: (payload) => {
        const page = normalizePageEnvelope<ErrorLogRow>(payload);
        this.total = page.total;
        this.pageIndex = clampPageIndex(this.pageIndex, page.total, this.pageSize);
        this.rows = page.items || [];
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.rows = [];
        this.total = 0;
        swal('โหลดไม่สำเร็จ', apiErrorMessage(err, 'โหลด error log ไม่สำเร็จ'), 'error');
      },
    });
  }

  openDetail(row: ErrorLogRow): void {
    this.detailLoading = true;
    this.selected = row;
    this.http.get<ErrorLogRow>(`/system/error-logs/${row.id}`).subscribe({
      next: (detail) => {
        this.selected = detail;
        this.detailLoading = false;
      },
      error: (err) => {
        this.detailLoading = false;
        swal('โหลดรายละเอียดไม่สำเร็จ', apiErrorMessage(err), 'error');
      },
    });
  }

  closeDetail(): void {
    this.selected = null;
  }

  markResolved(resolved: boolean): void {
    if (!this.selected) return;
    this.http
      .patch<ErrorLogRow>(`/system/error-logs/${this.selected.id}`, { resolved })
      .subscribe({
        next: (row) => {
          this.selected = row;
          this.reload();
          swal('สำเร็จ', resolved ? 'มาร์กว่าแก้แล้ว' : 'เปิดเคสใหม่', 'success');
        },
        error: (err) => swal('บันทึกไม่สำเร็จ', apiErrorMessage(err), 'error'),
      });
  }

  fmtTime(value: string | null | undefined): string {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString('th-TH', { hour12: false });
  }

  clip(value: string | null | undefined, max: number): string {
    const text = (value || '').trim();
    if (text.length <= max) return text || '—';
    return `${text.slice(0, max)}…`;
  }
}
