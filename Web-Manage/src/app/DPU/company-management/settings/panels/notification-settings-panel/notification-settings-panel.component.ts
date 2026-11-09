import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../../shared/services/token.service';

type NotifyStatus = 'idle' | 'saved' | 'tested' | 'error';

/** Company notification channels (email + LINE token) — shared by audit-log and the settings hub. */
@Component({
  selector: 'app-notification-settings-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './notification-settings-panel.component.html',
})
export class NotificationSettingsPanelComponent implements OnInit {
  /** Override the selected company (defaults to TokenService selection). */
  @Input() companyId = '';

  email = '';
  lineToken = '';
  loading = false;
  busy = false;
  status: NotifyStatus = 'idle';

  constructor(private http: HttpClient, private token: TokenService) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.loading = true;
    this.http.get<any>(`/notifications/company/${this.companyId}/settings`).subscribe({
      next: (s) => {
        this.email = s?.email || '';
        this.lineToken = s?.lineToken || '';
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  saveNotify(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    this.http
      .put(`/notifications/company/${this.companyId}/settings`, {
        email: this.email,
        lineToken: this.lineToken,
        events: ['import.finished', 'approval.pending'],
      })
      .subscribe({
        next: () => this.done('saved'),
        error: () => this.done('error'),
      });
  }

  testNotify(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    this.http.post(`/notifications/company/${this.companyId}/test`, {}).subscribe({
      next: () => this.done('tested'),
      error: () => this.done('error'),
    });
  }

  private done(status: NotifyStatus): void {
    this.busy = false;
    this.status = status;
  }
}
