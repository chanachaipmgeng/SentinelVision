import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

interface InviteMetadata {
  visitorName: string;
  hostName?: string | null;
  purpose?: string | null;
  validHours: number;
  expiresAt: string;
  consentPolicy?: { title?: string; summary?: string; version?: string } | null;
}

@Component({
  selector: 'app-public-visitor-invite',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-screen bg-[#04080f] text-slate-100 flex items-center justify-center p-4">
      <div class="w-full max-w-lg rounded-2xl border border-white/10 bg-[#070d14] shadow-2xl p-6 space-y-5">
        <div class="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-cyan-400">SentinelVision</span>
            <h1 class="text-xl font-bold text-slate-100 mt-0.5">Visitor Self-Registration</h1>
          </div>
          <span class="badge bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs px-2.5 py-1 rounded-full">
            PDPA Secured
          </span>
        </div>

        <div *ngIf="loading" class="text-center py-8 text-slate-400 text-sm">
          กำลังตรวจสอบลิงก์ลงทะเบียน...
        </div>

        <div *ngIf="!loading && errorMsg" class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
          {{ errorMsg }}
        </div>

        <div *ngIf="!loading && completed" class="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
          <div class="text-emerald-300 font-bold text-base">ลงทะเบียนล่วงหน้าสำเร็จ</div>
          <p class="text-xs text-slate-300 mb-0">
            ระบบบันทึกข้อมูลใบหน้าและบัตรผู้มาติดต่อของ <strong>{{ invite?.visitorName }}</strong> เรียบร้อยแล้ว สามารถเดินผ่านจุดคัดกรอง Kiosk ได้ทันทีเมื่อเดินทางมาถึง
          </p>
        </div>

        <ng-container *ngIf="!loading && invite && !completed">
          <div class="p-4 rounded-xl bg-slate-900/70 border border-white/10 space-y-1.5 text-sm">
            <div><span class="text-slate-400">ผู้มาติดต่อ:</span> <strong class="text-slate-100">{{ invite.visitorName }}</strong></div>
            <div *ngIf="invite.hostName"><span class="text-slate-400">ผู้รับรอง:</span> {{ invite.hostName }}</div>
            <div *ngIf="invite.purpose"><span class="text-slate-400">วัตถุประสงค์:</span> {{ invite.purpose }}</div>
            <div class="text-xs text-slate-400">อายุบัตร: {{ invite.validHours }} ชั่วโมง · ลิงก์หมดอายุ {{ invite.expiresAt | date: 'short' }}</div>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-900/50 border border-white/10 space-y-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-semibold text-slate-300">สแกนบัตรประชาชน / พาสปอร์ต (ไม่บังคับ)</span>
              <label class="ti-btn ti-btn-light text-xs px-3 py-1.5 rounded-lg cursor-pointer mb-0 border border-white/15">
                {{ ocrBusy ? 'กำลังสแกน...' : 'อัปโหลดรูปบัตร/พาสปอร์ต' }}
                <input type="file" accept="image/*" class="hidden" hidden (change)="onDocSelected($event)" />
              </label>
            </div>
            <div *ngIf="ocrDoc" class="text-xs text-cyan-300 flex flex-wrap gap-3">
              <span>{{ ocrDoc['documentType'] }}: <code>{{ ocrDoc['documentNumberMasked'] }}</code></span>
              <span>Checksum: {{ ocrDoc['checksumValid'] ? 'VALID' : 'UNVERIFIED' }}</span>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">เบอร์โทรศัพท์ติดต่อ</label>
            <input
              type="tel"
              [(ngModel)]="phoneNumber"
              placeholder="08x-xxx-xxxx"
              class="w-full rounded-lg bg-slate-950/80 border border-white/15 px-3 py-2 text-sm text-slate-100"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">รูปถ่ายใบหน้า (Selfie) สำหรับสแกนเข้าอาคาร</label>
            <input
              type="file"
              accept="image/*"
              capture="user"
              (change)="onSelfieSelected($event)"
              class="w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-cyan-500/20 file:text-cyan-300"
            />
          </div>

          <label class="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" [(ngModel)]="consentAccepted" class="mt-0.5 rounded border-white/20" />
            <span>
              ข้าพเจ้ายินยอมให้เก็บรวบรวมและประมวลผลข้อมูลชีวมิติ (Face Embedding) เพื่อการยืนยันตัวตนและควบคุมการเข้า-ออกตามนโยบาย PDPA ขององค์กร
            </span>
          </label>

          <button
            type="button"
            (click)="submit()"
            [disabled]="submitting || !consentAccepted"
            class="w-full py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm transition"
          >
            {{ submitting ? 'กำลังบันทึกข้อมูล...' : 'ยืนยันการลงทะเบียนล่วงหน้า' }}
          </button>
        </ng-container>
      </div>
    </div>
  `,
})
export class PublicVisitorInviteComponent implements OnInit {
  token = '';
  loading = true;
  submitting = false;
  ocrBusy = false;
  completed = false;
  errorMsg = '';
  invite: InviteMetadata | null = null;
  ocrDoc: Record<string, unknown> | null = null;
  phoneNumber = '';
  consentAccepted = false;
  selfieFile: File | null = null;

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    if (!this.token) {
      this.loading = false;
      this.errorMsg = 'ไม่พบโทเค็นเชิญผู้มาติดต่อ';
      this.cdr.markForCheck();
      return;
    }
    this.http.get<InviteMetadata>(`/sentinel/public/visitor-invite/${encodeURIComponent(this.token)}`).subscribe({
      next: (res) => {
        this.invite = res;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.errorMsg = err?.error?.detail || 'ลิงก์ลงทะเบียนไม่ถูกต้องหรือหมดอายุแล้ว';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  onDocSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file || !this.token || this.ocrBusy) return;
    this.ocrBusy = true;
    this.cdr.markForCheck();
    const fd = new FormData();
    fd.append('file', file);
    fd.append('documentType', 'AUTO');
    this.http
      .post<{ ok: boolean; document: Record<string, unknown> }>(
        `/sentinel/public/visitor-invite/${encodeURIComponent(this.token)}/ocr-document`,
        fd,
      )
      .subscribe({
        next: (res) => {
          this.ocrDoc = res.document || null;
          this.ocrBusy = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.ocrBusy = false;
          this.cdr.markForCheck();
        },
      });
  }

  onSelfieSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    this.selfieFile = input?.files?.[0] || null;
  }

  submit(): void {
    if (!this.consentAccepted || this.submitting || !this.token) return;
    this.submitting = true;
    this.errorMsg = '';
    this.cdr.markForCheck();
    const fd = new FormData();
    fd.append('consentAccepted', 'true');
    if (this.phoneNumber.trim()) {
      fd.append('phoneNumber', this.phoneNumber.trim());
    }
    if (this.selfieFile) {
      fd.append('photo', this.selfieFile);
    }
    this.http
      .post(`/sentinel/public/visitor-invite/${encodeURIComponent(this.token)}/complete`, fd)
      .subscribe({
        next: () => {
          this.completed = true;
          this.submitting = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.errorMsg = err?.error?.detail || 'ลงทะเบียนไม่สำเร็จ กรุณาลองใหม่อีกครั้ง';
          this.submitting = false;
          this.cdr.markForCheck();
        },
      });
  }
}
