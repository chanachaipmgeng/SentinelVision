import { Component, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../services/token.service';
import { ShellUiService } from '../../services/shell-ui.service';

export interface InboxNotification {
  notificationId: string;
  event?: string;
  title?: string;
  body?: string;
  readAt?: string | null;
  createdAt?: string | null;
}

const APPROVAL_EVENT = /^(attendance\.|approval|leave\.|ot\.)/i;

@Component({
  selector: 'app-notification-drawer',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  templateUrl: './notification-drawer.component.html',
  styleUrl: './notification-drawer.component.css',
})
export class NotificationDrawerComponent {
  items: InboxNotification[] = [];
  loading = false;
  error = false;
  pendingOutbox = 0;

  constructor(
    readonly ui: ShellUiService,
    private http: HttpClient,
    private tokenService: TokenService,
    private router: Router,
  ) {
    effect(() => {
      if (this.ui.notificationsOpen()) {
        this.load();
      }
    });
  }

  get companyId(): string | null {
    const id = this.tokenService.getSelectCompany()?.companyId;
    return id ? String(id) : null;
  }

  get unreadCount(): number {
    return this.items.filter((n) => !n.readAt).length;
  }

  load(): void {
    const cid = this.companyId;
    this.error = false;
    this.http
      .get<{ pending: number }>('/notifications/pending-count', {
        params: cid ? { companyId: cid } : {},
      })
      .subscribe({
        next: (res) => (this.pendingOutbox = res?.pending || 0),
        error: () => (this.pendingOutbox = 0),
      });
    if (!cid) {
      this.items = [];
      return;
    }
    this.loading = true;
    this.http
      .get<InboxNotification[]>(`/notifications/company/${cid}/inbox`, { params: { limit: 20 } })
      .subscribe({
        next: (rows) => {
          this.items = rows || [];
          this.loading = false;
        },
        error: () => {
          this.items = [];
          this.loading = false;
          this.error = true;
        },
      });
  }

  linkFor(n: InboxNotification): string {
    return APPROVAL_EVENT.test(n.event || '') ? '/company/approval-inbox' : '/company/notification-center';
  }

  open(n: InboxNotification): void {
    if (!n.readAt) {
      this.markRead(n);
    }
    this.close();
    this.router.navigateByUrl(this.linkFor(n));
  }

  markRead(n: InboxNotification, ev?: Event): void {
    ev?.stopPropagation();
    const cid = this.companyId;
    if (!cid || n.readAt) return;
    this.http.post(`/notifications/company/${cid}/inbox/${n.notificationId}/read`, {}).subscribe({
      next: () => {
        n.readAt = new Date().toISOString();
        this.ui.notificationsChanged$.next();
      },
    });
  }

  markAllRead(): void {
    const cid = this.companyId;
    if (!cid) return;
    this.http.post(`/notifications/company/${cid}/inbox/read-all`, {}).subscribe({
      next: () => {
        const now = new Date().toISOString();
        this.items.forEach((n) => (n.readAt = n.readAt || now));
        this.ui.notificationsChanged$.next();
      },
    });
  }

  close(): void {
    this.ui.notificationsOpen.set(false);
  }
}
