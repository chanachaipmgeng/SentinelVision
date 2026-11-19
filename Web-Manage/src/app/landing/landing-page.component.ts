import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, Renderer2, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { DpuCardTiltDirective } from '../shared/directives/dpu-card-tilt.directive';
import { DpuCountUpDirective } from '../shared/directives/dpu-count-up.directive';
import { DpuRevealDirective } from '../shared/directives/dpu-reveal.directive';
import { EmployeeService } from '../DPU/services/employee.service';
import { TokenService } from '../shared/services/token.service';
import { DpuAuraFieldComponent } from './fx/dpu-aura-field.component';
import { DpuCursorDotComponent } from './fx/dpu-cursor-dot.component';
import { DpuHorizonGlowComponent } from './fx/dpu-horizon-glow.component';
import { DpuMouseGlowComponent } from './fx/dpu-mouse-glow.component';

@Component({
    selector: 'app-landing-page',
    imports: [
        CommonModule,
        RouterModule,
        TranslateModule,
        DpuRevealDirective,
        DpuCountUpDirective,
        DpuCardTiltDirective,
        DpuHorizonGlowComponent,
        DpuAuraFieldComponent,
        DpuMouseGlowComponent,
        DpuCursorDotComponent,
    ],
    templateUrl: './landing-page.component.html',
    styleUrl: './landing-page.component.scss'
})
export class LandingPageComponent implements OnInit, OnDestroy {
  lang = 'th';
  menuOpen = false;

  readonly values = [
    { icon: 'ri-scan-2-line', titleKey: 'landing.value.face.title', bodyKey: 'landing.value.face.body' },
    { icon: 'ri-door-lock-box-line', titleKey: 'landing.value.access.title', bodyKey: 'landing.value.access.body' },
    { icon: 'ri-alarm-warning-line', titleKey: 'landing.value.watchlist.title', bodyKey: 'landing.value.watchlist.body' },
    { icon: 'ri-shield-check-line', titleKey: 'landing.value.visitor.title', bodyKey: 'landing.value.visitor.body' },
    { icon: 'ri-vidicon-line', titleKey: 'landing.value.cctv.title', bodyKey: 'landing.value.cctv.body' },
    { icon: 'ri-broadcast-line', titleKey: 'landing.value.attendance.title', bodyKey: 'landing.value.attendance.body' },
  ];

  readonly features = [
    { titleKey: 'landing.feature.command.title', bodyKey: 'landing.feature.command.body', icon: 'ri-dashboard-3-line', tag: 'Realtime Command' },
    { titleKey: 'landing.feature.kiosk.title', bodyKey: 'landing.feature.kiosk.body', icon: 'ri-camera-lens-line', tag: '6 Station Modes' },
    { titleKey: 'landing.feature.walkby.title', bodyKey: 'landing.feature.walkby.body', icon: 'ri-group-line', tag: 'Zero Latency' },
    { titleKey: 'landing.feature.pdpa.title', bodyKey: 'landing.feature.pdpa.body', icon: 'ri-shield-user-line', tag: 'PDPA Compliant' },
    { titleKey: 'landing.feature.presence.title', bodyKey: 'landing.feature.presence.body', icon: 'ri-radar-line', tag: 'OT Evidence' },
    { titleKey: 'landing.feature.muster.title', bodyKey: 'landing.feature.muster.body', icon: 'ri-building-line', tag: 'Emergency Headcount' },
  ];

  readonly kioskModes = [
    { code: 'ATTENDANCE', icon: 'ri-calendar-check-line', tone: 'cyan', titleKey: 'landing.kiosk.mode.attendance.title', descKey: 'landing.kiosk.mode.attendance.desc' },
    { code: 'ACCESS_CONTROL', icon: 'ri-door-lock-line', tone: 'sky', titleKey: 'landing.kiosk.mode.access.title', descKey: 'landing.kiosk.mode.access.desc' },
    { code: 'WATCHLIST_MONITOR', icon: 'ri-alarm-warning-line', tone: 'rose', titleKey: 'landing.kiosk.mode.watchlist.title', descKey: 'landing.kiosk.mode.watchlist.desc' },
    { code: 'VISITOR_CHECKIN', icon: 'ri-user-shared-line', tone: 'violet', titleKey: 'landing.kiosk.mode.visitor.title', descKey: 'landing.kiosk.mode.visitor.desc' },
    { code: 'EVENT_CHECKIN', icon: 'ri-ticket-2-line', tone: 'amber', titleKey: 'landing.kiosk.mode.event.title', descKey: 'landing.kiosk.mode.event.desc' },
    { code: 'UNIFIED_HYBRID', icon: 'ri-apps-2-line', tone: 'teal', titleKey: 'landing.kiosk.mode.unified.title', descKey: 'landing.kiosk.mode.unified.desc' },
  ];

  readonly metrics = [
    { value: 512, decimals: 0, suffix: '-d', labelKey: 'landing.metric.embedding' },
    { value: 99.8, decimals: 1, suffix: '%', labelKey: 'landing.metric.accuracy' },
    { value: 6, decimals: 0, suffix: ' Modes', labelKey: 'landing.metric.modes' },
    { value: 100, decimals: 0, suffix: '%', labelKey: 'landing.metric.pdpa' },
  ];

  readonly marqueeChips = [
    'landing.marquee.face',
    'landing.marquee.access',
    'landing.marquee.watchlist',
    'landing.marquee.visitor',
    'landing.marquee.events',
    'landing.marquee.cctv',
    'landing.marquee.attendance',
    'landing.marquee.presence',
    'landing.marquee.muster',
    'landing.marquee.export',
  ];

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private renderer: Renderer2,
    private router: Router,
    private translate: TranslateService,
    private tokens: TokenService,
    private empService: EmployeeService,
  ) {}

  ngOnInit(): void {
    this.lang = this.translate.currentLang || this.translate.defaultLang || 'th';
    this.renderer.addClass(this.document.body, 'dpu-landing-body');
    this.maybeRedirectAuthenticated();
  }

  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, 'dpu-landing-body');
  }

  setLang(code: string): void {
    this.lang = code;
    this.translate.use(code);
    try {
      localStorage.setItem('dpu-lang', code);
    } catch {
      /* ignore */
    }
  }

  scrollTo(id: string): void {
    this.menuOpen = false;
    const el = this.document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  private maybeRedirectAuthenticated(): void {
    if (this.tokens.isKioskSession()) {
      this.router.navigate(['/company/timestamp-face']);
      return;
    }
    if (!this.tokens.getToken()) {
      return;
    }
    const role = String(this.tokens.getUser()?.member?.role ?? '');
    if (role === '99') {
      this.router.navigate(['/admin/member-manage']);
      return;
    }
    const memberId = this.tokens.getUser()?.member?.memberId;
    if (!memberId) {
      this.router.navigate(['/auth/login']);
      return;
    }
    this.empService.getCompanyAdmin(memberId).subscribe({
      next: (companies) => {
        if (companies?.length) {
          this.router.navigate(['/company/home/' + companies[0].companyId]);
        } else {
          this.router.navigate(['/auth/login']);
        }
      },
      error: () => this.router.navigate(['/auth/login']),
    });
  }
}
