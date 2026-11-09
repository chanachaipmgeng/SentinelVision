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
  loading = false;
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

  selectClip(clip: VideoClipRow): void {
    this.selected = clip;
    this.revokeObjectUrl();
    this.currentTime = 0;
    this.duration = Math.max(0, (clip.durationMs || 0) / 1000);
    const path =
      clip.downloadPath ||
      `/cameras/company/${this.companyId}/clips/${clip.clipId}/download`;
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
