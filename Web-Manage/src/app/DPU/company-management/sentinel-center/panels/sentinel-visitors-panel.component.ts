import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import {
  defaultVisitorForm,
  escapeHtml,
  filterVisitorItems,
  firstFileFromInput,
} from '../sentinel.helpers';
import { SentinelIdentity } from '../sentinel.models';
import { VisitorSection } from '../sentinel-routing';

@Component({
    selector: 'app-sentinel-visitors-panel',
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './sentinel-visitors-panel.component.html'
})
export class SentinelVisitorsPanelComponent implements OnInit {
  @Input() section: VisitorSection = 'passes';
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  identities: SentinelIdentity[] = [];
  selectedIdentityPhoto: File | null = null;
  visitorForm = defaultVisitorForm();
  inviteResult: { inviteToken: string; invitePath: string; expiresAt: string } | null = null;
  ocrBusy = false;
  ocrResult: Record<string, unknown> | null = null;

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadIdentities();
  }

  get visitorItems(): SentinelIdentity[] {
    return filterVisitorItems(this.identities);
  }

  get enrolledVisitorCount(): number {
    return this.visitorItems.filter((v) => !!v.hasFaceEnrolled).length;
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

  copyPreRegLink(): void {
    if (this.inviteResult?.inviteToken) {
      const url = `${window.location.origin}/#/visitor-invite/${this.inviteResult.inviteToken}`;
      navigator.clipboard?.writeText(url).then(
        () => this.toast.emit('คัดลอกลิงก์เชิญลงทะเบียนล่วงหน้าแล้ว'),
        () => this.toast.emit(url),
      );
      return;
    }
    this.api
      .createVisitorInvite(this.companyId, {
        visitorName: this.visitorForm.fullName.trim() || 'Guest Visitor',
        purpose: this.visitorForm.visitPurpose?.trim() || undefined,
      })
      .subscribe({
        next: (res) => {
          this.inviteResult = res;
          const url = `${window.location.origin}/#/visitor-invite/${res.inviteToken}`;
          navigator.clipboard?.writeText(url).then(
            () => this.toast.emit('สร้างและคัดลอกลิงก์เชิญลงทะเบียนผู้มาติดต่อแล้ว'),
            () => this.toast.emit(url),
          );
        },
        error: () => {
          const fallback = `${window.location.origin}/#/company/scan/visitor`;
          this.toast.emit(fallback);
        },
      });
  }

  printVisitorBadge(v: SentinelIdentity): void {
    const popup = window.open('', '_blank', 'width=460,height=600');
    if (!popup) {
      this.toast.emit('กรุณาอนุญาตป๊อปอัป (Pop-up) เพื่อพิมพ์บัตรผู้มาติดต่อ');
      return;
    }
    const name = escapeHtml(v.fullName);
    const org = escapeHtml(v.organization || '-');
    const purpose = escapeHtml((v as unknown as { visitPurpose?: string }).visitPurpose || v.alertNote || '-');
    const expiry = escapeHtml(v.expiresAt ? new Date(v.expiresAt).toLocaleString() : 'ไม่ระบุ');
    const code = escapeHtml(`SV-VISITOR:${v.identityId}`);
    popup.document.write(`<!doctype html>
<html><head><meta charset="utf-8"><title>Visitor Pass - ${name}</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; color: #0f172a; }
  .badge { border: 2px solid #0f172a; border-radius: 12px; padding: 20px; max-width: 340px; }
  .brand { font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: #0284c7; font-weight: 700; }
  h1 { font-size: 20px; margin: 8px 0 4px; }
  .meta { font-size: 13px; color: #334155; margin: 6px 0; }
  .code { margin-top: 14px; padding: 10px; background: #f1f5f9; border-radius: 8px; font-family: monospace; font-size: 11px; word-break: break-all; }
  @media print { .no-print { display: none; } }
</style></head>
<body>
  <div class="badge">
    <div class="brand">SentinelVision Visitor Pass</div>
    <h1>${name}</h1>
    <div class="meta"><strong>หน่วยงาน:</strong> ${org}</div>
    <div class="meta"><strong>วัตถุประสงค์:</strong> ${purpose}</div>
    <div class="meta"><strong>หมดอายุ:</strong> ${expiry}</div>
    <div class="code">${code}</div>
  </div>
  <p class="no-print" style="margin-top:16px"><button onclick="window.print()">พิมพ์บัตร</button></p>
</body></html>`);
    popup.document.close();
    popup.focus();
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

  issueInviteLink(): void {
    const name = String(this.visitorForm.fullName || '').trim();
    if (!name) {
      this.toast.emit('กรุณาระบุชื่อผู้มาติดต่อก่อนสร้างลิงก์เชิญ');
      return;
    }
    this.api
      .createVisitorInvite(this.companyId, {
        visitorName: name,
        hostName: String(this.visitorForm.organization || '') || undefined,
        purpose: String(this.visitorForm.visitPurpose || '') || undefined,
      })
      .subscribe({
        next: (res) => {
          this.inviteResult = res;
          this.toast.emit('สร้างลิงก์ลงทะเบียนล่วงหน้า (HMAC) สำเร็จ');
        },
        error: () => this.toast.emit('ไม่สามารถสร้างลิงก์เชิญได้'),
      });
  }

  onOcrFileSelected(event: Event): void {
    const file = firstFileFromInput(event);
    if (!file || !this.companyId || this.ocrBusy) return;
    this.ocrBusy = true;
    const fd = new FormData();
    fd.append('file', file);
    fd.append('documentType', 'AUTO');
    this.api.ocrVisitorDocument(this.companyId, fd).subscribe({
      next: (res) => {
        this.ocrBusy = false;
        this.ocrResult = res.document || null;
        const fullName = String(res.document?.['fullName'] || '').trim();
        if (fullName) {
          this.visitorForm.fullName = fullName;
        }
        this.toast.emit('สแกนเอกสารบัตรประชาชน/พาสปอร์ตสำเร็จ');
      },
      error: () => {
        this.ocrBusy = false;
        this.toast.emit('ไม่สามารถอ่านข้อมูลจากเอกสารได้');
      },
    });
  }
}
