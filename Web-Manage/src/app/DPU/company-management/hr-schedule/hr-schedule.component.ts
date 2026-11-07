import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { HR_SCHEDULE_TABS, HrScheduleTab } from './hr-schedule.helpers';

/**
 * HR Schedule shell — tab nav + router-outlet.
 * Each tab loads its own data (no eager reloadAll).
 */
@Component({
  selector: 'app-hr-schedule',
  standalone: true,
  imports: [CommonModule, RouterModule, SharedModule],
  template: `
    <app-page-header
      [title]="'กะทำงาน / วันลา / วันหยุด / PDPA / Kiosk 2FA / Webhook & Observability'"
      [activeTitle]="'จัดการข้อมูลการลงเวลา'"
      [title1]="'กะงาน / วันลา / PDPA / Cloud'"
    ></app-page-header>

    <div class="grid grid-cols-12 gap-6">
      <div class="col-span-12">
        <div class="box">
          <div class="box-header flex flex-wrap items-center justify-between gap-2">
            <div class="flex flex-wrap gap-2">
              <a
                *ngFor="let tab of tabs"
                [routerLink]="['/company/hr-schedule', tab.id]"
                routerLinkActive="ti-btn-primary-full"
                [routerLinkActiveOptions]="{ exact: true }"
                #rla="routerLinkActive"
                class="ti-btn"
                [class.ti-btn-light]="!rla.isActive"
              >
                <i [class]="tab.icon + ' me-1'"></i> {{ tab.label }}
              </a>
            </div>
            <span *ngIf="statusMsg" class="badge bg-success/10 text-success px-3 py-1">
              {{ statusMsg }}
            </span>
          </div>

          <div class="box-body space-y-6">
            <router-outlet (activate)="onActivate($event)"></router-outlet>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class HrScheduleComponent {
  readonly tabs = HR_SCHEDULE_TABS;
  statusMsg = '';
  private statusTimer: ReturnType<typeof setTimeout> | null = null;

  onActivate(component: { status?: { subscribe: (fn: (m: string) => void) => void } }): void {
    if (component?.status?.subscribe) {
      component.status.subscribe((msg: string) => this.flash(msg));
    }
  }

  private flash(msg: string): void {
    this.statusMsg = msg;
    if (this.statusTimer) clearTimeout(this.statusTimer);
    this.statusTimer = setTimeout(() => {
      if (this.statusMsg === msg) this.statusMsg = '';
    }, 3500);
  }
}

export type { HrScheduleTab };
