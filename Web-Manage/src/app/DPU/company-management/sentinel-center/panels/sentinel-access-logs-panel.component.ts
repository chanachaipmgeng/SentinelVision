import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TokenService } from '../../../../shared/services/token.service';
import { accessZoneScanRoute } from '../sentinel.helpers';
import { SentinelApiService } from '../sentinel-api.service';

/**
 * Access Control logs (`/company/access-control/logs`).
 * Filters by zone + status; empty state points to create zone or open scan.
 */
@Component({
  selector: 'app-sentinel-access-logs-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './sentinel-access-logs-panel.component.html',
})
export class SentinelAccessLogsPanelComponent implements OnInit {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  zones: any[] = [];
  incidents: any[] = [];
  loading = false;
  incidentFilterZoneId = '';
  incidentFilterStatus = '';
  incidentFilterSeverity = '';

  constructor(
    private api: SentinelApiService,
    private token: TokenService,
    private router: Router,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadZones();
    this.loadIncidents();
  }

  loadZones(): void {
    this.api.getZones(this.companyId).subscribe((rows) => (this.zones = rows || []));
  }

  loadIncidents(): void {
    this.loading = true;
    this.api
      .getIncidents(
        this.companyId,
        this.incidentFilterSeverity || undefined,
        this.incidentFilterStatus || undefined,
        this.incidentFilterZoneId || undefined,
      )
      .subscribe({
        next: (rows) => {
          this.incidents = rows || [];
          this.loading = false;
        },
        error: () => {
          this.incidents = [];
          this.loading = false;
        },
      });
  }

  openScanForFilter(): void {
    const route = accessZoneScanRoute(this.incidentFilterZoneId || null);
    this.router.navigateByUrl(route);
  }

  goCreateZone(): void {
    this.router.navigateByUrl('/company/access-control/zones');
  }

  acknowledgeIncident(incidentId: string): void {
    this.api.acknowledgeIncident(this.companyId, incidentId).subscribe({
      next: () => {
        this.toast.emit('รับทราบเหตุการณ์แล้ว');
        this.loadIncidents();
        this.overviewChanged.emit();
      },
    });
  }

  assignIncident(incidentId: string): void {
    this.api.assignIncident(this.companyId, incidentId).subscribe({
      next: () => {
        this.toast.emit('มอบหมายเหตุการณ์แล้ว');
        this.loadIncidents();
        this.overviewChanged.emit();
      },
    });
  }

  closeIncident(incidentId: string): void {
    this.api.closeIncident(this.companyId, incidentId).subscribe({
      next: () => {
        this.toast.emit('ปิดเหตุการณ์แล้ว');
        this.loadIncidents();
        this.overviewChanged.emit();
      },
    });
  }

  canActOnIncident(inc: any): boolean {
    const st = (inc?.status || 'OPEN').toUpperCase();
    return st !== 'CLOSED';
  }
}
