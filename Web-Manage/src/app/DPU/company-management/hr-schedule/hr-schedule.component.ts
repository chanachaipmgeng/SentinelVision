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
    imports: [CommonModule, RouterModule, SharedModule],
    template: `
    <app-page-header
      [title]="'นโยบายกะเวลา & ระบบองค์กร (HR Schedule)'"
      [activeTitle]="'จัดการข้อมูลการลงเวลา'"
      [title1]="'กะเวลา & นโยบาย'"
    ></app-page-header>

    <div class="grid grid-cols-12 gap-6">
      <div class="col-span-12">
        <div class="box modern-card glass card-surface-cyan">
          <div class="box-header flex flex-wrap items-center justify-between gap-3 p-4 border-b border-white/10">
            <div class="flex flex-wrap gap-2">
              <a
                *ngFor="let tab of tabs"
                [routerLink]="['/company/hr-schedule', tab.id]"
                routerLinkActive="!bg-gradient-to-r !from-cyan-500 !to-teal-500 !text-white !border-transparent !shadow-md !shadow-cyan-500/25"
                [routerLinkActiveOptions]="{ exact: true }"
                #rla="routerLinkActive"
                class="ti-btn !rounded-full !px-4 !py-2 !text-xs !font-semibold transition-all duration-200"
                [ngClass]="rla.isActive ? '' : '!bg-white/5 hover:!bg-white/10 !text-slate-300 !border !border-white/10'"
              >
                <i [class]="tab.icon + ' me-1.5'"></i> {{ tab.label }}
              </a>
            </div>
            <span *ngIf="statusMsg" class="badge bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-semibold">
              {{ statusMsg }}
            </span>
          </div>

          <div class="box-body p-5 space-y-6">
            <router-outlet (activate)="onActivate($event)"></router-outlet>
          </div>
        </div>
      </div>
    </div>
  `
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
