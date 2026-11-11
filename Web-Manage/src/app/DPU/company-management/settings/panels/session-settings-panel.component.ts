import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { IdleTimeoutService } from '../../../../shared/services/idle-timeout.service';
import {
  CompanySettingsApiService,
  SessionSettings,
} from '../company-settings-api.service';

type PanelStatus = 'idle' | 'saved' | 'error';

/** Admin SPA idle logout minutes — settings hub panel. */
@Component({
    selector: 'app-session-settings-panel',
    imports: [CommonModule, FormsModule, TranslateModule],
    template: `
    <div class="box modern-card glass">
      <div class="box-body space-y-4">
        <div>
          <h6 class="font-bold text-base mb-1">{{ 'settingsHub.session.title' | translate }}</h6>
          <p class="text-xs text-dpu-muted mb-0">{{ 'settingsHub.session.hint' | translate }}</p>
        </div>

        <div *ngIf="loading" class="text-xs text-dpu-muted">{{ 'settingsHub.loading' | translate }}</div>

        <label class="block" *ngIf="!loading">
          <span class="text-xs font-semibold text-slate-700">
            {{ 'settingsHub.session.idleMinutes' | translate }}
          </span>
          <input
            type="number"
            class="form-control mt-1 !max-w-[12rem]"
            min="0"
            max="480"
            [(ngModel)]="idleMinutes"
            [disabled]="busy"
          />
          <span class="block text-[0.7rem] text-dpu-muted mt-1">
            {{ 'settingsHub.session.idleMinutesHelp' | translate }}
          </span>
        </label>

        <div class="flex flex-wrap items-center gap-2" *ngIf="!loading">
          <button
            type="button"
            class="ti-btn ti-btn-primary-full font-semibold text-xs"
            [disabled]="busy"
            (click)="save()"
          >
            {{ 'settingsHub.session.save' | translate }}
          </button>
          <span class="text-xs font-semibold text-emerald-700" *ngIf="status === 'saved'">
            {{ 'settingsHub.session.saved' | translate }}
          </span>
          <span class="text-xs font-semibold text-rose-700" *ngIf="status === 'error'">
            {{ 'settingsHub.session.error' | translate }}
          </span>
        </div>
      </div>
    </div>
  `
})
export class SessionSettingsPanelComponent implements OnInit {
  @Input() companyId = '';
  @Output() statusFlash = new EventEmitter<string>();

  idleMinutes = 0;
  loading = false;
  busy = false;
  status: PanelStatus = 'idle';

  constructor(
    private api: CompanySettingsApiService,
    private token: TokenService,
    private idle: IdleTimeoutService,
  ) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.loading = true;
    this.api.getSessionSettings(this.companyId).subscribe({
      next: (s) => {
        this.idleMinutes = Number(s?.idleTimeoutMinutes ?? 0);
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  save(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    const minutes = Math.max(0, Math.min(480, Math.floor(Number(this.idleMinutes) || 0)));
    this.api.putSessionSettings(this.companyId, { idleTimeoutMinutes: minutes }).subscribe({
      next: (s: SessionSettings) => {
        this.idleMinutes = Number(s?.idleTimeoutMinutes ?? minutes);
        this.busy = false;
        this.status = 'saved';
        this.idle.applyMinutes(this.idleMinutes);
        this.statusFlash.emit('บันทึก session แล้ว');
      },
      error: () => {
        this.busy = false;
        this.status = 'error';
      },
    });
  }
}
