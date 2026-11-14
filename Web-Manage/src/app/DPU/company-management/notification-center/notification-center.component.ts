import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import { TranslateModule } from '@ngx-translate/core';
import {
  DeadLetterRow,
  InboxNotification,
  NotificationPrefs,
  NotificationTemplatesView,
} from './notification.models';

type Tab = 'inbox' | 'dead-letter' | 'history' | 'prefs' | 'templates';

@Component({
    selector: 'app-notification-center',
    imports: [
        CommonModule,
        FormsModule,
        RouterModule,
        TranslateModule,
        SharedModule,
        PageToolbarComponent,
        EmptyStateComponent,
    ],
    templateUrl: './notification-center.component.html',
    styleUrls: ['./notification-center.component.css'],
    encapsulation: ViewEncapsulation.None
})
export class NotificationCenterComponent implements OnInit {
  companyId = '';
  activeTab: Tab = 'inbox';
  loading = false;
  inbox: InboxNotification[] = [];
  inboxFiltered: InboxNotification[] = [];
  searchTerm = '';
  deadLetter: DeadLetterRow[] = [];
  outboxHistory: (DeadLetterRow & { status?: string; sentAt?: string | null })[] = [];
  prefs: NotificationPrefs = {
    channelEmail: true,
    channelLine: true,
    channelInApp: true,
    lineUserId: '',
    mutedEvents: [],
    locale: 'th',
  };
  templates: NotificationTemplatesView = { builtins: [], custom: [], i18nKeys: {} };
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
      this.http.get<InboxNotification[]>(`/notifications/company/${this.companyId}/inbox`).subscribe({
        next: (rows) => {
          this.inbox = rows || [];
          this.applyInboxFilter();
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else if (this.activeTab === 'dead-letter') {
      this.http.get<DeadLetterRow[]>(`/notifications/company/${this.companyId}/dead-letter`).subscribe({
        next: (rows) => {
          this.deadLetter = rows || [];
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else if (this.activeTab === 'history') {
      this.http
        .get<(DeadLetterRow & { status?: string; sentAt?: string | null })[]>(
          `/notifications/company/${this.companyId}/outbox?limit=100`,
        )
        .subscribe({
          next: (rows) => {
            this.outboxHistory = rows || [];
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
    } else if (this.activeTab === 'prefs') {
      this.http.get<NotificationPrefs>(`/notifications/company/${this.companyId}/preferences/me`).subscribe({
        next: (p) => {
          this.prefs = { ...this.prefs, ...(p || {}) };
          this.mutedRaw = (this.prefs.mutedEvents || []).join('\n');
          this.loading = false;
        },
        error: () => (this.loading = false),
      });
    } else if (this.activeTab === 'templates') {
      this.http
        .get<NotificationTemplatesView>(`/notifications/company/${this.companyId}/templates`)
        .subscribe({
          next: (t) => {
            this.templates = t || this.templates;
            this.loading = false;
          },
          error: () => (this.loading = false),
        });
    }
  }

  applyInboxFilter(): void {
    const q = (this.searchTerm || '').trim().toLowerCase();
    if (!q) {
      this.inboxFiltered = [...this.inbox];
      return;
    }
    this.inboxFiltered = this.inbox.filter(
      (n) =>
        (n.title || '').toLowerCase().includes(q) ||
        (n.body || '').toLowerCase().includes(q) ||
        (n.event || '').toLowerCase().includes(q),
    );
  }

  markRead(n: InboxNotification): void {
    const id = n.id;
    if (!id) return;
    this.http
      .post(`/notifications/company/${this.companyId}/inbox/${id}/read`, {})
      .subscribe(() => this.reload());
  }

  markAllRead(): void {
    this.http
      .post(`/notifications/company/${this.companyId}/inbox/read-all`, {})
      .subscribe(() => this.reload());
  }

  retryDead(row: DeadLetterRow): void {
    const id = row.id;
    if (!id) return;
    this.http
      .post(`/notifications/company/${this.companyId}/dead-letter/${id}/retry`, {})
      .subscribe(() => this.reload());
  }

  i18nEntries(): { event: string; key: string }[] {
    const keys = this.templates?.i18nKeys || {};
    return Object.keys(keys).map((event) => ({ event, key: keys[event] || '' }));
  }

  savePrefs(): void {
    const muted = (this.mutedRaw || '')
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);
    this.prefs.mutedEvents = muted;
    this.http
      .put(`/notifications/company/${this.companyId}/preferences/me`, this.prefs)
      .subscribe({
        next: () => this.reload(),
      });
  }
}
