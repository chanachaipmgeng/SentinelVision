import { Component, OnInit } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../services/token.service';

type ErrorCode = '403' | '404' | '500';

const ICONS: Record<ErrorCode, string> = {
  '403': 'ri-lock-2-line',
  '404': 'ri-compass-3-line',
  '500': 'ri-error-warning-line',
};

/** Standalone 403 / 404 / 500 page rendered inside the admin shell (`route.data.code`). */
@Component({
  selector: 'app-error-page',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule],
  template: `
    <section class="sv-error" role="alert">
      <div class="sv-error__icon"><i [class]="icon" aria-hidden="true"></i></div>
      <p class="sv-error__code">{{ code }}</p>
      <h1 class="sv-error__title">{{ 'shell.error.' + code + '.title' | translate }}</h1>
      <p class="sv-error__text">{{ 'shell.error.' + code + '.body' | translate }}</p>
      <div class="sv-error__actions">
        <button type="button" class="ti-btn ti-btn-light" (click)="back()">
          <i class="ri-arrow-left-line"></i> {{ 'shell.common.back' | translate }}
        </button>
        <button type="button" class="ti-btn ti-btn-light" *ngIf="code === '500'" (click)="reload()">
          <i class="ri-refresh-line"></i> {{ 'shell.error.retry' | translate }}
        </button>
        <a [routerLink]="homeLink" class="ti-btn ti-btn-primary-full">
          <i class="ri-home-4-line"></i> {{ 'shell.error.home' | translate }}
        </a>
      </div>
    </section>
  `,
  styles: [
    `
      .sv-error {
        min-height: calc(100dvh - 12rem);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 2rem 1rem;
      }
      .sv-error__icon {
        width: 5rem;
        height: 5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 1.5rem;
        background: var(--dpu-brand-soft);
        color: var(--dpu-brand);
        font-size: 2.5rem;
        margin-bottom: 1rem;
      }
      .sv-error__code {
        margin: 0;
        font-family: var(--dpu-font-display);
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: var(--dpu-ink);
        line-height: 1;
      }
      .sv-error__title {
        margin: 0.5rem 0 0.35rem;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--dpu-ink);
      }
      .sv-error__text {
        margin: 0 0 1.5rem;
        max-width: 32rem;
        color: var(--dpu-muted);
        font-size: 0.92rem;
      }
      .sv-error__actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
      }
    `,
  ],
})
export class ErrorPageComponent implements OnInit {
  code: ErrorCode = '404';
  homeLink = '/admin/home';

  constructor(
    private route: ActivatedRoute,
    private location: Location,
    private tokenService: TokenService,
  ) {}

  get icon(): string {
    return ICONS[this.code];
  }

  ngOnInit(): void {
    const raw = String(this.route.snapshot.data?.['code'] ?? '404');
    this.code = (['403', '404', '500'] as const).includes(raw as ErrorCode) ? (raw as ErrorCode) : '404';
    const companyId = this.tokenService.getSelectCompany()?.companyId;
    this.homeLink = companyId ? `/company/home/${companyId}` : '/admin/home';
  }

  back(): void {
    this.location.back();
  }

  reload(): void {
    window.location.reload();
  }
}
