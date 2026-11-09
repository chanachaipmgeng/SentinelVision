import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { AuthedImageService } from '../../../../shared/services/authed-image.service';
import { SavedViewsBarComponent } from '../../../../shared/components/saved-views-bar/saved-views-bar.component';
import { SideDrawerComponent } from '../../../../shared/components/side-drawer/side-drawer.component';
import {
  isIncidentSoundEnabled,
  playIncidentEventSound,
  setIncidentSoundEnabled,
  unlockBeepAudio,
} from '../../../../shared/utils/beep';
import { accessZoneScanRoute } from '../sentinel.helpers';
import { SentinelApiService } from '../sentinel-api.service';

interface AccessLogsViewFilters {
  zoneId: string;
  status: string;
  severity: string;
}

const POLL_MS = 15000;

/**
 * Access Control logs (`/company/access-control/logs`).
 * Filters by zone + status; empty state points to create zone or open scan.
 * Phase 4/6B: multi-select bulk ack/close, SLA overdue badge, incident sound toast.
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
export class SentinelAccessLogsPanelComponent implements OnInit, OnDestroy {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  zones: any[] = [];
  incidents: any[] = [];
  loading = false;
  bulkBusy = false;
  incidentFilterZoneId = '';
  incidentFilterStatus = '';
  incidentFilterSeverity = '';
  savedFilters: AccessLogsViewFilters = { zoneId: '', status: '', severity: '' };
  selectedIncident: any = null;
  drawerOpen = false;
  /** Multi-select for bulk ops (incidentId → true). */
  selectedIds = new Set<string>();
  soundEnabled = true;

  private knownIds = new Set<string>();
  private pollReady = false;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private api: SentinelApiService,
    private token: TokenService,
    private router: Router,
    private authedImages: AuthedImageService,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    this.soundEnabled = isIncidentSoundEnabled();
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadZones();
    this.loadIncidents();
    this.pollTimer = setInterval(() => this.loadIncidents(true), POLL_MS);
  }

  ngOnDestroy(): void {
    if (this.pollTimer) clearInterval(this.pollTimer);
  }

  get selectedCount(): number {
    return this.selectedIds.size;
  }

  get allVisibleSelected(): boolean {
    return this.incidents.length > 0 && this.incidents.every((i) => this.selectedIds.has(i.incidentId));
  }

  loadZones(): void {
    this.api.getZones(this.companyId).subscribe((rows) => (this.zones = rows || []));
  }

  loadIncidents(fromPoll = false): void {
    if (!fromPoll) this.loading = true;
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
          const list = rows || [];
          this.detectNewIncidents(list);
          this.incidents = list;
          this.loading = false;
          this.pruneSelection();
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

  toggleRowSelect(inc: any, event: Event): void {
    event.stopPropagation();
    const id = inc?.incidentId;
    if (!id) return;
    if (this.selectedIds.has(id)) this.selectedIds.delete(id);
    else this.selectedIds.add(id);
    this.selectedIds = new Set(this.selectedIds);
  }

  isRowChecked(inc: any): boolean {
    return this.selectedIds.has(inc?.incidentId);
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement)?.checked;
    if (checked) {
      this.selectedIds = new Set(this.incidents.map((i) => i.incidentId).filter(Boolean));
    } else {
      this.selectedIds = new Set();
    }
  }

  clearSelection(): void {
    this.selectedIds = new Set();
  }

  bulkAcknowledge(): void {
    const ids = [...this.selectedIds];
    if (!ids.length || this.bulkBusy) return;
    this.bulkBusy = true;
    this.api.bulkAcknowledgeIncidents(this.companyId, ids).subscribe({
      next: (res) => {
        this.bulkBusy = false;
        const n = res?.acknowledgedCount ?? 0;
        this.toast.emit(`รับทราบแล้ว ${n} เหตุการณ์`);
        this.clearSelection();
        this.loadIncidents();
        this.overviewChanged.emit();
      },
      error: () => {
        this.bulkBusy = false;
        this.toast.emit('รับทราบหลายรายการไม่สำเร็จ');
      },
    });
  }

  bulkClose(): void {
    const ids = [...this.selectedIds];
    if (!ids.length || this.bulkBusy) return;
    this.bulkBusy = true;
    this.api.bulkCloseIncidents(this.companyId, ids).subscribe({
      next: (res) => {
        this.bulkBusy = false;
        const n = res?.closedCount ?? 0;
        this.toast.emit(`ปิดแล้ว ${n} เหตุการณ์`);
        this.clearSelection();
        this.loadIncidents();
        this.overviewChanged.emit();
      },
      error: () => {
        this.bulkBusy = false;
        this.toast.emit('ปิดหลายรายการไม่สำเร็จ');
      },
    });
  }

  toggleSound(): void {
    unlockBeepAudio();
    this.soundEnabled = !this.soundEnabled;
    setIncidentSoundEnabled(this.soundEnabled);
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

  isOverdue(inc: any): boolean {
    if (!inc?.slaDueAt) return false;
    const st = (inc?.status || 'OPEN').toUpperCase();
    if (st === 'CLOSED') return false;
    const due = new Date(inc.slaDueAt).getTime();
    return Number.isFinite(due) && due < Date.now();
  }

  private detectNewIncidents(list: any[]): void {
    const nextIds = new Set<string>(list.map((i) => i?.incidentId).filter(Boolean));
    if (!this.pollReady) {
      this.knownIds = nextIds;
      this.pollReady = true;
      return;
    }
    const newcomers = list.filter(
      (i) => i?.incidentId && !this.knownIds.has(i.incidentId),
    );
    this.knownIds = nextIds;
    if (!newcomers.length) return;
    const newest = newcomers[0];
    const label = newest.subjectName || newest.eventType || 'incident';
    this.toast.emit(`เหตุการณ์ใหม่: ${label}`);
    playIncidentEventSound(newest.eventType);
    this.overviewChanged.emit();
  }

  private pruneSelection(): void {
    if (!this.selectedIds.size) return;
    const visible = new Set(this.incidents.map((i) => i.incidentId));
    const next = new Set<string>();
    for (const id of this.selectedIds) {
      if (visible.has(id)) next.add(id);
    }
    this.selectedIds = next;
  }

  private resyncSelected(): void {
    const id = this.selectedIncident?.incidentId;
    if (!id) return;
    // If the incident was filtered out (e.g. closed while filtering OPEN), keep the last copy shown.
    const fresh = this.incidents.find((x) => x.incidentId === id);
    if (fresh) this.selectedIncident = fresh;
  }
}
