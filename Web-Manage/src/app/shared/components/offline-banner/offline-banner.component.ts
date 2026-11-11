import { Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { TranslateModule } from '@ngx-translate/core';
import { Subscription, timeout } from 'rxjs';

const POLL_MS = 30_000;
const PROBE_TIMEOUT_MS = 8_000;

/** Connectivity banner: browser offline OR `/health` unreachable (polled only while the tab is visible). */
@Component({
    selector: 'app-offline-banner',
    imports: [CommonModule, TranslateModule],
    template: `
    <div class="sv-offline" *ngIf="visible" role="status" aria-live="polite">
      <i class="ri-wifi-off-line" aria-hidden="true"></i>
      <span class="sv-offline__text">
        {{ (browserOffline ? 'shell.offline.browser' : 'shell.offline.server') | translate }}
      </span>
      <button type="button" class="sv-offline__btn" (click)="probe()" [disabled]="probing">
        {{ 'shell.offline.retry' | translate }}
      </button>
      <button type="button" class="sv-offline__close" (click)="dismiss()" [attr.aria-label]="'shell.common.close' | translate">
        <i class="ri-close-line"></i>
      </button>
    </div>
  `,
    styles: [
        `
      .sv-offline {
        position: sticky;
        top: 3.75rem;
        z-index: 45;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 0 0 0.75rem;
        padding: 0.55rem 0.85rem;
        border-radius: var(--dpu-radius-sm);
        border: 1px solid var(--sv-warning-border, rgba(180, 83, 9, 0.3));
        background: var(--sv-warning-bg, #fff7ed);
        color: var(--dpu-warning);
        font-size: 0.85rem;
        font-weight: 600;
      }
      .sv-offline__text {
        flex: 1;
      }
      .sv-offline__btn {
        border: 1px solid currentColor;
        background: transparent;
        color: inherit;
        border-radius: 999px;
        padding: 0.15rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 600;
      }
      .sv-offline__btn:disabled {
        opacity: 0.6;
      }
      .sv-offline__close {
        border: 0;
        background: transparent;
        color: inherit;
        font-size: 1.05rem;
        line-height: 1;
      }
    `,
    ]
})
export class OfflineBannerComponent implements OnInit, OnDestroy {
  browserOffline = typeof navigator !== 'undefined' && navigator.onLine === false;
  serverDown = false;
  dismissed = false;
  probing = false;

  private timer?: ReturnType<typeof setInterval>;
  private probeSub?: Subscription;
  private readonly onOnline = () => this.zone.run(() => this.setBrowserOffline(false));
  private readonly onOffline = () => this.zone.run(() => this.setBrowserOffline(true));
  private readonly onVisibility = () => {
    if (document.visibilityState === 'visible') {
      this.zone.run(() => this.probe());
    }
  };

  constructor(private http: HttpClient, private zone: NgZone) {}

  get visible(): boolean {
    return !this.dismissed && (this.browserOffline || this.serverDown);
  }

  ngOnInit(): void {
    window.addEventListener('online', this.onOnline);
    window.addEventListener('offline', this.onOffline);
    document.addEventListener('visibilitychange', this.onVisibility);
    this.zone.runOutsideAngular(() => {
      this.timer = setInterval(() => {
        if (document.visibilityState === 'visible') {
          this.zone.run(() => this.probe());
        }
      }, POLL_MS);
    });
  }

  ngOnDestroy(): void {
    window.removeEventListener('online', this.onOnline);
    window.removeEventListener('offline', this.onOffline);
    document.removeEventListener('visibilitychange', this.onVisibility);
    if (this.timer) clearInterval(this.timer);
    this.probeSub?.unsubscribe();
  }

  probe(): void {
    if (this.probing) return;
    this.probing = true;
    this.probeSub = this.http
      .get('/health')
      .pipe(timeout(PROBE_TIMEOUT_MS))
      .subscribe({
        next: () => this.setServerDown(false),
        error: (err: unknown) => {
          const status = err instanceof HttpErrorResponse ? err.status : 0;
          this.setServerDown(status === 0 || status >= 500);
        },
      });
  }

  dismiss(): void {
    this.dismissed = true;
  }

  private setServerDown(down: boolean): void {
    this.probing = false;
    if (down && !this.serverDown) this.dismissed = false;
    this.serverDown = down;
  }

  private setBrowserOffline(offline: boolean): void {
    if (offline && !this.browserOffline) this.dismissed = false;
    this.browserOffline = offline;
    if (!offline) this.probe();
  }
}
