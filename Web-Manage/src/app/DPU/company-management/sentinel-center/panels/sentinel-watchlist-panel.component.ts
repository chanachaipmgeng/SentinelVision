import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import {
  defaultWatchlistForm,
  filterWatchlistItems,
  firstFileFromInput,
} from '../sentinel.helpers';
import { SentinelIdentity, SentinelSiemSettings } from '../sentinel.models';
import { WatchlistSection } from '../sentinel-routing';
import { SentinelCommandPanelComponent } from './sentinel-command-panel.component';

@Component({
    selector: 'app-sentinel-watchlist-panel',
    imports: [CommonModule, FormsModule, RouterModule, SentinelCommandPanelComponent],
    templateUrl: './sentinel-watchlist-panel.component.html'
})
export class SentinelWatchlistPanelComponent implements OnInit, OnChanges {
  @Input() section: WatchlistSection = 'identities';
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  identities: SentinelIdentity[] = [];
  selectedIdentityPhoto: File | null = null;
  watchlistForm = defaultWatchlistForm();

  siemForm = {
    siemWebhookUrl: '',
    siemWebhookSecret: '',
    hasSiemWebhookSecret: false,
  };
  siemSaving = false;
  slaMinutesHigh = 15;
  slaSaving = false;

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadIdentities();
    if (this.section === 'settings') {
      this.loadAlertSettings();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['section'] && this.section === 'settings' && this.companyId) {
      this.loadAlertSettings();
    }
  }

  loadAlertSettings(): void {
    this.api.getSiemSettings(this.companyId).subscribe({
      next: (s: SentinelSiemSettings) => {
        this.siemForm = {
          siemWebhookUrl: s.siemWebhookUrl || '',
          siemWebhookSecret: '',
          hasSiemWebhookSecret: !!s.hasSiemWebhookSecret,
        };
      },
    });
    this.api.getIncidentSlaSettings(this.companyId).subscribe({
      next: (res) => {
        if (res?.incidentSlaMinutesHigh) {
          this.slaMinutesHigh = res.incidentSlaMinutesHigh;
        }
      },
    });
  }

  saveSiemSettings(): void {
    this.siemSaving = true;
    const body: Record<string, string> = {
      siemWebhookUrl: this.siemForm.siemWebhookUrl || '',
    };
    if ((this.siemForm.siemWebhookSecret || '').trim()) {
      body['siemWebhookSecret'] = this.siemForm.siemWebhookSecret.trim();
    }
    this.api.putSiemSettings(this.companyId, body).subscribe({
      next: (s) => {
        this.siemSaving = false;
        this.siemForm.siemWebhookSecret = '';
        this.siemForm.hasSiemWebhookSecret = !!s?.hasSiemWebhookSecret;
        this.siemForm.siemWebhookUrl = s?.siemWebhookUrl || this.siemForm.siemWebhookUrl;
        this.toast.emit('บันทึก SIEM Webhook แล้ว');
      },
      error: () => {
        this.siemSaving = false;
        this.toast.emit('บันทึก SIEM ไม่สำเร็จ');
      },
    });
  }

  testSiemSettings(): void {
    this.api.testSiemSettings(this.companyId).subscribe({
      next: (res) => {
        const body = res as { queued?: boolean; reason?: string };
        this.toast.emit(
          body.queued ? 'ส่ง SIEM test ping เข้า outbox แล้ว' : body.reason || 'ยังไม่ได้ตั้งค่า webhook'
        );
      },
      error: () => this.toast.emit('ทดสอบ SIEM ไม่สำเร็จ'),
    });
  }

  saveSlaSettings(): void {
    this.slaSaving = true;
    this.api
      .putIncidentSlaSettings(this.companyId, {
        incidentSlaMinutesHigh: Math.max(1, Number(this.slaMinutesHigh) || 15),
      })
      .subscribe({
        next: (res) => {
          this.slaSaving = false;
          this.slaMinutesHigh = res.incidentSlaMinutesHigh;
          this.toast.emit('บันทึก SLA เหตุการณ์ความสำคัญสูงแล้ว');
        },
        error: () => {
          this.slaSaving = false;
          this.toast.emit('บันทึก SLA ไม่สำเร็จ');
        },
      });
  }

  get watchlistItems(): SentinelIdentity[] {
    return filterWatchlistItems(this.identities);
  }

  loadIdentities(): void {
    this.api.getIdentities(this.companyId).subscribe((rows) => (this.identities = rows || []));
  }

  onIdentityPhotoSelected(event: Event): void {
    this.selectedIdentityPhoto = firstFileFromInput(event);
  }

  createIdentityRecord(formObj: { fullName?: string; [key: string]: unknown }): void {
    if (!formObj.fullName || !String(formObj.fullName).trim()) {
      this.toast.emit('กรุณาระบุชื่อ-นามสกุล');
      return;
    }
    this.api.createIdentity(this.companyId, formObj).subscribe({
      next: (created) => {
        const photo = this.selectedIdentityPhoto;
        this.selectedIdentityPhoto = null;
        formObj.fullName = '';
        if (photo && created?.identityId) {
          this.uploadIdentityFace(created.identityId, photo);
        } else {
          this.toast.emit('บันทึกรายชื่อสำเร็จ');
          this.loadIdentities();
          this.overviewChanged.emit();
        }
      },
    });
  }

  enrollExistingIdentityFace(identityId: string, event: Event): void {
    const file = firstFileFromInput(event);
    if (!file) return;
    this.uploadIdentityFace(identityId, file);
  }

  private uploadIdentityFace(identityId: string, file: File): void {
    this.api.enrollIdentityFace(this.companyId, identityId, file).subscribe({
      next: () => {
        this.toast.emit('ลงทะเบียนใบหน้า 512-d สำเร็จ');
        this.loadIdentities();
        this.overviewChanged.emit();
      },
      error: (err) => {
        this.toast.emit(err?.error?.detail || 'ไม่พบใบหน้าในภาพที่อัปโหลด');
        this.loadIdentities();
      },
    });
  }

  deleteIdentity(identityId: string): void {
    this.api.deleteIdentity(this.companyId, identityId).subscribe({
      next: () => {
        this.toast.emit('ลบรายการเรียบร้อยแล้ว');
        this.loadIdentities();
        this.overviewChanged.emit();
      },
    });
  }
}
