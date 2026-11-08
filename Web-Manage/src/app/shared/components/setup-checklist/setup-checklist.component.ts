import { Component, ElementRef, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { Observable, forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { TokenService } from '../../services/token.service';
import { PermissionService } from '../../services/permission.service';

export type SetupStepId = 'location' | 'employees' | 'faces' | 'kiosk' | 'notifications';

export interface SetupStep {
  id: SetupStepId;
  title: string;
  hint: string;
  link: string;
  icon: string;
  /** null = status unavailable to this caller (step hidden). */
  done: boolean | null;
}

export const SETUP_DISMISS_PREFIX = 'sv_setup_checklist_dismissed:';

@Component({
  selector: 'app-setup-checklist',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  templateUrl: './setup-checklist.component.html',
  styleUrl: './setup-checklist.component.css',
})
export class SetupChecklistComponent implements OnInit {
  @Input() companyId: string | null = null;

  steps: SetupStep[] = [];
  loading = true;
  dismissed = false;

  constructor(
    private http: HttpClient,
    private tokenService: TokenService,
    private permissions: PermissionService,
    private host: ElementRef<HTMLElement>,
  ) {}

  get visibleSteps(): SetupStep[] {
    return this.steps.filter((s) => s.done !== null);
  }

  get doneCount(): number {
    return this.visibleSteps.filter((s) => s.done).length;
  }

  get allDone(): boolean {
    return this.visibleSteps.length > 0 && this.doneCount === this.visibleSteps.length;
  }

  get progressPct(): number {
    const total = this.visibleSteps.length;
    return total ? Math.round((this.doneCount / total) * 100) : 0;
  }

  get show(): boolean {
    return !!this.companyId && !this.dismissed && !this.loading && this.visibleSteps.length > 0 && !this.allDone;
  }

  ngOnInit(): void {
    if (!this.companyId) {
      const id = this.tokenService.getSelectCompany()?.companyId;
      this.companyId = id ? String(id) : null;
    }
    if (!this.companyId) {
      this.loading = false;
      return;
    }
    this.dismissed = this.readDismissed();
    if (this.dismissed) {
      this.loading = false;
      return;
    }
    this.refresh();
  }

  refresh(): void {
    const cid = this.companyId!;
    this.loading = true;
    forkJoin({
      locations: this.probe(this.http.get<unknown[]>(`/company-locations/company/${cid}`), (rows) =>
        Array.isArray(rows) ? rows.length > 0 : null,
      ),
      pdpa: this.http
        .get<{ totalEmployees?: number; enrolledEmployees?: number }>(`/hr/company/${cid}/pdpa-summary`)
        .pipe(catchError(() => of(null))),
      devices: this.probe(
        this.http.get<{ isPaired?: boolean; revokedAt?: string | null }[]>(`/devices/company/${cid}/devices`),
        (rows) => (Array.isArray(rows) ? rows.some((d) => d.isPaired && !d.revokedAt) : null),
      ),
      notify: this.permissions.has('notifications.manage')
        ? this.probe(
            this.http.get<{ hasLineToken?: boolean; webhookUrl?: string }>(`/notifications/company/${cid}/settings`),
            (s) => !!(s && (s.hasLineToken || (s.webhookUrl || '').trim())),
          )
        : of(null),
    }).subscribe((r) => {
      const employees =
        r.pdpa && typeof r.pdpa.totalEmployees === 'number' ? r.pdpa.totalEmployees > 0 : null;
      const faces =
        r.pdpa && typeof r.pdpa.enrolledEmployees === 'number' ? r.pdpa.enrolledEmployees > 0 : null;
      this.steps = [
        this.step('location', '/company/company-location', 'ri-map-pin-line', r.locations),
        this.step('employees', '/company/company-emp', 'ri-team-line', employees),
        this.step('faces', '/company/company-emp', 'ri-user-smile-line', faces),
        this.step('kiosk', '/company/devices', 'ri-tablet-line', r.devices),
        this.step('notifications', '/company/audit-log', 'ri-notification-3-line', r.notify),
      ];
      this.loading = false;
    });
  }

  dismiss(): void {
    this.dismissed = true;
    try {
      localStorage.setItem(SETUP_DISMISS_PREFIX + this.companyId, '1');
    } catch {
      /* ignore */
    }
  }

  /** Expand + scroll into view (used by the welcome wizard). */
  reveal(): void {
    if (this.dismissed) {
      this.dismissed = false;
      try {
        localStorage.removeItem(SETUP_DISMISS_PREFIX + this.companyId);
      } catch {
        /* ignore */
      }
      this.refresh();
    }
    setTimeout(() => this.host.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  }

  private step(id: SetupStepId, link: string, icon: string, done: boolean | null): SetupStep {
    return {
      id,
      link,
      icon,
      done,
      title: `shell.setup.${id}.title`,
      hint: `shell.setup.${id}.hint`,
    };
  }

  private probe<T>(req: Observable<T>, test: (v: T) => boolean | null): Observable<boolean | null> {
    return req.pipe(
      map(test),
      catchError(() => of(null)),
    );
  }

  private readDismissed(): boolean {
    try {
      return localStorage.getItem(SETUP_DISMISS_PREFIX + this.companyId) === '1';
    } catch {
      return false;
    }
  }
}
