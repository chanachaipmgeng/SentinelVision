import { Injectable, NgZone, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthService } from './auth.service';
import { PermissionService } from './permission.service';
import { TokenService } from './token.service';
import { CompanySettingsApiService } from '../../DPU/company-management/settings/company-settings-api.service';

const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'] as const;

/**
 * Admin SPA idle logout. Minutes come from company session-settings (0 = disabled).
 * Skips kiosk sessions — those keep their own keep-alive / pairing lifecycle.
 */
@Injectable({ providedIn: 'root' })
export class IdleTimeoutService implements OnDestroy {
  private minutes = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private bound = false;
  private loggingOut = false;
  private readonly onActivity = () => this.bump();
  private companyWatch?: Subscription;

  constructor(
    private zone: NgZone,
    private auth: AuthService,
    private tokens: TokenService,
    private permissions: PermissionService,
    private settingsApi: CompanySettingsApiService,
  ) {}

  /** Start watching the selected company; call from content-layout. */
  start(): void {
    if (this.bound) return;
    this.bound = true;
    this.zone.runOutsideAngular(() => {
      for (const ev of ACTIVITY_EVENTS) {
        window.addEventListener(ev, this.onActivity, { passive: true });
      }
    });
    this.reloadForSelectedCompany();
  }

  stop(): void {
    if (!this.bound) return;
    this.bound = false;
    for (const ev of ACTIVITY_EVENTS) {
      window.removeEventListener(ev, this.onActivity);
    }
    this.clearTimer();
    this.companyWatch?.unsubscribe();
    this.companyWatch = undefined;
  }

  ngOnDestroy(): void {
    this.stop();
  }

  /** Apply minutes immediately (after settings save) without a refetch. */
  applyMinutes(minutes: number): void {
    this.minutes = Math.max(0, Math.min(480, Math.floor(Number(minutes) || 0)));
    this.bump();
  }

  reloadForSelectedCompany(): void {
    if (this.tokens.isKioskSession()) {
      this.applyMinutes(0);
      return;
    }
    const companyId = this.tokens.getSelectCompany()?.companyId || '';
    if (!companyId) {
      this.applyMinutes(0);
      return;
    }
    this.settingsApi.getSessionSettings(companyId).subscribe({
      next: (s) => this.applyMinutes(Number(s?.idleTimeoutMinutes ?? 0)),
      error: () => this.applyMinutes(0),
    });
  }

  private bump(): void {
    this.clearTimer();
    if (this.minutes <= 0 || this.tokens.isKioskSession() || !this.tokens.getToken()) {
      return;
    }
    const ms = this.minutes * 60_000;
    this.zone.runOutsideAngular(() => {
      this.timer = setTimeout(() => this.zone.run(() => this.logout()), ms);
    });
  }

  private clearTimer(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private logout(): void {
    if (this.loggingOut || this.tokens.isKioskSession()) return;
    this.loggingOut = true;
    this.clearTimer();
    this.auth.logout(this.tokens.getRefreshToken()).subscribe({
      next: () => {
        this.permissions.clear();
        this.tokens.signOut();
        this.loggingOut = false;
      },
      error: () => {
        this.permissions.clear();
        this.tokens.signOut();
        this.loggingOut = false;
      },
    });
  }
}
