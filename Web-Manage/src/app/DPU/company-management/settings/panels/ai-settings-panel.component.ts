import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import {
  AiSettings,
  CompanySettingsApiService,
} from '../company-settings-api.service';

type PanelStatus = 'idle' | 'saved' | 'error';

/** Company face-match threshold + CCTV analysis interval — settings hub panel. */
@Component({
    selector: 'app-ai-settings-panel',
    imports: [CommonModule, FormsModule, TranslateModule],
    template: `
    <div class="box modern-card glass">
      <div class="box-body space-y-4">
        <div>
          <h6 class="font-bold text-base mb-1">{{ 'settingsHub.ai.title' | translate }}</h6>
          <p class="text-xs text-dpu-muted mb-0">{{ 'settingsHub.ai.hint' | translate }}</p>
        </div>

        <div *ngIf="loading" class="text-xs text-dpu-muted">{{ 'settingsHub.loading' | translate }}</div>

        <ng-container *ngIf="!loading">
          <label class="flex items-start gap-2">
            <input type="checkbox" class="mt-1" [(ngModel)]="faceOverride" [disabled]="busy" />
            <span>
              <span class="block text-xs font-semibold text-slate-700">
                {{ 'settingsHub.ai.faceOverride' | translate }}
              </span>
              <span class="block text-[0.7rem] text-dpu-muted">
                {{ 'settingsHub.ai.faceOverrideHelp' | translate }}
              </span>
            </span>
          </label>

          <label class="block" *ngIf="faceOverride">
            <span class="text-xs font-semibold text-slate-700">
              {{ 'settingsHub.ai.faceThreshold' | translate }}
            </span>
            <input
              type="number"
              class="form-control mt-1 !max-w-[12rem]"
              min="0.15"
              max="0.70"
              step="0.01"
              [(ngModel)]="faceThreshold"
              [disabled]="busy"
            />
            <span class="block text-[0.7rem] text-dpu-muted mt-1">
              {{ 'settingsHub.ai.faceThresholdHelp' | translate }}
            </span>
          </label>

          <label class="flex items-start gap-2">
            <input type="checkbox" class="mt-1" [(ngModel)]="cctvOverride" [disabled]="busy" />
            <span>
              <span class="block text-xs font-semibold text-slate-700">
                {{ 'settingsHub.ai.cctvOverride' | translate }}
              </span>
              <span class="block text-[0.7rem] text-dpu-muted">
                {{ 'settingsHub.ai.cctvOverrideHelp' | translate }}
              </span>
            </span>
          </label>

          <label class="block" *ngIf="cctvOverride">
            <span class="text-xs font-semibold text-slate-700">
              {{ 'settingsHub.ai.cctvInterval' | translate }}
            </span>
            <input
              type="number"
              class="form-control mt-1 !max-w-[12rem]"
              min="10"
              max="600"
              step="1"
              [(ngModel)]="cctvInterval"
              [disabled]="busy"
            />
            <span class="block text-[0.7rem] text-dpu-muted mt-1">
              {{ 'settingsHub.ai.cctvIntervalHelp' | translate }}
            </span>
          </label>

          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="ti-btn ti-btn-primary-full font-semibold text-xs"
              [disabled]="busy"
              (click)="save()"
            >
              {{ 'settingsHub.ai.save' | translate }}
            </button>
            <span class="text-xs font-semibold text-emerald-700" *ngIf="status === 'saved'">
              {{ 'settingsHub.ai.saved' | translate }}
            </span>
            <span class="text-xs font-semibold text-rose-700" *ngIf="status === 'error'">
              {{ 'settingsHub.ai.error' | translate }}
            </span>
          </div>
        </ng-container>
      </div>
    </div>
  `
})
export class AiSettingsPanelComponent implements OnInit {
  @Input() companyId = '';
  @Output() statusFlash = new EventEmitter<string>();

  faceOverride = false;
  faceThreshold = 0.4;
  cctvOverride = false;
  cctvInterval = 30;
  loading = false;
  busy = false;
  status: PanelStatus = 'idle';

  constructor(private api: CompanySettingsApiService, private token: TokenService) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.loading = true;
    this.api.getAiSettings(this.companyId).subscribe({
      next: (s) => {
        this.apply(s);
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  private apply(s: AiSettings): void {
    this.faceOverride = !!s?.faceMatchThresholdOverride;
    this.faceThreshold = Number(s?.faceMatchThreshold ?? 0.4);
    this.cctvOverride = !!s?.cctvCameraIntervalOverride;
    this.cctvInterval = Number(s?.cctvCameraIntervalSeconds ?? 30);
  }

  save(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    const body: Partial<AiSettings> = {
      faceMatchThresholdOverride: this.faceOverride,
      cctvCameraIntervalOverride: this.cctvOverride,
    };
    if (this.faceOverride) {
      body.faceMatchThreshold = Math.max(0.15, Math.min(0.7, Number(this.faceThreshold) || 0.4));
    }
    if (this.cctvOverride) {
      body.cctvCameraIntervalSeconds = Math.max(
        10,
        Math.min(600, Math.floor(Number(this.cctvInterval) || 30)),
      );
    }
    this.api.putAiSettings(this.companyId, body).subscribe({
      next: (s) => {
        this.apply(s);
        this.busy = false;
        this.status = 'saved';
        this.statusFlash.emit('บันทึก AI แล้ว');
      },
      error: () => {
        this.busy = false;
        this.status = 'error';
      },
    });
  }
}
