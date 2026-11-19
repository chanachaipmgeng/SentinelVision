import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';
import { BentoGridComponent } from './bento-grid.component';
import { BentoCardComponent } from './bento-card.component';
import { BentoStatComponent } from './bento-stat.component';

@Component({
  imports: [BentoGridComponent, BentoCardComponent, BentoStatComponent, TranslateModule],
  template: `
    <app-bento-grid gap="gap-4">
      <app-bento-card
        title="Test Card"
        subtitle="Test Subtitle"
        badge="Active"
        badgeTone="emerald"
        accentTone="cyan"
        colSpan="col-span-12 md:col-span-8"
        rowSpan="row-span-1"
        headerIcon="ri-shield-line"
      >
        <span headerExtra id="test-header-extra">Extra</span>
        <div id="test-body">Card Body</div>
        <div footer id="test-footer">Card Footer</div>
      </app-bento-card>

      <app-bento-stat
        label="Total Punch"
        [value]="1250"
        unit="times"
        accentTone="sky"
        icon="ri-fingerprint-line"
        trend="up"
        trendLabel="+12% today"
        routerLink="/company/timestamp-log"
      >
      </app-bento-stat>
    </app-bento-grid>
  `,
})
class BentoHostComponent {}

describe('Bento Components', () => {
  let fixture: ComponentFixture<BentoHostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TranslateModule.forRoot(), BentoHostComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(BentoHostComponent);
    fixture.detectChanges();
  });

  it('renders bento-grid container with 12-column layout and gap', () => {
    const gridEl = fixture.nativeElement.querySelector('.sv-bento-grid');
    expect(gridEl).toBeTruthy();
    expect(gridEl.classList.contains('gap-4')).toBeTrue();
  });

  it('renders bento-card with accent tone, title, subtitle, badge, and content slots', () => {
    const cardEl = fixture.nativeElement.querySelector('.sv-bento-card');
    expect(cardEl).toBeTruthy();
    expect(cardEl.classList.contains('accent-cyan')).toBeTrue();
    expect(cardEl.classList.contains('col-span-12')).toBeTrue();
    expect(cardEl.classList.contains('md:col-span-8')).toBeTrue();

    const titleEl = cardEl.querySelector('.sv-bento-card__title-text');
    expect(titleEl?.textContent?.trim()).toBe('Test Card');

    const subtitleEl = cardEl.querySelector('.sv-bento-card__subtitle');
    expect(subtitleEl?.textContent?.trim()).toBe('Test Subtitle');

    const badgeEl = cardEl.querySelector('.sv-bento-card__badge');
    expect(badgeEl?.textContent?.trim()).toBe('Active');

    const extraEl = cardEl.querySelector('#test-header-extra');
    expect(extraEl).toBeTruthy();

    const bodyEl = cardEl.querySelector('#test-body');
    expect(bodyEl?.textContent?.trim()).toBe('Card Body');

    const footerEl = cardEl.querySelector('#test-footer');
    expect(footerEl?.textContent?.trim()).toBe('Card Footer');
  });

  it('renders bento-stat tile with label, value, unit, icon, and trend', () => {
    const statEl = fixture.nativeElement.querySelector('.sv-bento-stat');
    expect(statEl).toBeTruthy();
    expect(statEl.classList.contains('accent-sky')).toBeTrue();

    const labelEl = statEl.querySelector('.sv-bento-stat__label');
    expect(labelEl?.textContent?.trim()).toBe('Total Punch');

    const valueEl = statEl.querySelector('.sv-bento-stat__value');
    expect(valueEl?.textContent?.trim()).toContain('1250');

    const unitEl = statEl.querySelector('.sv-bento-stat__unit');
    expect(unitEl?.textContent?.trim()).toBe('times');

    const trendEl = statEl.querySelector('.sv-bento-stat__trend');
    expect(trendEl?.textContent?.trim()).toContain('+12% today');
    expect(trendEl?.classList?.contains('is-up')).toBeTrue();

    const iconEl = statEl.querySelector('.sv-bento-stat__icon i');
    expect(iconEl?.classList?.contains('ri-fingerprint-line')).toBeTrue();
  });
});
