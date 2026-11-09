import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { AuthedImageService } from '../../../../shared/services/authed-image.service';
import { SavedViewsBarComponent } from '../../../../shared/components/saved-views-bar/saved-views-bar.component';
import { SideDrawerComponent } from '../../../../shared/components/side-drawer/side-drawer.component';
import { accessZoneScanRoute } from '../sentinel.helpers';
import { SentinelApiService } from '../sentinel-api.service';

interface AccessLogsViewFilters {
  zoneId: string;
  status: string;
  severity: string;
}

/**
 * Access Control logs (`/company/access-control/logs`).
 * Filters by zone + status; empty state points to create zone or open scan.
 */
@Component({
  selector: 'app-sentinel-access-logs-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TranslateModule, SavedViewsBarComponent, SideDrawerComponent],
  templateUrl: './sentinel-access-logs-panel.component.html',
  styleUrls: [
    './sentinel-access-logs-panel.component.css',
    '../../../../shared/styles/dpu-filter-toolbar.css',
  ],
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
  savedFilters: AccessLogsViewFilters = { zoneId: '', status: '', severity: '' };
  selectedIncident: any = null;
  drawerOpen = false;

  constructor(
    private api: SentinelApiService,
    private token: TokenService,
    private router: Router,
    private authedImages: AuthedImageService,
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
    this.savedFilters = {
      zoneId: this.incidentFilterZoneId || '',
      status: this.incidentFilterStatus || '',
      severity: this.incidentFilterSeverity || '',
    };
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
          this.resyncSelected();
        },
        error: () => {
          this.incidents = [];
          this.loading = false;
          this.resyncSelected();
        },
      });
  }

  applySavedView(filters: Partial<AccessLogsViewFilters> | null): void {
    if (!filters) return;
    this.incidentFilterZoneId = filters.zoneId || '';
    this.incidentFilterStatus = filters.status || '';
    this.incidentFilterSeverity = filters.severity || '';
    if (this.companyId) this.loadIncidents();
  }

  openIncident(inc: any): void {
    this.selectedIncident = inc;
    this.drawerOpen = true;
  }

  isSelectedIncident(inc: any): boolean {
    return this.drawerOpen && this.selectedIncident?.incidentId === inc?.incidentId;
  }

  /** Incident evidence is served from `/images/*`; fetch via Bearer → blob URL. */
  snapshotSrc(inc: any): string {
    const raw: string = inc?.snapshotUrl || '';
    if (!raw) return '';
    if (/^(https?:|data:|blob:)/i.test(raw)) return raw;
    return this.authedImages.urlFor(raw.replace(/^\/?images\//, '').replace(/^\//, ''));
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

  canAcknowledge(inc: any): boolean {
    return !inc?.acknowledgedAt && (inc?.severity === 'CRITICAL' || inc?.severity === 'WARNING');
  }

  private resyncSelected(): void {
    const id = this.selectedIncident?.incidentId;
    if (!id) return;
    // If the incident was filtered out (e.g. closed while filtering OPEN), keep the last copy shown.
    const fresh = this.incidents.find((x) => x.incidentId === id);
    if (fresh) this.selectedIncident = fresh;
  }
}
