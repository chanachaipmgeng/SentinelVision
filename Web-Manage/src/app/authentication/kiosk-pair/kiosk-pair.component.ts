import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../shared/services/auth.service';
import { KioskSession, TokenService } from '../../shared/services/token.service';

/**
 * Kiosk pairing screen. The admin creates a device under HR → Security and reads the one-time
 * code aloud / types it here. The device-scoped token pair never appears in a URL; it is kept in
 * sessionStorage for this tab only and refreshed via /auth/kiosk/refresh.
 */
@Component({
  selector: 'app-kiosk-pair',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="dpu-pair">
      <div class="dpu-pair__card">
        <img src="./assets/images/brand-logos/logo.png" alt="SentinelVision" class="dpu-pair__logo" />
        <h1 class="dpu-pair__title">จับคู่ตู้ Kiosk</h1>
        <p class="dpu-pair__subtitle">
          กรอกรหัสจับคู่ 8 หลักที่ผู้ดูแลระบบสร้างจากเมนู HR &rarr; ความปลอดภัย &rarr; ตู้ Kiosk
          (รหัสใช้ได้ครั้งเดียวและหมดอายุใน {{ ttlMinutes }} นาที)
        </p>

        <form (ngSubmit)="pair()" autocomplete="off">
          <label for="pairing-code" class="dpu-pair__label">รหัสจับคู่</label>
          <input
            id="pairing-code"
            class="dpu-pair__input"
            [(ngModel)]="code"
            name="pairingCode"
            placeholder="ABCD-EFGH"
            maxlength="9"
            autocapitalize="characters"
            autocorrect="off"
            spellcheck="false"
            inputmode="text"
            (input)="formatCode()"
            [disabled]="busy"
            autofocus
          />
          @if (error) {
            <p class="dpu-pair__error" role="alert">{{ error }}</p>
          }
          <button type="submit" class="dpu-pair__btn" [disabled]="busy || normalized().length < 8">
            @if (busy) {
              <span class="dpu-pair__spinner"></span>
            }
            จับคู่อุปกรณ์
          </button>
        </form>

        <p class="dpu-pair__hint">
          เมื่อจับคู่แล้ว แท็บเล็ตนี้จะเข้าถึงได้เฉพาะหน้าสแกนใบหน้าของบริษัทที่ผูกไว้เท่านั้น
          หากปิดแท็บ จะต้องขอรหัสจับคู่ใหม่จากผู้ดูแลระบบ
        </p>
        <a routerLink="/auth/login" class="dpu-pair__link">เข้าสู่ระบบในฐานะผู้ดูแลแทน</a>
      </div>
    </div>
  `,
  styles: [
    `
      :host { display: block; min-height: 100vh; }
      .dpu-pair {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 1.5rem;
        background:
          radial-gradient(circle at 20% 20%, rgba(15, 118, 110, 0.35), transparent 45%),
          radial-gradient(circle at 80% 80%, rgba(94, 234, 212, 0.18), transparent 50%),
          #042f2e;
        color: #ecfeff;
        font-family: inherit;
      }
      .dpu-pair__card {
        width: min(28rem, 100%);
        padding: 2rem 2rem 1.5rem;
        border-radius: 1.25rem;
        border: 1px solid rgba(94, 234, 212, 0.28);
        background: rgba(4, 47, 46, 0.78);
        backdrop-filter: blur(12px);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
        text-align: center;
      }
      .dpu-pair__logo { height: 3.25rem; margin: 0 auto 1rem; }
      .dpu-pair__title { margin: 0 0 0.5rem; font-size: 1.6rem; font-weight: 800; }
      .dpu-pair__subtitle { margin: 0 0 1.5rem; font-size: 0.9rem; color: rgba(236, 254, 255, 0.78); line-height: 1.5; }
      .dpu-pair__label { display: block; text-align: start; font-size: 0.8rem; font-weight: 700; margin-bottom: 0.35rem; letter-spacing: 0.04em; text-transform: uppercase; color: rgba(236, 254, 255, 0.7); }
      .dpu-pair__input {
        width: 100%;
        padding: 0.9rem 1rem;
        border-radius: 0.85rem;
        border: 1px solid rgba(94, 234, 212, 0.4);
        background: rgba(255, 255, 255, 0.06);
        color: #fff;
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: 0.35em;
        text-align: center;
        text-transform: uppercase;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }
      .dpu-pair__input:focus { outline: none; border-color: #5eead4; box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.25); }
      .dpu-pair__error { margin: 0.75rem 0 0; color: #fecaca; font-size: 0.85rem; font-weight: 600; }
      .dpu-pair__btn {
        width: 100%;
        margin-top: 1.25rem;
        padding: 0.9rem 1rem;
        border: 0;
        border-radius: 999px;
        background: linear-gradient(135deg, #0f766e, #14b8a6);
        color: #fff;
        font-size: 1rem;
        font-weight: 800;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
      }
      .dpu-pair__btn:disabled { opacity: 0.55; cursor: not-allowed; }
      .dpu-pair__spinner {
        width: 1rem; height: 1rem; border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.4); border-top-color: #fff;
        animation: dpu-spin 0.8s linear infinite;
      }
      @keyframes dpu-spin { to { transform: rotate(360deg); } }
      .dpu-pair__hint { margin: 1.25rem 0 0.5rem; font-size: 0.78rem; color: rgba(236, 254, 255, 0.62); line-height: 1.5; }
      .dpu-pair__link { font-size: 0.8rem; color: #5eead4; text-decoration: underline; }
    `,
  ],
})
export class KioskPairComponent implements OnInit, OnDestroy {
  code = '';
  error = '';
  busy = false;
  readonly ttlMinutes = 10;

  constructor(
    private authService: AuthService,
    private tokenService: TokenService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    document.documentElement.classList.add('dpu-kiosk-mode');
    if (this.tokenService.isKioskSession()) {
      this.router.navigate(['/company/timestamp-face']);
    }
  }

  ngOnDestroy(): void {
    document.documentElement.classList.remove('dpu-kiosk-mode');
  }

  normalized(): string {
    return (this.code || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  formatCode(): void {
    const raw = this.normalized().slice(0, 8);
    this.code = raw.length > 4 ? `${raw.slice(0, 4)}-${raw.slice(4)}` : raw;
    this.error = '';
  }

  pair(): void {
    const code = this.normalized();
    if (code.length < 8 || this.busy) {
      return;
    }
    this.busy = true;
    this.error = '';
    this.authService.kioskPair(code).subscribe({
      next: (session: KioskSession) => {
        this.tokenService.saveKioskSession(session);
        this.tokenService.saveSelectCompany({
          companyId: session.companyId,
          companyName: session.deviceName || 'Kiosk Device',
        } as any);
        this.busy = false;
        this.router.navigate(['/company/timestamp-face']);
      },
      error: (err) => {
        this.busy = false;
        const detail = err?.error?.detail;
        if (err?.status === 429) {
          this.error = 'พยายามจับคู่บ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่';
        } else if (typeof detail === 'string' && /expired/i.test(detail)) {
          this.error = 'รหัสจับคู่หมดอายุแล้ว กรุณาขอรหัสใหม่จากผู้ดูแลระบบ';
        } else if (typeof detail === 'string' && /revoked/i.test(detail)) {
          this.error = 'อุปกรณ์นี้ถูกเพิกถอนสิทธิ์แล้ว กรุณาลงทะเบียนอุปกรณ์ใหม่';
        } else {
          this.error = 'รหัสจับคู่ไม่ถูกต้องหรือถูกใช้ไปแล้ว';
        }
      },
    });
  }
}
