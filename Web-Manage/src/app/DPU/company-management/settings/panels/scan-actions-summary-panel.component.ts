import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { StatChipComponent } from '../../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../../shared/services/token.service';
import {
  CompanyModuleConfig,
  CompanyModuleConfigService,
  ScanActionRules,
} from '../../../services/company-module-config.service';
import { HubModuleCard, buildHubModuleCards } from '../../scan-hub/scan-hub.helpers';

interface RuleRow {
  labelKey: string;
  on: boolean;
}

/** Read-only summary of module toggles + scan action rules; editing stays in Scan & Action Hub. */
@Component({
    selector: 'app-scan-actions-summary-panel',
    imports: [CommonModule, RouterModule, TranslateModule, EmptyStateComponent, StatChipComponent],
    template: `
    <app-empty-state *ngIf="loading" [loading]="true" message="settingsHub.loading"></app-empty-state>
    <div *ngIf="!loading" class="grid grid-cols-12 gap-4">
      <div class="col-span-12 xl:col-span-7">
        <div class="box modern-card glass h-full">
          <div class="box-header">
            <h5 class="box-title !mb-0">{{ 'Active modules' | translate }}</h5>
          </div>
          <div class="box-body">
            <p *ngIf="error" class="text-sm text-danger mb-2">{{ 'settingsHub.scan.loadError' | translate }}</p>
            <ul class="dpu-settings-list">
              <li *ngFor="let card of modules" class="dpu-settings-list__row">
                <span class="dpu-settings-list__icon"><i [ngClass]="card.icon"></i></span>
                <span class="dpu-settings-list__text">
                  <strong>{{ card.label | translate }}</strong>
                  <em>{{ card.hint | translate }}</em>
                </span>
                <app-stat-chip [tone]="card.enabled ? 'ok' : 'soft'">
                  {{ (card.enabled ? 'settingsHub.on' : 'settingsHub.off') | translate }}
                </app-stat-chip>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-5">
        <div class="box modern-card glass h-full">
          <div class="box-header">
            <h5 class="box-title !mb-0">{{ 'On face match actions' | translate }}</h5>
          </div>
          <div class="box-body">
            <ul class="dpu-settings-list">
              <li *ngFor="let rule of rules" class="dpu-settings-list__row">
                <span class="dpu-settings-list__text"><strong>{{ rule.labelKey | translate }}</strong></span>
                <app-stat-chip [tone]="rule.on ? 'ok' : 'soft'">
                  {{ (rule.on ? 'settingsHub.on' : 'settingsHub.off') | translate }}
                </app-stat-chip>
              </li>
              <li class="dpu-settings-list__row">
                <span class="dpu-settings-list__text"><strong>{{ 'Unknown face action' | translate }}</strong></span>
                <app-stat-chip tone="soft">{{ unknownFaceAction }}</app-stat-chip>
              </li>
              <li class="dpu-settings-list__row" *ngIf="defaultStationMode">
                <span class="dpu-settings-list__text"><strong>{{ 'Default station mode' | translate }}</strong></span>
                <app-stat-chip tone="soft">{{ defaultStationMode }}</app-stat-chip>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ScanActionsSummaryPanelComponent implements OnInit {
  loading = true;
  error = false;
  modules: HubModuleCard[] = [];
  rules: RuleRow[] = [];
  unknownFaceAction = '';
  defaultStationMode = '';

  constructor(private token: TokenService, private moduleConfig: CompanyModuleConfigService) {}

  ngOnInit(): void {
    const companyId = this.token.getSelectCompany()?.companyId || '';
    if (!companyId) {
      this.loading = false;
      this.error = true;
      return;
    }
    this.moduleConfig.getModuleConfig(companyId, true).subscribe({
      next: (cfg) => this.apply(cfg),
      error: () => {
        this.loading = false;
        this.error = true;
      },
    });
  }

  private apply(cfg: CompanyModuleConfig): void {
    this.modules = buildHubModuleCards(cfg);
    const r: ScanActionRules = cfg.scanActionRules;
    this.rules = [
      { labelKey: 'Silent alert on Blacklist / POI', on: r.enableBlacklistSilentAlarm },
      { labelKey: 'VIP greeting', on: r.enableVipGreeting },
      { labelKey: 'TTS voice', on: r.enableTtsVoice },
      { labelKey: 'Unlock door on successful punch', on: r.enableDoorRelayOnAttendance },
    ];
    this.unknownFaceAction = r.unknownFaceAction;
    this.defaultStationMode = cfg.defaultStationMode || '';
    this.loading = false;
  }
}
