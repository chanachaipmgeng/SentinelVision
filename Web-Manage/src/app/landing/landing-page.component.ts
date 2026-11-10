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
  standalone: true,
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
  styleUrl: './landing-page.component.scss',
})
export class LandingPageComponent implements OnInit, OnDestroy {
  lang = 'th';
  menuOpen = false;

  readonly values = [
    { icon: 'ri-face-recognition-line', titleKey: 'landing.value.face.title', bodyKey: 'landing.value.face.body' },
    { icon: 'ri-cctv-line', titleKey: 'landing.value.cctv.title', bodyKey: 'landing.value.cctv.body' },
    { icon: 'ri-shield-keyhole-line', titleKey: 'landing.value.access.title', bodyKey: 'landing.value.access.body' },
    { icon: 'ri-calendar-check-line', titleKey: 'landing.value.attendance.title', bodyKey: 'landing.value.attendance.body' },
  ];

  readonly features = [
    { titleKey: 'landing.feature.kiosk.title', bodyKey: 'landing.feature.kiosk.body' },
    { titleKey: 'landing.feature.hybrid.title', bodyKey: 'landing.feature.hybrid.body' },
    { titleKey: 'landing.feature.shift.title', bodyKey: 'landing.feature.shift.body' },
    { titleKey: 'landing.feature.export.title', bodyKey: 'landing.feature.export.body' },
  ];

  readonly metrics = [
    { value: 512, suffix: '-d', labelKey: 'landing.metric.embedding' },
    { value: 1, suffix: ':N', labelKey: 'landing.metric.match' },
    { value: 24, suffix: '/7', labelKey: 'landing.metric.uptime' },
  ];

  readonly marqueeChips = [
    'landing.marquee.face',
    'landing.marquee.cctv',
    'landing.marquee.access',
    'landing.marquee.attendance',
    'landing.marquee.hybrid',
    'landing.marquee.shift',
    'landing.marquee.export',
    'landing.marquee.kiosk',
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
