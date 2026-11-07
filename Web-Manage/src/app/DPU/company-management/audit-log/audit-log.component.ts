import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  DataTableColumn,
  DataTableComponent,
  DataTableSortChange,
} from '../../../shared/components/data-table/data-table.component';
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
  path: string | null;
  statusCode: string | null;
  ip: string | null;
}

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule, DataTableComponent],
  template: `
    <section class="box p-4 audit-page">
      <h2>ประวัติการใช้งาน</h2>
      <div class="audit-actions">
        <button type="button" (click)="exportCsv()" [disabled]="!rows.length">ส่งออก CSV (หน้านี้)</button>
      </div>

      <app-data-table
        [columns]="columns"
        [rows]="rows"
        [total]="total"
        [loading]="loading"
        [pageIndex]="pageIndex"
        [pageSize]="pageSize"
        [sortBy]="sortBy"
        [sortDir]="sortDir"
        [search]="search"
        searchPlaceholder="ค้นหา action / path / IP…"
        trackByKey="id"
        emptyTitle="ยังไม่มีบันทึก audit"
        emptyHint="เมื่อมีการแก้ไขข้อมูล ระบบจะบันทึกประวัติที่นี่"
        (pageIndexChange)="onPage($event)"
        (sortChange)="onSort($event)"
        (searchChange)="onSearch($event)"
        (searchSubmit)="reload()"
      ></app-data-table>

      <h3>แจ้งเตือน</h3>
      <label>อีเมล <input [(ngModel)]="email" /></label>
      <label>LINE token <input [(ngModel)]="lineToken" /></label>
      <button type="button" (click)="saveNotify()">บันทึก</button>
      <button type="button" (click)="testNotify()">ทดสอบ</button>
    </section>
  `,
  styles: [
    `
      .audit-page h2 {
        margin: 0 0 0.75rem;
      }
      .audit-actions {
        margin-bottom: 0.75rem;
      }
      .audit-page h3 {
        margin-top: 1.5rem;
      }
      .audit-page label {
        display: block;
        margin: 0.35rem 0;
      }
    `,
  ],
})
export class AuditLogComponent implements OnInit, OnDestroy {
  rows: AuditRow[] = [];
  total = 0;
  loading = false;
  pageIndex = 0;
  pageSize = 25;
  search = '';
  sortBy: string | null = 'occurredAt';
  sortDir: SortDir | null = 'desc';
  email = '';
  lineToken = '';
  private companyId = '';
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  readonly columns: DataTableColumn<AuditRow>[] = [
    { key: 'occurredAt', header: 'เวลา', sortable: true },
    { key: 'action', header: 'การกระทำ', sortable: true },
    { key: 'path', header: 'เส้นทาง', sortable: true },
    { key: 'statusCode', header: 'สถานะ', sortable: true },
    { key: 'ip', header: 'IP' },
    { key: 'actorRole', header: 'บทบาท' },
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

  onSearch(value: string): void {
    this.search = value;
    this.pageIndex = 0;
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reload(), 250);
  }

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    const query = buildDataTableQuery({
      pageIndex: this.pageIndex,
      pageSize: this.pageSize,
      q: this.search,
      sortBy: this.sortBy,
      sortDir: this.sortDir || 'desc',
    });
    const params = new HttpParams({ fromObject: toDataTableParams(query) });
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
    const header = 'occurredAt,action,path,statusCode,ip,actorRole';
    const body = this.rows
      .map((r) =>
        [r.occurredAt, r.action, r.path, r.statusCode, r.ip, r.actorRole]
          .map((v) => `"${v ?? ''}"`)
          .join(','),
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
