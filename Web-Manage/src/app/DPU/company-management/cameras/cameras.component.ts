import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import swal from 'sweetalert';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { SideDrawerComponent } from '../../../shared/components/side-drawer/side-drawer.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../shared/services/token.service';
import { VALID_STATION_MODES } from '../../services/company-module-config.service';

export interface CameraAiConfig {
  peopleEnabled?: boolean;
  line?: number[][];
  zone_polygon?: number[][];
  loiter_polygon?: number[][];
  roi_polygon?: number[][];
  crowd_min_count?: number;
  loiter_min_seconds?: number;
  confidence?: number;
  modes?: string[];
  hasRoi?: boolean;
}

export interface CameraRow {
  cameraId: string;
  companyId: string;
  name: string;
  streamUrl: string;
  protocol: string;
  description?: string | null;
  hasCredentials?: boolean;
  stationMode?: string | null;
  recordMode?: string;
  status?: string;
  lastPingAt?: string | null;
  lastPingLatencyMs?: number | null;
  lastAnalyzedAt?: string | null;
  isActive?: boolean;
  analysisEnabled?: boolean;
  aiConfig?: CameraAiConfig | null;
  whepPath?: string;
  hlsPath?: string;
  mtxPath?: string;
}

export interface PeopleMetrics {
  totals?: {
    inCount: number;
    outCount: number;
    net: number;
    peakZoneOccupancy: number;
    bucketCount: number;
  };
  byCamera?: {
    cameraId: string;
    inCount: number;
    outCount: number;
    peakZone: number;
    crossings: number;
  }[];
}

type RoiMode = 'line' | 'zone' | 'loiter' | 'roi';

@Component({
    selector: 'app-company-cameras',
    imports: [
        CommonModule,
        FormsModule,
        RouterLink,
        TranslateModule,
        PageToolbarComponent,
        PillSearchComponent,
        StatChipComponent,
        EmptyStateComponent,
        SideDrawerComponent,
    ],
    templateUrl: './cameras.component.html',
    styleUrls: ['../../../shared/styles/dpu-list-page.css', './cameras.component.css'],
    encapsulation: ViewEncapsulation.None
})
export class CamerasComponent implements OnInit {
  @ViewChild('roiCanvas') roiCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('roiImg') roiImg?: ElementRef<HTMLImageElement>;
  @ViewChild('csvInput') csvInput?: ElementRef<HTMLInputElement>;

  readonly stationModes = VALID_STATION_MODES;
  readonly protocols = ['rtsp', 'http', 'hls', 'rtmp'];
  readonly recordModes = ['event', 'continuous', 'off'];
  readonly roiModes: RoiMode[] = ['line', 'zone', 'loiter', 'roi'];

  companyId = '';
  loading = false;
  items: CameraRow[] = [];
  filtered: CameraRow[] = [];
  private _searchTerm = '';
  snapshotPreview: string | null = null;
  createOpen = false;
  detailOpen = false;
  selected: CameraRow | null = null;
  importing = false;
  peopleMetrics: PeopleMetrics | null = null;

  /** ROI editor state */
  roiCamera: CameraRow | null = null;
  roiMode: RoiMode = 'line';
  roiDraft: number[][] = [];
  roiSnapshot: string | null = null;
  roiSaving = false;
  roiCrowdMin = 5;
  roiLoiterSec = 30;
  roiPeopleEnabled = false;

  draft = {
    name: '',
    streamUrl: '',
    protocol: 'rtsp',
    description: '',
    streamUsername: '',
    streamPassword: '',
    stationMode: '',
    recordMode: 'event',
    analysisEnabled: false,
  };

  editDraft = {
    name: '',
    streamUrl: '',
    protocol: 'rtsp',
    description: '',
    streamUsername: '',
    streamPassword: '',
    stationMode: '',
    recordMode: 'event',
    analysisEnabled: false,
  };

  get searchTerm(): string {
    return this._searchTerm;
  }
  set searchTerm(val: string) {
    this._searchTerm = val;
    this.applyFilter();
  }

  get onlineCount(): number {
    return this.items.filter((c) => c.status === 'online').length;
  }

  get peopleEnabledCount(): number {
    return this.items.filter((c) => !!c.aiConfig?.peopleEnabled).length;
  }

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.load();
    this.loadPeopleMetrics();
  }

  private api(path = ''): string {
    return `/cameras/company/${this.companyId}/cameras${path}`;
  }

  private peopleApi(path = ''): string {
    return `/people/company/${this.companyId}${path}`;
  }

  load(): void {
    if (!this.companyId) return;
    this.loading = true;
    this.http.get<CameraRow[]>(this.api()).subscribe({
      next: (rows) => {
        this.items = rows || [];
        this.applyFilter();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        swal('Error', err?.error?.detail || 'Failed to load cameras', 'error');
      },
    });
  }

  loadPeopleMetrics(): void {
    if (!this.companyId) return;
    this.http.get<PeopleMetrics>(this.peopleApi('/metrics')).subscribe({
      next: (m) => (this.peopleMetrics = m),
      error: () => (this.peopleMetrics = null),
    });
  }

  applyFilter(): void {
    const q = (this._searchTerm || '').trim().toLowerCase();
    this.filtered = !q
      ? [...this.items]
      : this.items.filter((x) =>
          [x.name, x.streamUrl, x.protocol, x.status, x.stationMode, x.cameraId]
            .join(' ')
            .toLowerCase()
            .includes(q),
        );
  }

  clearSearch(): void {
    this.searchTerm = '';
  }

  openCreate(): void {
    this.detailOpen = false;
    this.resetDraft();
    this.createOpen = true;
  }

  openDetail(cam: CameraRow): void {
    this.createOpen = false;
    this.selected = cam;
    this.editDraft = {
      name: cam.name || '',
      streamUrl: cam.streamUrl || '',
      protocol: cam.protocol || 'rtsp',
      description: cam.description || '',
      streamUsername: '',
      streamPassword: '',
      stationMode: cam.stationMode || '',
      recordMode: cam.recordMode || 'event',
      analysisEnabled: !!cam.analysisEnabled,
    };
    this.detailOpen = true;
  }

  resetDraft(): void {
    this.draft = {
      name: '',
      streamUrl: '',
      protocol: 'rtsp',
      description: '',
      streamUsername: '',
      streamPassword: '',
      stationMode: '',
      recordMode: 'event',
      analysisEnabled: false,
    };
  }

  create(): void {
    const name = (this.draft.name || '').trim();
    const streamUrl = (this.draft.streamUrl || '').trim();
    if (!name || !streamUrl) {
      swal('Incomplete', 'Name and stream URL are required', 'warning');
      return;
    }
    const body: Record<string, unknown> = {
      name,
      streamUrl,
      protocol: this.draft.protocol,
      description: this.draft.description || null,
      recordMode: this.draft.recordMode,
      stationMode: this.draft.stationMode || null,
      analysisEnabled: !!this.draft.analysisEnabled,
    };
    if (this.draft.streamUsername) {
      body['streamUsername'] = this.draft.streamUsername;
      body['streamPassword'] = this.draft.streamPassword || '';
    }
    this.http.post<CameraRow>(this.api(), body).subscribe({
      next: () => {
        this.resetDraft();
        this.createOpen = false;
        swal('Saved', 'Camera created and MediaMTX path synced', 'success');
        this.load();
      },
      error: (err) => swal('Error', err?.error?.detail || 'Create failed', 'error'),
    });
  }

  saveDetail(): void {
    if (!this.selected) return;
    const name = (this.editDraft.name || '').trim();
    const streamUrl = (this.editDraft.streamUrl || '').trim();
    if (!name || !streamUrl) {
      swal('Incomplete', 'Name and stream URL are required', 'warning');
      return;
    }
    const body: Record<string, unknown> = {
      name,
      streamUrl,
      protocol: this.editDraft.protocol,
      description: this.editDraft.description || null,
      recordMode: this.editDraft.recordMode,
      stationMode: this.editDraft.stationMode || null,
      analysisEnabled: !!this.editDraft.analysisEnabled,
    };
    if (this.editDraft.streamUsername) {
      body['streamUsername'] = this.editDraft.streamUsername;
      body['streamPassword'] = this.editDraft.streamPassword || '';
    }
    this.http.patch<CameraRow>(this.api(`/${this.selected.cameraId}`), body).subscribe({
      next: (row) => {
        this.selected = row;
        this.detailOpen = false;
        swal('Saved', 'Camera connection updated', 'success');
        this.load();
      },
      error: (err) => swal('Error', err?.error?.detail || 'Update failed', 'error'),
    });
  }

  ping(cam: CameraRow): void {
    this.http
      .get<{ online: boolean; latency_ms?: number; error?: string }>(this.api(`/${cam.cameraId}/ping`))
      .subscribe({
        next: (res) => {
          swal(
            res.online ? 'Online' : 'Offline',
            res.online ? `Latency ${res.latency_ms ?? '—'} ms` : res.error || 'Unreachable',
            res.online ? 'success' : 'warning',
          );
          this.load();
        },
        error: (err) => swal('Error', err?.error?.detail || 'Ping failed', 'error'),
      });
  }

  snapshot(cam: CameraRow): void {
    this.http
      .post<{ imageBase64: string; contentType: string }>(this.api(`/${cam.cameraId}/snapshot`), {})
      .subscribe({
        next: (res) => {
          this.snapshotPreview = `data:${res.contentType};base64,${res.imageBase64}`;
        },
        error: (err) => swal('Error', err?.error?.detail || 'Snapshot failed', 'error'),
      });
  }

  toggleAnalysis(cam: CameraRow): void {
    const next = !cam.analysisEnabled;
    this.http.patch<CameraRow>(this.api(`/${cam.cameraId}`), { analysisEnabled: next }).subscribe({
      next: (row) => {
        cam.analysisEnabled = !!row.analysisEnabled;
      },
      error: (err) => swal('Error', err?.error?.detail || 'Failed to update analysis', 'error'),
    });
  }

  remove(cam: CameraRow): void {
    swal({
      title: 'Delete camera?',
      text: cam.name,
      icon: 'warning',
      buttons: ['Cancel', 'Delete'],
      dangerMode: true,
    }).then((ok) => {
      if (!ok) return;
      this.http.delete(this.api(`/${cam.cameraId}`)).subscribe({
        next: () => {
          this.detailOpen = false;
          this.selected = null;
          this.load();
        },
        error: (err) => swal('Error', err?.error?.detail || 'Delete failed', 'error'),
      });
    });
  }

  // ---- CSV import -----------------------------------------------------------

  triggerCsvPick(): void {
    this.csvInput?.nativeElement?.click();
  }

  onCsvSelected(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.importing = true;
    const fd = new FormData();
    fd.append('file', file);
    this.http.post<{ created: number; errors: unknown[] }>(this.peopleApi('/cameras/import-csv'), fd).subscribe({
      next: (res) => {
        this.importing = false;
        input.value = '';
        swal(
          'Import',
          `Created ${res.created}${res.errors?.length ? `, errors ${res.errors.length}` : ''}`,
          res.errors?.length ? 'warning' : 'success',
        );
        this.load();
      },
      error: (err) => {
        this.importing = false;
        input.value = '';
        swal('Error', err?.error?.detail || 'CSV import failed', 'error');
      },
    });
  }

  // ---- ROI editor -----------------------------------------------------------

  openRoiEditor(cam: CameraRow): void {
    this.roiCamera = cam;
    this.roiMode = 'line';
    this.roiDraft = [];
    this.roiCrowdMin = cam.aiConfig?.crowd_min_count ?? 5;
    this.roiLoiterSec = cam.aiConfig?.loiter_min_seconds ?? 30;
    this.roiPeopleEnabled = !!cam.aiConfig?.peopleEnabled;
    this.roiSnapshot = null;
    this.http
      .post<{ imageBase64: string; contentType: string }>(this.api(`/${cam.cameraId}/snapshot`), {})
      .subscribe({
        next: (res) => {
          this.roiSnapshot = `data:${res.contentType};base64,${res.imageBase64}`;
          setTimeout(() => this.redrawRoi(), 50);
        },
        error: (err) => {
          swal('Error', err?.error?.detail || 'Snapshot failed — ROI needs a live frame', 'error');
          this.roiCamera = null;
        },
      });
  }

  closeRoiEditor(): void {
    this.roiCamera = null;
    this.roiSnapshot = null;
    this.roiDraft = [];
  }

  onRoiImgLoad(): void {
    this.syncCanvasSize();
    this.seedDraftFromConfig();
    this.redrawRoi();
  }

  private syncCanvasSize(): void {
    const img = this.roiImg?.nativeElement;
    const canvas = this.roiCanvas?.nativeElement;
    if (!img || !canvas) return;
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
  }

  private seedDraftFromConfig(): void {
    const cfg = this.roiCamera?.aiConfig;
    if (!cfg) return;
    if (this.roiMode === 'line' && cfg.line?.length) this.roiDraft = cfg.line.map((p) => [...p]);
    if (this.roiMode === 'zone' && cfg.zone_polygon?.length)
      this.roiDraft = cfg.zone_polygon.map((p) => [...p]);
    if (this.roiMode === 'loiter' && cfg.loiter_polygon?.length)
      this.roiDraft = cfg.loiter_polygon.map((p) => [...p]);
    if (this.roiMode === 'roi' && cfg.roi_polygon?.length)
      this.roiDraft = cfg.roi_polygon.map((p) => [...p]);
  }

  setRoiMode(mode: RoiMode): void {
    this.roiMode = mode;
    this.roiDraft = [];
    this.seedDraftFromConfig();
    this.redrawRoi();
  }

  onCanvasClick(ev: MouseEvent): void {
    const canvas = this.roiCanvas?.nativeElement;
    const img = this.roiImg?.nativeElement;
    if (!canvas || !img || !img.naturalWidth) return;
    const rect = canvas.getBoundingClientRect();
    const sx = img.naturalWidth / canvas.width;
    const sy = img.naturalHeight / canvas.height;
    const x = (ev.clientX - rect.left) * sx;
    const y = (ev.clientY - rect.top) * sy;
    this.roiDraft = [...this.roiDraft, [Math.round(x), Math.round(y)]];
    this.redrawRoi();
  }

  undoRoiPoint(): void {
    this.roiDraft = this.roiDraft.slice(0, -1);
    this.redrawRoi();
  }

  clearRoiDraft(): void {
    this.roiDraft = [];
    this.redrawRoi();
  }

  private redrawRoi(): void {
    const canvas = this.roiCanvas?.nativeElement;
    const img = this.roiImg?.nativeElement;
    if (!canvas || !img || !img.naturalWidth) return;
    this.syncCanvasSize();
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const sx = canvas.width / img.naturalWidth;
    const sy = canvas.height / img.naturalHeight;
    const pts = this.roiDraft.map((p) => [p[0] * sx, p[1] * sy] as [number, number]);
    if (!pts.length) return;
    ctx.strokeStyle = '#0f766e';
    ctx.fillStyle = 'rgba(15, 118, 110, 0.2)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    if (this.roiMode !== 'line' && pts.length >= 3) {
      ctx.closePath();
      ctx.fill();
    }
    ctx.stroke();
    for (const [x, y] of pts) {
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#0f766e';
      ctx.fill();
    }
  }

  saveRoi(): void {
    if (!this.roiCamera) return;
    const minPts = this.roiMode === 'line' ? 2 : 3;
    if (this.roiDraft.length < minPts) {
      swal('Incomplete', `Need at least ${minPts} points for ${this.roiMode}`, 'warning');
      return;
    }
    const cfg: CameraAiConfig = { ...(this.roiCamera.aiConfig || {}) };
    if (this.roiMode === 'line') cfg.line = this.roiDraft;
    if (this.roiMode === 'zone') cfg.zone_polygon = this.roiDraft;
    if (this.roiMode === 'loiter') cfg.loiter_polygon = this.roiDraft;
    if (this.roiMode === 'roi') cfg.roi_polygon = this.roiDraft;
    cfg.crowd_min_count = this.roiCrowdMin;
    cfg.loiter_min_seconds = this.roiLoiterSec;
    cfg.peopleEnabled = this.roiPeopleEnabled;
    const modes: string[] = [];
    if (cfg.line?.length) modes.push('line_crossing');
    if (cfg.zone_polygon?.length) modes.push('zone_count');
    if (cfg.loiter_polygon?.length) modes.push('loitering');
    cfg.modes = modes;

    this.roiSaving = true;
    this.http
      .put<CameraRow>(this.peopleApi(`/cameras/${this.roiCamera.cameraId}/ai-config`), { aiConfig: cfg })
      .subscribe({
        next: (row) => {
          this.roiSaving = false;
          const idx = this.items.findIndex((c) => c.cameraId === row.cameraId);
          if (idx >= 0) this.items[idx] = { ...this.items[idx], ...row };
          this.applyFilter();
          swal('Saved', 'People ROI / ai_config updated', 'success');
          this.loadPeopleMetrics();
        },
        error: (err) => {
          this.roiSaving = false;
          swal('Error', err?.error?.detail || 'Failed to save ai_config', 'error');
        },
      });
  }

  cameraPeopleLabel(cam: CameraRow): string {
    if (cam.aiConfig?.peopleEnabled) return 'cctv.cameras.peopleOn';
    return 'cctv.cameras.peopleOff';
  }
}
