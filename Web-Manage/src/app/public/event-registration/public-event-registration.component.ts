import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

interface PublicEventDetails {
  eventId: string;
  name: string;
  publicSlug: string;
  locationName?: string | null;
  startAt: string;
  endAt: string;
  welcomeMessage?: string | null;
  description?: string | null;
  capacity: number;
  registeredCount: number;
  remainingSeats: number;
  registrationOpen: boolean;
  registrationDeadline?: string | null;
  isSoldOut: boolean;
  status: string;
}

interface EventRegistrationResult {
  registered: boolean;
  registrationId: string;
  passCode: string;
  qrDataUrl?: string;
  eventName: string;
  fullName: string;
  email: string;
  startAt: string;
  endAt: string;
  locationName?: string | null;
  welcomeMessage?: string | null;
}

@Component({
  selector: 'app-public-event-registration',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-screen bg-[#04080f] text-slate-100 flex items-center justify-center p-4">
      <div class="w-full max-w-xl rounded-2xl border border-white/10 bg-[#070d14] shadow-2xl p-6 md:p-8 space-y-6">
        <!-- Top branding header -->
        <div class="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <span class="text-xs font-mono font-semibold uppercase tracking-widest text-cyan-400">SentinelVision Event Pass</span>
            <h1 class="text-xl md:text-2xl font-bold text-slate-100 mt-1">ลงทะเบียนเข้าร่วมงาน</h1>
          </div>
          <span class="badge bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs px-3 py-1 rounded-full flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            Public Portal
          </span>
        </div>

        <!-- Loading State -->
        <div *ngIf="loading" class="text-center py-12 text-slate-400 text-sm">
          <i class="ri-loader-4-line text-2xl animate-spin block mb-2 text-cyan-400"></i>
          กำลังโหลดข้อมูลกิจกรรม...
        </div>

        <!-- Error State -->
        <div *ngIf="!loading && errorMsg" class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
          <i class="ri-error-warning-line text-lg mt-0.5 shrink-0"></i>
          <div>{{ errorMsg }}</div>
        </div>

        <!-- Completed Confirmation & Digital Badge -->
        <div *ngIf="!loading && completed && result" class="space-y-5">
          <div class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center">
            <div class="text-emerald-300 font-bold text-lg flex items-center justify-center gap-2">
              <i class="ri-checkbox-circle-fill text-2xl text-emerald-400"></i>
              ลงทะเบียนสำเร็จเรียบร้อย!
            </div>
            <p class="text-xs text-slate-300 mt-1 mb-0">
              ยินดีต้อนรับสู่ <strong>{{ result.eventName }}</strong> ระบบออกบัตรเข้าร่วมงานดิจิทัลให้ท่านแล้ว
            </p>
          </div>

          <div class="rounded-2xl border border-cyan-500/30 bg-gradient-to-b from-[#0a1525] to-[#04080f] p-6 shadow-2xl relative overflow-hidden">
            <div class="absolute top-0 right-0 transform translate-x-4 -translate-y-4 w-36 h-36 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none"></div>

            <div class="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <span class="text-[10px] font-mono tracking-widest text-cyan-400 uppercase">EVENT PASS / TICKET</span>
                <div class="text-lg font-bold text-slate-100">{{ result.fullName }}</div>
              </div>
              <span class="px-2.5 py-1 text-xs rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold font-mono">
                PASS CONFIRMED
              </span>
            </div>

            <div *ngIf="result.qrDataUrl" class="my-5 flex flex-col items-center">
              <div class="p-3 bg-white rounded-2xl shadow-xl border border-slate-200 inline-block">
                <img [src]="result.qrDataUrl" alt="Event Pass QR" class="w-48 h-48 object-contain" />
              </div>
              <span class="text-xs text-slate-400 mt-2 font-mono">
                PASS: {{ result.passCode }}
              </span>
            </div>

            <div class="space-y-2 text-xs bg-slate-900/70 p-3.5 rounded-xl border border-white/5">
              <div class="flex justify-between">
                <span class="text-slate-400">ชื่องาน:</span>
                <strong class="text-slate-200">{{ result.eventName }}</strong>
              </div>
              <div *ngIf="result.locationName" class="flex justify-between">
                <span class="text-slate-400">สถานที่:</span>
                <span class="text-slate-200">{{ result.locationName }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">วันเวลา:</span>
                <span class="text-cyan-300 font-mono">{{ result.startAt | date: 'dd/MM/yyyy HH:mm' }} - {{ result.endAt | date: 'HH:mm' }}</span>
              </div>
              <div *ngIf="result.welcomeMessage" class="pt-2 border-t border-white/5 text-slate-300 text-[11px] italic">
                "{{ result.welcomeMessage }}"
              </div>
            </div>

            <div class="mt-4 pt-3 border-t border-white/10 text-center text-xs text-cyan-300">
              💡 กรุณาบันทึกภาพหน้าจอ (Screenshot) บัตรนี้ไว้ เพื่อใช้สแกนผ่าน Kiosk หรือจุดลงทะเบียนหน้างาน
            </div>
          </div>
        </div>

        <!-- Event Details & Registration Form -->
        <ng-container *ngIf="!loading && event && !completed">
          <div class="p-5 rounded-xl bg-slate-900/60 border border-white/10 space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <h2 class="text-lg font-bold text-slate-100">{{ event.name }}</h2>
                <div *ngIf="event.locationName" class="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                  <i class="ri-map-pin-line text-cyan-400"></i>
                  {{ event.locationName }}
                </div>
              </div>

              <!-- Remaining seats pill -->
              <div class="shrink-0">
                <span *ngIf="event.isSoldOut" class="badge bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs px-2.5 py-1 rounded-full font-bold">
                  ที่นั่งเต็มแล้ว
                </span>
                <span *ngIf="!event.isSoldOut && event.remainingSeats <= 10" class="badge bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs px-2.5 py-1 rounded-full font-bold animate-pulse">
                  เหลือ {{ event.remainingSeats }} ที่นั่งสุดท้าย
                </span>
                <span *ngIf="!event.isSoldOut && event.remainingSeats > 10" class="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs px-2.5 py-1 rounded-full font-medium">
                  เหลือ {{ event.remainingSeats }} / {{ event.capacity }} ที่นั่ง
                </span>
              </div>
            </div>

            <div class="text-xs text-slate-300 flex flex-wrap gap-4 pt-1">
              <span class="flex items-center gap-1.5">
                <i class="ri-calendar-event-line text-cyan-400"></i>
                {{ event.startAt | date: 'dd/MM/yyyy HH:mm' }} - {{ event.endAt | date: 'HH:mm' }}
              </span>
              <span *ngIf="event.registrationDeadline" class="text-slate-400 flex items-center gap-1.5">
                <i class="ri-timer-line text-amber-400"></i>
                ปิดรับลงทะเบียน: {{ event.registrationDeadline | date: 'dd/MM/yyyy HH:mm' }}
              </span>
            </div>

            <p *ngIf="event.description" class="text-xs text-slate-400 pt-2 border-t border-white/5 mb-0">
              {{ event.description }}
            </p>
          </div>

          <!-- Registration Gate Notice if Closed or Sold out -->
          <div *ngIf="!event.registrationOpen" class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs text-center">
            กิจกรรมนี้ยังไม่เปิดรับลงทะเบียน หรือสิ้นสุดระยะเวลาการลงทะเบียนแล้ว
          </div>

          <!-- Registration Form -->
          <form *ngIf="event.registrationOpen && !event.isSoldOut" class="space-y-4" (ngSubmit)="submit()">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">
                ชื่อ - นามสกุล <span class="text-rose-400">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="fullName"
                name="fullName"
                required
                placeholder="สมชาย ใจดี"
                class="w-full rounded-xl bg-slate-950/80 border border-white/15 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none transition"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">
                อีเมล <span class="text-rose-400">*</span>
              </label>
              <input
                type="email"
                [(ngModel)]="email"
                name="email"
                required
                placeholder="somchai@example.com"
                class="w-full rounded-xl bg-slate-950/80 border border-white/15 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none transition"
              />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">เบอร์โทรศัพท์ (ไม่บังคับ)</label>
                <input
                  type="tel"
                  [(ngModel)]="phoneNumber"
                  name="phoneNumber"
                  placeholder="08x-xxx-xxxx"
                  class="w-full rounded-xl bg-slate-950/80 border border-white/15 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none transition"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">หน่วยงาน / บริษัท (ไม่บังคับ)</label>
                <input
                  type="text"
                  [(ngModel)]="organization"
                  name="organization"
                  placeholder="บริษัท เอบีซี จำกัด"
                  class="w-full rounded-xl bg-slate-950/80 border border-white/15 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none transition"
                />
              </div>
            </div>

            <!-- PDPA Consent -->
            <label class="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer pt-1">
              <input type="checkbox" [(ngModel)]="consentAccepted" name="consentAccepted" class="mt-0.5 rounded border-white/20 text-cyan-500" />
              <span>
                ข้าพเจ้ายินยอมให้ประมวลผลข้อมูลส่วนบุคคลสำหรับการลงทะเบียนและออกบัตรดิจิทัลเข้าร่วมงานตามนโยบายคุ้มครองข้อมูลส่วนบุคคล (PDPA)
              </span>
            </label>

            <!-- Submit Button -->
            <button
              type="submit"
              [disabled]="submitting || !fullName || !email || !consentAccepted"
              class="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20"
            >
              <i *ngIf="submitting" class="ri-loader-4-line animate-spin"></i>
              {{ submitting ? 'กำลังบันทึกการลงทะเบียน...' : 'ยืนยันการลงทะเบียน (รับ Digital Pass)' }}
            </button>
          </form>
        </ng-container>
      </div>
    </div>
  `,
})
export class PublicEventRegistrationComponent implements OnInit {
  slug = '';
  loading = true;
  submitting = false;
  completed = false;
  errorMsg = '';
  event: PublicEventDetails | null = null;
  result: EventRegistrationResult | null = null;

  fullName = '';
  email = '';
  phoneNumber = '';
  organization = '';
  consentAccepted = false;

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.slug = this.route.snapshot.paramMap.get('slug') || '';
    if (!this.slug) {
      this.loading = false;
      this.errorMsg = 'ไม่พบรหัสกิจกรรม (Missing Event Slug)';
      this.cdr.markForCheck();
      return;
    }
    this.fetchEventDetails();
  }

  fetchEventDetails(): void {
    this.loading = true;
    this.http.get<PublicEventDetails>(`/sentinel/public/events/${encodeURIComponent(this.slug)}`).subscribe({
      next: (res) => {
        this.event = res;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.errorMsg = err?.error?.detail || 'ไม่พบกิจกรรมหรือลิงก์ลงทะเบียนไม่ถูกต้อง';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  submit(): void {
    if (!this.consentAccepted || !this.fullName.trim() || !this.email.trim() || this.submitting) {
      return;
    }
    this.submitting = true;
    this.errorMsg = '';
    this.cdr.markForCheck();

    const payload = {
      fullName: this.fullName.trim(),
      email: this.email.trim(),
      phoneNumber: this.phoneNumber.trim() || null,
      organization: this.organization.trim() || null,
      consentAccepted: true,
    };

    this.http
      .post<EventRegistrationResult>(`/sentinel/public/events/${encodeURIComponent(this.slug)}/register`, payload)
      .subscribe({
        next: (res) => {
          this.result = res;
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
