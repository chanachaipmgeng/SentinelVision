import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import swal from 'sweetalert';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../shared/services/token.service';
import { VALID_STATION_MODES } from '../../services/company-module-config.service';

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
  isActive?: boolean;
  whepPath?: string;
  hlsPath?: string;
  mtxPath?: string;
}

@Component({
  selector: 'app-company-cameras',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    TranslateModule,
    PageToolbarComponent,
    PillSearchComponent,
    StatChipComponent,
    EmptyStateComponent,
  ],
  templateUrl: './cameras.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css', './cameras.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class CamerasComponent implements OnInit {
  readonly stationModes = VALID_STATION_MODES;
  readonly protocols = ['rtsp', 'http', 'hls', 'rtmp'];
  readonly recordModes = ['event', 'continuous', 'off'];

  companyId = '';
  loading = false;
  items: CameraRow[] = [];
  filtered: CameraRow[] = [];
  private _searchTerm = '';
  snapshotPreview: string | null = null;
  showForm = false;

  draft = {
    name: '',
    streamUrl: '',
    protocol: 'rtsp',
    description: '',
    streamUsername: '',
    streamPassword: '',
    stationMode: '',
    recordMode: 'event',
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

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.load();
  }

  private api(path = ''): string {
    return `/cameras/company/${this.companyId}/cameras${path}`;
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
    };
    if (this.draft.streamUsername) {
      body['streamUsername'] = this.draft.streamUsername;
      body['streamPassword'] = this.draft.streamPassword || '';
    }
    this.http.post<CameraRow>(this.api(), body).subscribe({
      next: () => {
        this.resetDraft();
        this.showForm = false;
        swal('Saved', 'Camera created and MediaMTX path synced', 'success');
        this.load();
      },
      error: (err) => swal('Error', err?.error?.detail || 'Create failed', 'error'),
    });
  }

  ping(cam: CameraRow): void {
    this.http.get<{ online: boolean; latency_ms?: number; error?: string }>(
      this.api(`/${cam.cameraId}/ping`),
    ).subscribe({
      next: (res) => {
        swal(
          res.online ? 'Online' : 'Offline',
          res.online
            ? `Latency ${res.latency_ms ?? '—'} ms`
            : res.error || 'Unreachable',
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
        next: () => this.load(),
        error: (err) => swal('Error', err?.error?.detail || 'Delete failed', 'error'),
      });
    });
  }
}
