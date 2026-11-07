import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  DataTableColumn,
  DataTableComponent,
  DataTableSortChange,
} from '../../../shared/components/data-table/data-table.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import {
  SortDir,
  buildDataTableQuery,
  clampPageIndex,
  normalizePageEnvelope,
  toDataTableParams,
} from '../../../shared/utils/data-table-query';

interface AuditRow {
  id: string;
  occurredAt: string | null;
  actorMemberId: string | null;
  actorRole: string | null;
  action: string;
  entityType?: string | null;
  entityId?: string | null;
  path: string | null;
  statusCode: string | null;
  ip: string | null;
}

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SharedModule,
    PageToolbarComponent,
    PillSearchComponent,
    EmptyStateComponent,
    DataTableComponent,
  ],
  templateUrl: './audit-log.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css'],
  encapsulation: ViewEncapsulation.None,
})
export class AuditLogComponent implements OnInit, OnDestroy {
  rows: AuditRow[] = [];
  total = 0;
  loading = false;
  pageIndex = 0;
  pageSize = 25;
  sortBy: string | null = 'occurredAt';
  sortDir: SortDir | null = 'desc';
  email = '';
  lineToken = '';
  companyId = '';
  filters = {
    q: '',
    actor: '',
    action: '',
    resource: '',
    dateFrom: '',
    dateTo: '',
  };
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  readonly columns: DataTableColumn<AuditRow>[] = [
    { key: 'occurredAt', header: 'เวลา', sortable: true },
    { key: 'actorRole', header: 'Actor' },
    { key: 'action', header: 'Action', sortable: true },
    { key: 'entityType', header: 'Resource' },
    { key: 'path', header: 'Path', sortable: true },
    { key: 'statusCode', header: 'สถานะ', sortable: true },
    { key: 'ip', header: 'IP' },
  ];

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.reload();
    this.http.get<any>(`/notifications/company/${this.companyId}/settings`).subscribe((s) => {
      this.email = s?.email || '';
      this.lineToken = s?.lineToken || '';
    });
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

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    const query = buildDataTableQuery({
      pageIndex: this.pageIndex,
      pageSize: this.pageSize,
      q: this.filters.q,
      sortBy: this.sortBy,
      sortDir: this.sortDir || 'desc',
    });
    let params = new HttpParams({ fromObject: toDataTableParams(query) });
    const f = this.filters;
    if (f.actor.trim()) params = params.set('actor', f.actor.trim());
    if (f.action.trim()) params = params.set('action', f.action.trim());
    if (f.resource.trim()) params = params.set('resource', f.resource.trim());
    if (f.dateFrom) params = params.set('dateFrom', f.dateFrom);
    if (f.dateTo) params = params.set('dateTo', f.dateTo);

    this.http
      .get<any>(`/companys/${this.companyId}/audit-logs`, { params })
      .subscribe({
        next: (payload) => {
          const page = normalizePageEnvelope<AuditRow>(payload);
          this.total = page.total;
          this.pageIndex = clampPageIndex(this.pageIndex, page.total, this.pageSize);
          this.rows = page.items || [];
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          this.rows = [];
          this.total = 0;
        },
      });
  }

  saveNotify(): void {
    this.http
      .put(`/notifications/company/${this.companyId}/settings`, {
        email: this.email,
        lineToken: this.lineToken,
        events: ['import.finished', 'approval.pending'],
      })
      .subscribe();
  }

  testNotify(): void {
    this.http.post(`/notifications/company/${this.companyId}/test`, {}).subscribe();
  }

  exportCsv(): void {
    const header = 'occurredAt,actor,action,resource,path,statusCode,ip';
    const body = this.rows
      .map((r) =>
        [
          r.occurredAt,
          r.actorMemberId || r.actorRole,
          r.action,
          [r.entityType, r.entityId].filter(Boolean).join(':'),
          r.path,
          r.statusCode,
          r.ip,
        ]
          .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
          .join(',')
      )
      .join('\n');
    const blob = new Blob([header + '\n' + body], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit-log.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
}
