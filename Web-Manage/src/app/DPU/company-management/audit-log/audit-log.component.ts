import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../shared/services/token.service';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="box p-4">
      <h2>ประวัติการใช้งาน</h2>
      <button type="button" (click)="exportCsv()">ส่งออก CSV</button>
      <table>
        <tr><th>เวลา</th><th>การกระทำ</th><th>เส้นทาง</th><th>สถานะ</th></tr>
        <tr *ngFor="let row of rows">
          <td>{{ row.occurredAt }}</td>
          <td>{{ row.action }}</td>
          <td>{{ row.path }}</td>
          <td>{{ row.statusCode }}</td>
        </tr>
      </table>
      <h3>แจ้งเตือน</h3>
      <label>อีเมล <input [(ngModel)]="email" /></label>
      <label>LINE token <input [(ngModel)]="lineToken" /></label>
      <button type="button" (click)="saveNotify()">บันทึก</button>
      <button type="button" (click)="testNotify()">ทดสอบ</button>
    </section>
  `,
})
export class AuditLogComponent implements OnInit {
  rows: any[] = [];
  email = '';
  lineToken = '';
  private companyId = '';

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) {
      return;
    }
    this.http.get<any[]>(`/companys/${this.companyId}/audit-logs`).subscribe((rows) => (this.rows = rows || []));
    this.http.get<any>(`/notifications/company/${this.companyId}/settings`).subscribe((s) => {
      this.email = s?.email || '';
      this.lineToken = s?.lineToken || '';
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
    const header = 'occurredAt,action,path,statusCode';
    const body = this.rows
      .map((r) => [r.occurredAt, r.action, r.path, r.statusCode].map((v) => `"${v ?? ''}"`).join(','))
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
