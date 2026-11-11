import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { StatChipComponent } from '../../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../../shared/services/token.service';
import { LocaleDatePipe } from '../../../../shared/pipes/locale-date.pipe';
import type { KioskDeviceRow } from '../../devices/devices.component';

/** Kiosk device counts + recent rows; pairing/rotate/revoke stay on `/company/devices`. */
@Component({
    selector: 'app-devices-summary-panel',
    imports: [CommonModule, TranslateModule, EmptyStateComponent, StatChipComponent, LocaleDatePipe],
    template: `
    <div class="box modern-card glass">
      <div class="box-header flex flex-wrap items-center gap-2">
        <h5 class="box-title !mb-0">{{ 'settingsHub.devices.title' | translate }}</h5>
        <app-stat-chip>{{ 'All' | translate }} {{ items.length }}</app-stat-chip>
        <app-stat-chip tone="ok">{{ 'Enabled' | translate }} {{ activeCount }}</app-stat-chip>
        <app-stat-chip tone="soft">{{ 'Paired' | translate }} {{ pairedCount }}</app-stat-chip>
      </div>
      <div class="box-body">
        <app-empty-state *ngIf="loading" [loading]="true" message="settingsHub.loading"></app-empty-state>
        <app-empty-state
          *ngIf="!loading && !items.length"
          [message]="error ? 'settingsHub.devices.loadError' : 'settingsHub.devices.empty'"
        ></app-empty-state>
        <ul *ngIf="!loading && items.length" class="dpu-settings-list">
          <li *ngFor="let d of recent" class="dpu-settings-list__row">
            <span class="dpu-settings-list__icon"><i class="ri-tablet-line"></i></span>
            <span class="dpu-settings-list__text">
              <strong>{{ d.name }}</strong>
              <em>{{ d.stationMode || '—' }} · {{ d.lastSeenAt ? (d.lastSeenAt | localeDate: 'datetime') : ('settingsHub.devices.neverSeen' | translate) }}</em>
            </span>
            <app-stat-chip [tone]="d.revokedAt ? 'danger' : d.isPaired ? 'ok' : 'warn'">
              {{ d.revokedAt ? 'REVOKED' : d.isPaired ? 'PAIRED' : 'PENDING' }}
            </app-stat-chip>
          </li>
        </ul>
      </div>
    </div>
  `
})
export class DevicesSummaryPanelComponent implements OnInit {
  loading = true;
  error = false;
  items: KioskDeviceRow[] = [];

  constructor(private http: HttpClient, private token: TokenService) {}

  get activeCount(): number {
    return this.items.filter((d) => d.isActive !== false && !d.revokedAt).length;
  }

  get pairedCount(): number {
    return this.items.filter((d) => d.isPaired).length;
  }

  get recent(): KioskDeviceRow[] {
    return this.items.slice(0, 5);
  }

  ngOnInit(): void {
    const companyId = this.token.getSelectCompany()?.companyId || '';
    if (!companyId) {
      this.loading = false;
      return;
    }
    this.http.get<KioskDeviceRow[]>(`/devices/company/${companyId}/devices`).subscribe({
      next: (rows) => {
        this.items = rows || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = true;
      },
    });
  }
}
