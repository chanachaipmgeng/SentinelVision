import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TokenService } from '../../../shared/services/token.service';
import { TranslateModule } from '@ngx-translate/core';

type Tab = 'inbox' | 'dead-letter' | 'prefs' | 'templates';

@Component({
  selector: 'app-notification-center',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    TranslateModule,
    PageToolbarComponent,
    EmptyStateComponent,
  ],
  templateUrl: './notification-center.component.html',
  styleUrls: ['./notification-center.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class NotificationCenterComponent implements OnInit {
  companyId = '';
  activeTab: Tab = 'inbox';
  loading = false;
  inbox: any[] = [];
  deadLetter: any[] = [];
  prefs: any = {
    channelEmail: true,
    channelLine: true,
    channelInApp: true,
    lineUserId: '',
    mutedEvents: [],
    locale: 'th',
  };
  templates: any = { builtins: [], custom: [], i18nKeys: {} };
  mutedRaw = '';

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.reload();
  }

  setTab(tab: Tab): void {
    this.activeTab = tab;
    this.reload();
  }

  reload(): void {
    if (!this.companyId) return;
    this.loading = true;
    if (this.activeTab === 'inbox') {
      this.http.get<any[]>(`/notifications/company/${this.companyId}/inbox`).subscribe({
        next: (rows) => {
          this.inbox = rows || [];
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else if (this.activeTab === 'dead-letter') {
      this.http.get<any[]>(`/notifications/company/${this.companyId}/dead-letter`).subscribe({
        next: (rows) => {
          this.deadLetter = rows || [];
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else if (this.activeTab === 'prefs') {
      this.http.get<any>(`/notifications/company/${this.companyId}/preferences/me`).subscribe({
        next: (p) => {
          this.prefs = { ...this.prefs, ...p };
          this.mutedRaw = (this.prefs.mutedEvents || []).join(', ');
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else {
      this.http.get<any>(`/notifications/company/${this.companyId}/templates`).subscribe({
        next: (t) => {
          this.templates = t || this.templates;
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    }
  }

  markRead(n: any): void {
    this.http
      .post(`/notifications/company/${this.companyId}/inbox/${n.notificationId}/read`, {})
      .subscribe(() => this.reload());
  }

  markAllRead(): void {
    this.http
      .post(`/notifications/company/${this.companyId}/inbox/read-all`, {})
      .subscribe(() => this.reload());
  }

  retryDead(row: any): void {
    this.http
      .post(`/notifications/company/${this.companyId}/dead-letter/${row.id}/retry`, {})
      .subscribe(() => this.reload());
  }

  savePrefs(): void {
    const muted = (this.mutedRaw || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    this.http
      .put(`/notifications/company/${this.companyId}/preferences/me`, {
        ...this.prefs,
        mutedEvents: muted,
      })
      .subscribe((p) => {
        this.prefs = { ...this.prefs, ...p };
      });
  }

  i18nEntries(): Array<{ event: string; key: string }> {
    const keys = this.templates?.i18nKeys || {};
    return Object.keys(keys).map((event) => ({ event, key: keys[event] }));
  }
}
