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
  NotificationTemplateRow,
  NotificationTemplatesView,
} from './notification.models';

type Tab = 'inbox' | 'dead-letter' | 'history' | 'prefs' | 'templates';

interface EventCatalogOption {
  key: string;
  label: string;
  category: 'attendance' | 'security' | 'system';
}

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
  prefsSavedMsg = '';

  // Event category options
  readonly eventOptions: EventCatalogOption[] = [
    { key: 'attendance.checked_in', label: 'ลงเวลาเข้างาน (Check-in)', category: 'attendance' },
    { key: 'attendance.checked_out', label: 'ลงเวลาออกงาน (Check-out)', category: 'attendance' },
    { key: 'attendance.late_arrival', label: 'แจ้งเตือนเข้างานสาย (Late Arrival)', category: 'attendance' },
    { key: 'attendance.missing', label: 'ยังไม่ลงเวลาเข้างาน (Missing Check-in)', category: 'attendance' },
    { key: 'sentinel.blacklist_hit', label: '🚨 พบบุคคลต้องห้าม (Blacklist Alert)', category: 'security' },
    { key: 'sentinel.vip_detected', label: '🌟 ต้อนรับแขกผู้บริหาร (VIP Arrival)', category: 'security' },
    { key: 'sentinel.poi_detected', label: '⚠️ พบบุคคลเฝ้าระวัง (POI Alert)', category: 'security' },
    { key: 'sentinel.door_alarm', label: '🚪 สัญญาณเตือนประตู (Access Alarm)', category: 'security' },
    { key: 'sentinel.emergency_muster', label: '🦺 รายงานจุดรวมพล (Emergency Muster)', category: 'security' },
    { key: 'import.finished', label: 'นำเข้าข้อมูลพนักงานเสร็จสิ้น (Import Finished)', category: 'system' },
    { key: 'system.test', label: 'ทดสอบระบบแจ้งเตือน (System Test)', category: 'system' },
  ];

  // Event variable map
  readonly eventVariableMap: Record<string, string[]> = {
    'attendance.checked_in': ['employeeName', 'time', 'location'],
    'attendance.checked_out': ['employeeName', 'time'],
    'attendance.late_arrival': ['employeeName', 'shiftName', 'lateMinutes', 'time'],
    'attendance.missing': ['missingCount', 'date'],
    'sentinel.blacklist_hit': ['personName', 'zoneName', 'cameraName', 'time', 'similarity'],
    'sentinel.vip_detected': ['personName', 'zoneName', 'time'],
    'sentinel.poi_detected': ['personName', 'zoneName', 'time'],
    'sentinel.door_alarm': ['doorName', 'alarmType', 'time'],
    'sentinel.emergency_muster': ['zoneName', 'evacuatedCount', 'missingCount', 'time'],
    'import.finished': ['jobId', 'ok', 'failed'],
    'system.test': [],
  };

  customDraft = {
    eventKey: 'attendance.checked_in',
    locale: 'th',
    channel: 'line',
    subject: '',
    bodyTemplate: '',
  };

  livePreviewText = '';
  previewLoading = false;
  templateCategoryFilter: 'all' | 'attendance' | 'security' | 'system' = 'all';

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

  get currentAvailableVariables(): string[] {
    return this.eventVariableMap[this.customDraft.eventKey] || ['employeeName', 'time', 'location'];
  }

  get filteredEventOptions(): EventCatalogOption[] {
    if (this.templateCategoryFilter === 'all') return this.eventOptions;
    return this.eventOptions.filter((opt) => opt.category === this.templateCategoryFilter);
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
            if (!this.customDraft.bodyTemplate) {
              this.loadDefaultTemplateForCurrentEvent();
            } else {
              this.updateLivePreview();
            }
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
    this.prefsSavedMsg = '';
    this.http
      .put(`/notifications/company/${this.companyId}/preferences/me`, this.prefs)
      .subscribe({
        next: () => {
          this.prefsSavedMsg = 'บันทึกค่ากำหนดการแจ้งเตือนแล้ว';
          this.reload();
        },
      });
  }

  onEventKeyChange(): void {
    this.loadDefaultTemplateForCurrentEvent();
  }

  loadDefaultTemplateForCurrentEvent(): void {
    // Check if custom template exists first
    const custom = (this.templates?.custom || []).find(
      (c) =>
        c.eventKey === this.customDraft.eventKey &&
        c.locale === this.customDraft.locale &&
        c.channel === this.customDraft.channel,
    );
    if (custom) {
      this.customDraft.subject = custom.subject || '';
      this.customDraft.bodyTemplate = custom.bodyTemplate || '';
      this.updateLivePreview();
      return;
    }

    // Fall back to built-in template
    const builtin = (this.templates?.builtins || []).find(
      (b) =>
        b.eventKey === this.customDraft.eventKey &&
        b.locale === this.customDraft.locale &&
        b.channel === this.customDraft.channel,
    );
    if (builtin) {
      this.customDraft.subject = builtin.subject || '';
      this.customDraft.bodyTemplate = builtin.bodyTemplate || '';
    } else {
      this.customDraft.subject = '';
      this.customDraft.bodyTemplate = '';
    }
    this.updateLivePreview();
  }

  insertVariable(varName: string): void {
    const token = `{${varName}}`;
    this.customDraft.bodyTemplate = (this.customDraft.bodyTemplate || '') + ' ' + token;
    this.updateLivePreview();
  }

  updateLivePreview(): void {
    if (!this.companyId || !this.customDraft.eventKey || !this.customDraft.bodyTemplate.trim()) {
      this.livePreviewText = this.customDraft.bodyTemplate || '(ยังไม่มีข้อความ)';
      return;
    }
    this.previewLoading = true;
    this.http
      .post<{ rendered: string }>(`/notifications/company/${this.companyId}/templates/preview`, {
        eventKey: this.customDraft.eventKey,
        bodyTemplate: this.customDraft.bodyTemplate,
      })
      .subscribe({
        next: (res) => {
          this.livePreviewText = res.rendered || '';
          this.previewLoading = false;
        },
        error: () => {
          this.livePreviewText = this.customDraft.bodyTemplate;
          this.previewLoading = false;
        },
      });
  }

  editCustomTemplate(t: NotificationTemplateRow): void {
    this.customDraft = {
      eventKey: t.eventKey || 'attendance.checked_in',
      locale: t.locale || 'th',
      channel: t.channel || 'line',
      subject: t.subject || '',
      bodyTemplate: t.bodyTemplate || '',
    };
    this.updateLivePreview();
  }

  deleteCustomTemplate(t: NotificationTemplateRow): void {
    if (!t.templateId || !confirm(`ต้องการลบ Custom Template '${t.eventKey}' และรีเซ็ตกลับเป็นค่าเริ่มต้นหรือไม่?`)) {
      return;
    }
    this.http
      .delete(`/notifications/company/${this.companyId}/templates/${t.templateId}`)
      .subscribe({
        next: () => {
          this.reload();
          this.loadDefaultTemplateForCurrentEvent();
        },
      });
  }

  saveCustomTemplate(): void {
    if (!this.companyId || !this.customDraft.eventKey.trim() || !this.customDraft.bodyTemplate.trim()) {
      return;
    }
    this.http
      .put(`/notifications/company/${this.companyId}/templates`, {
        eventKey: this.customDraft.eventKey.trim(),
        locale: this.customDraft.locale,
        channel: this.customDraft.channel,
        subject: this.customDraft.subject.trim(),
        bodyTemplate: this.customDraft.bodyTemplate.trim(),
      })
      .subscribe({
        next: () => {
          this.reload();
        },
      });
  }
}
