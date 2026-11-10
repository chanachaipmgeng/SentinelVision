import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { TokenService } from '../../../shared/services/token.service';
import type { CameraRow } from '../cameras/cameras.component';

export interface VideoClipRow {
  clipId: string;
  companyId: string;
  cameraId: string;
  cameraName?: string | null;
  incidentId?: string | null;
  startedAt: string;
  endedAt: string;
  storageKey: string;
  durationMs: number;
  kind: 'event' | 'continuous_ref' | string;
  downloadPath?: string;
}

@Component({
  selector: 'app-company-playback',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslateModule, PageToolbarComponent],
  templateUrl: './playback.component.html',
  styleUrl: './playback.component.css',
  encapsulation: ViewEncapsulation.None,
})
export class PlaybackComponent implements OnInit, OnDestroy {
  @ViewChild('player') playerRef?: ElementRef<HTMLVideoElement>;

  companyId = '';
  cameras: CameraRow[] = [];
  clips: VideoClipRow[] = [];
  selected: VideoClipRow | null = null;
  filterCameraId = '';
  filterKind: '' | 'event' | 'continuous_ref' = '';
  filterIncidentId = '';
  filterFrom = '';
  filterTo = '';
  loading = false;
  exporting = false;
  syncing = false;
  error = '';
  objectUrl = '';
  currentTime = 0;
  duration = 0;

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private route: ActivatedRoute,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    const q = this.route.snapshot.queryParamMap;
    this.filterCameraId = q.get('cameraId') || '';
    this.filterIncidentId = q.get('incidentId') || '';
    this.filterFrom = q.get('from') || '';
    this.filterTo = q.get('to') || '';
    const kind = q.get('kind');
    if (kind === 'event' || kind === 'continuous_ref') this.filterKind = kind;
    this.loadCameras();
    this.loadClips();
  }

  ngOnDestroy(): void {
    this.revokeObjectUrl();
  }

  get continuousCameras(): CameraRow[] {
    return this.cameras.filter((c) => (c.recordMode || '').toLowerCase() === 'continuous');
  }

  get canExport(): boolean {
    return !!this.filterCameraId && !this.exporting;
  }

  get canSyncContinuous(): boolean {
    if (!this.filterCameraId || this.syncing) return false;
    const cam = this.cameras.find((c) => c.cameraId === this.filterCameraId);
    return !!cam && (cam.recordMode || '').toLowerCase() === 'continuous';
  }

  downloadHref(clip: VideoClipRow | null): string {
    if (!clip) return '';
    return (
      clip.downloadPath ||
      `/cameras/company/${this.companyId}/clips/${clip.clipId}/download`
    );
  }

  loadCameras(): void {
    if (!this.companyId) return;
    this.http.get<CameraRow[]>(`/cameras/company/${this.companyId}/cameras`).subscribe({
      next: (rows) => (this.cameras = rows || []),
      error: () => (this.cameras = []),
    });
  }

  loadClips(): void {
    if (!this.companyId) return;
    this.loading = true;
    this.error = '';
    const params: Record<string, string> = { limit: '100' };
    if (this.filterCameraId) params['cameraId'] = this.filterCameraId;
    if (this.filterIncidentId) params['incidentId'] = this.filterIncidentId;
    if (this.filterKind) params['kind'] = this.filterKind;
    if (this.filterFrom) params['startedFrom'] = this.filterFrom;
    if (this.filterTo) params['startedTo'] = this.filterTo;

    // continuous_ref is only valid for continuous cameras — clear kind if camera is not continuous.
    if (this.filterKind === 'continuous_ref' && this.filterCameraId) {
      const cam = this.cameras.find((c) => c.cameraId === this.filterCameraId);
      if (cam && (cam.recordMode || '').toLowerCase() !== 'continuous') {
        this.filterKind = 'event';
        params['kind'] = 'event';
      }
    }

    this.http
      .get<VideoClipRow[]>(`/cameras/company/${this.companyId}/clips`, { params })
      .subscribe({
        next: (rows) => {
          this.clips = rows || [];
          this.loading = false;
          if (this.selected) {
            const fresh = this.clips.find((c) => c.clipId === this.selected!.clipId);
            if (fresh) this.selectClip(fresh);
            else if (this.clips.length) this.selectClip(this.clips[0]);
            else this.clearPlayer();
          } else if (this.clips.length) {
            this.selectClip(this.clips[0]);
          }
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Failed to load clips';
          this.clips = [];
        },
      });
  }

  exportClip(): void {
    if (!this.canExport) return;
    this.exporting = true;
    this.error = '';
    this.http
      .post<VideoClipRow>(
        `/cameras/company/${this.companyId}/cameras/${this.filterCameraId}/clips`,
        { waitForPost: false },
      )
      .subscribe({
        next: (clip) => {
          this.exporting = false;
          this.filterKind = 'event';
          this.loadClips();
          if (clip?.clipId) this.selectClip(clip);
        },
        error: (err) => {
          this.exporting = false;
          this.error = err?.error?.detail || 'Export failed';
        },
      });
  }

  syncContinuous(): void {
    if (!this.canSyncContinuous) return;
    this.syncing = true;
    this.error = '';
    this.http
      .get<VideoClipRow[]>(
        `/cameras/company/${this.companyId}/cameras/${this.filterCameraId}/continuous-refs`,
      )
      .subscribe({
        next: () => {
          this.syncing = false;
          this.filterKind = 'continuous_ref';
          this.loadClips();
        },
        error: (err) => {
          this.syncing = false;
          this.error = err?.error?.detail || 'Sync continuous failed';
        },
      });
  }

  downloadSelected(): void {
    if (!this.selected) return;
    const path = this.downloadHref(this.selected);
    const name = `${this.selected.clipId || 'clip'}.mp4`;
    this.http.get(path, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Download failed';
      },
    });
  }

  selectClip(clip: VideoClipRow): void {
    this.selected = clip;
    this.revokeObjectUrl();
    this.currentTime = 0;
    this.duration = Math.max(0, (clip.durationMs || 0) / 1000);
    const path = this.downloadHref(clip);
    this.http.get(path, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.objectUrl = URL.createObjectURL(blob);
        setTimeout(() => {
          const el = this.playerRef?.nativeElement;
          if (el) {
            el.load();
            void el.play().catch(() => undefined);
          }
        });
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Failed to load clip media';
      },
    });
  }

  onTimeUpdate(): void {
    const el = this.playerRef?.nativeElement;
    if (!el) return;
    this.currentTime = el.currentTime || 0;
    if (el.duration && isFinite(el.duration)) this.duration = el.duration;
  }

  onScrub(value: string | number): void {
    const el = this.playerRef?.nativeElement;
    if (!el) return;
    const t = Number(value);
    if (!isFinite(t)) return;
    el.currentTime = t;
    this.currentTime = t;
  }

  formatTime(sec: number): string {
    const s = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2, '0')}`;
  }

  kindLabel(kind: string): string {
    return kind === 'continuous_ref' ? 'continuous' : kind || 'event';
  }

  private clearPlayer(): void {
    this.selected = null;
    this.revokeObjectUrl();
    this.currentTime = 0;
    this.duration = 0;
  }

  private revokeObjectUrl(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = '';
    }
  }
}
