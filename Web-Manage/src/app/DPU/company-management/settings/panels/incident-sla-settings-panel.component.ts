import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../../sentinel-center/sentinel-api.service';

type SlaStatus = 'idle' | 'saved' | 'error';

/** Company SLA minutes for high-severity OPEN incidents — settings hub panel. */
@Component({
    selector: 'app-incident-sla-settings-panel',
    imports: [CommonModule, FormsModule, TranslateModule],
    template: `
    <div class="box modern-card glass">
      <div class="box-body space-y-4">
        <div>
          <h6 class="font-bold text-base mb-1">{{ 'settingsHub.incidentSla.title' | translate }}</h6>
          <p class="text-xs text-dpu-muted mb-0">{{ 'settingsHub.incidentSla.hint' | translate }}</p>
        </div>

        <div *ngIf="loading" class="text-xs text-dpu-muted">{{ 'settingsHub.loading' | translate }}</div>

        <label class="block" *ngIf="!loading">
          <span class="text-xs font-semibold text-slate-700">
            {{ 'settingsHub.incidentSla.minutesHigh' | translate }}
          </span>
          <input
            type="number"
            class="form-control mt-1 !max-w-[12rem]"
            min="0"
            max="10080"
            [(ngModel)]="minutesHigh"
            [disabled]="busy"
          />
          <span class="block text-[0.7rem] text-dpu-muted mt-1">
            {{ 'settingsHub.incidentSla.minutesHighHelp' | translate }}
          </span>
        </label>

        <div class="flex flex-wrap items-center gap-2" *ngIf="!loading">
          <button
            type="button"
            class="ti-btn ti-btn-primary-full font-semibold text-xs"
            [disabled]="busy"
            (click)="save()"
          >
            {{ 'settingsHub.incidentSla.save' | translate }}
          </button>
          <button
            type="button"
            class="ti-btn ti-btn-light font-semibold text-xs"
            [disabled]="busy"
            (click)="resetDefaults()"
          >
            รีเซ็ตค่าเริ่มต้น
          </button>
          <span class="text-xs font-semibold text-emerald-700" *ngIf="status === 'saved'">
            {{ 'settingsHub.incidentSla.saved' | translate }}
          </span>
          <span class="text-xs font-semibold text-rose-700" *ngIf="status === 'error'">
            {{ 'settingsHub.incidentSla.error' | translate }}
          </span>
        </div>
      </div>
    </div>
  `
})
export class IncidentSlaSettingsPanelComponent implements OnInit {
  @Input() companyId = '';
  @Output() statusFlash = new EventEmitter<string>();

  minutesHigh = 15;
  loading = false;
  busy = false;
  status: SlaStatus = 'idle';

  constructor(private api: SentinelApiService, private token: TokenService) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.loading = true;
    this.api.getIncidentSlaSettings(this.companyId).subscribe({
      next: (s) => {
        this.minutesHigh = Number(s?.incidentSlaMinutesHigh ?? 15);
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  resetDefaults(): void {
    this.minutesHigh = 15;
    this.status = 'idle';
    this.statusFlash.emit('คืนค่าเริ่มต้นแล้ว (กดบันทึกเพื่อยืนยัน)');
  }

  save(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    const minutes = Math.max(0, Math.floor(Number(this.minutesHigh) || 0));
    this.api.putIncidentSlaSettings(this.companyId, { incidentSlaMinutesHigh: minutes }).subscribe({
      next: (s) => {
        this.minutesHigh = Number(s?.incidentSlaMinutesHigh ?? minutes);
        this.busy = false;
        this.status = 'saved';
        this.statusFlash.emit('บันทึก SLA แล้ว');
      },
      error: () => {
        this.busy = false;
        this.status = 'error';
      },
    });
  }
}
