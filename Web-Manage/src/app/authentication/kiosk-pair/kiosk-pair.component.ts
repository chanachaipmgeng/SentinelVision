import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../shared/services/auth.service';
import { KioskSession, TokenService } from '../../shared/services/token.service';
import { CompanyModel } from '../../DPU/models/company.model';

/**
 * Kiosk pairing screen. The admin creates a device under HR → Security and types the one-time
 * code here. The device-scoped token pair never appears in a URL; it is kept in sessionStorage
 * for this tab only and refreshed via /auth/kiosk/refresh.
 */
@Component({
  selector: 'app-kiosk-pair',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TranslateModule],
  template: `
    <div class="dpu-pair">
      <header class="dpu-pair__topbar">
        <a routerLink="/" class="dpu-pair__back">
          <i class="ri-arrow-left-line"></i>
          <span>{{ lang === 'th' ? 'กลับสู่หน้าหลัก' : 'Back to Home' }}</span>
        </a>
        <div class="dpu-pair__lang" role="group" aria-label="Language selection">
          <button type="button" [class.is-active]="lang === 'th'" (click)="setLang('th')">TH</button>
          <span>/</span>
          <button type="button" [class.is-active]="lang === 'en'" (click)="setLang('en')">EN</button>
        </div>
      </header>

      <main id="main-content" class="dpu-pair__card" tabindex="-1">
        <img src="./assets/images/brand-logos/ivap-logo-light.png" alt="Sentinel by IVAP" class="dpu-pair__logo" />
        <p class="dpu-pair__byline">Sentinel by IVAP</p>
        <h1 class="dpu-pair__title">{{ 'kioskPair.title' | translate }}</h1>
        <p class="dpu-pair__subtitle">
          {{ 'kioskPair.subtitle' | translate: { ttl: ttlMinutes } }}
        </p>

        <form (ngSubmit)="pair()" autocomplete="off">
          <label for="pairing-code" class="dpu-pair__label">{{ 'kioskPair.codeLabel' | translate }}</label>
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
            {{ 'kioskPair.submit' | translate }}
          </button>
        </form>

        <p class="dpu-pair__hint">
          {{ 'kioskPair.hint' | translate }}
        </p>
        <a routerLink="/auth/login" class="dpu-pair__link">{{ 'kioskPair.adminLogin' | translate }}</a>
      </main>
    </div>
  `,
  styles: [
    `
      :host { display: block; min-height: 100vh; }
      .dpu-pair {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 1.25rem;
        gap: 1rem;
        background:
          radial-gradient(ellipse 80% 55% at 50% -10%, rgba(20, 184, 166, 0.22), transparent 60%),
          radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.12), transparent 50%),
          #04080f;
        color: #f1f5f9;
        font-family: inherit;
      }
      .dpu-pair__topbar {
        width: min(28rem, 100%);
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.85rem;
      }
      .dpu-pair__back {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: #94a3b8;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.2s ease;
      }
      .dpu-pair__back:hover { color: #5eead4; }
      .dpu-pair__lang {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        color: #64748b;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 9999px;
        padding: 0.25rem 0.6rem;
      }
      .dpu-pair__lang button {
        border: 0;
        background: transparent;
        color: #94a3b8;
        font-size: 0.75rem;
        font-weight: 700;
        cursor: pointer;
        padding: 0.15rem 0.3rem;
        border-radius: 9999px;
      }
      .dpu-pair__lang button.is-active {
        color: #041217;
        background: #2dd4bf;
      }
      .dpu-pair__card {
        width: min(28rem, 100%);
        padding: 2rem 1.75rem 1.5rem;
        border-radius: 1.25rem;
        border: 1px solid transparent;
        background:
          linear-gradient(180deg, rgba(10, 18, 30, 0.92), rgba(5, 10, 18, 0.96)) padding-box,
          linear-gradient(180deg, rgba(45, 212, 191, 0.45), rgba(255, 255, 255, 0.08) 45%, transparent) border-box;
        backdrop-filter: blur(18px) saturate(1.15);
        -webkit-backdrop-filter: blur(18px) saturate(1.15);
        box-shadow:
          0 1px 0 rgba(255, 255, 255, 0.08) inset,
          0 24px 60px rgba(0, 0, 0, 0.5);
        text-align: center;
      }
      .dpu-pair__logo { height: 2.4rem; margin: 0 auto 0.55rem; }
      .dpu-pair__byline {
        margin: 0 0 1rem;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #5eead4;
      }
      .dpu-pair__title { margin: 0 0 0.5rem; font-size: 1.55rem; font-weight: 800; color: #f8fafc; }
      .dpu-pair__subtitle { margin: 0 0 1.4rem; font-size: 0.88rem; color: #cbd5e1; line-height: 1.55; }
      .dpu-pair__label { display: block; text-align: start; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.35rem; letter-spacing: 0.04em; text-transform: uppercase; color: #94a3b8; }
      .dpu-pair__input {
        width: 100%;
        padding: 0.85rem 1rem;
        border-radius: 0.85rem;
        border: 1px solid rgba(45, 212, 191, 0.35);
        background: rgba(15, 23, 42, 0.7);
        color: #f8fafc;
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: 0.3em;
        text-align: center;
        text-transform: uppercase;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }
      .dpu-pair__input:focus {
        outline: none;
        border-color: #2dd4bf;
        box-shadow: 0 0 0 4px rgba(45, 212, 191, 0.2), 0 0 22px -4px rgba(20, 184, 166, 0.45);
        background: rgba(15, 23, 42, 0.9);
      }
      .dpu-pair__error { margin: 0.75rem 0 0; color: #fca5a5; font-size: 0.85rem; font-weight: 600; }
      .dpu-pair__btn {
        width: 100%;
        margin-top: 1.2rem;
        padding: 0.9rem 1rem;
        border: 0;
        border-radius: 999px;
        background: linear-gradient(135deg, #0f766e, #14b8a6);
        color: #fff;
        font-size: 0.98rem;
        font-weight: 800;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        box-shadow: 0 4px 22px -2px rgba(15, 118, 110, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.22);
        transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.25s ease, filter 0.25s ease;
      }
      .dpu-pair__btn:hover:not(:disabled) {
        transform: translateY(-1px);
        filter: brightness(1.05);
        box-shadow: 0 8px 28px -2px rgba(20, 184, 166, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.28);
      }
      .dpu-pair__btn:disabled {
        opacity: 0.5;
        cursor: not-allowed !important;
      }
      .dpu-pair__spinner {
        width: 1rem; height: 1rem; border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.4); border-top-color: #fff;
        animation: dpu-spin 0.8s linear infinite;
      }
      @keyframes dpu-spin { to { transform: rotate(360deg); } }
      .dpu-pair__hint { margin: 1.15rem 0 0.55rem; font-size: 0.78rem; color: #94a3b8; line-height: 1.5; }
      .dpu-pair__link { font-size: 0.82rem; color: #5eead4; text-decoration: underline; }
    `,
  ],
})
export class KioskPairComponent implements OnInit, OnDestroy {
  lang = 'th';
  code = '';
  error = '';
  busy = false;
  readonly ttlMinutes = 10;

  constructor(
    private authService: AuthService,
    private tokenService: TokenService,
    private router: Router,
    private translate: TranslateService,
  ) {}

  ngOnInit(): void {
    const saved = localStorage.getItem('dpu-lang') || localStorage.getItem('sv_lang');
    this.lang = saved === 'en' ? 'en' : (this.translate.currentLang || this.translate.defaultLang || 'th');
    this.translate.use(this.lang);
    document.documentElement.classList.add('dpu-kiosk-mode');
    if (this.tokenService.isKioskSession()) {
      this.router.navigate(['/company/timestamp-face']);
    }
  }

  ngOnDestroy(): void {
    document.documentElement.classList.remove('dpu-kiosk-mode');
  }

  setLang(code: 'th' | 'en'): void {
    this.lang = code;
    this.translate.use(code);
    try {
      localStorage.setItem('dpu-lang', code);
      localStorage.setItem('sv_lang', code);
    } catch {
      /* ignore */
    }
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
        } as CompanyModel);
        this.busy = false;
        this.router.navigate(['/company/timestamp-face']);
      },
      error: (err) => {
        this.busy = false;
        const detail = err?.error?.detail;
        if (err?.status === 429) {
          this.error = this.translate.instant('kioskPair.errorRateLimit');
        } else if (typeof detail === 'string' && /expired/i.test(detail)) {
          this.error = this.translate.instant('kioskPair.errorExpired');
        } else if (typeof detail === 'string' && /revoked/i.test(detail)) {
          this.error = this.translate.instant('kioskPair.errorRevoked');
        } else {
          this.error = this.translate.instant('kioskPair.errorInvalid');
        }
      },
    });
  }
}
