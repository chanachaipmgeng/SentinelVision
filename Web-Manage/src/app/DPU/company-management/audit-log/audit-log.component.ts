import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TokenService } from '../../../shared/services/token.service';

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
  ],
  templateUrl: './audit-log.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css'],
  encapsulation: ViewEncapsulation.None,
})
export class AuditLogComponent implements OnInit {
  rows: any[] = [];
  loading = false;
  companyId = '';
  filters = {
    q: '',
    actor: '',
    action: '',
    resource: '',
    dateFrom: '',
    dateTo: '',
  };

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.reload();
  }

  setSearch(val: string): void {
    this.filters.q = val;
    this.reload();
  }

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    let params = new HttpParams().set('limit', '200');
    const f = this.filters;
    if (f.q.trim()) params = params.set('q', f.q.trim());
    if (f.actor.trim()) params = params.set('actor', f.actor.trim());
    if (f.action.trim()) params = params.set('action', f.action.trim());
    if (f.resource.trim()) params = params.set('resource', f.resource.trim());
    if (f.dateFrom) params = params.set('dateFrom', f.dateFrom);
    if (f.dateTo) params = params.set('dateTo', f.dateTo);
    this.http.get<any[]>(`/companys/${this.companyId}/audit-logs`, { params }).subscribe({
      next: (rows) => {
        this.rows = rows || [];
        this.loading = false;
      },
      error: () => {
        this.rows = [];
        this.loading = false;
      },
    });
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
