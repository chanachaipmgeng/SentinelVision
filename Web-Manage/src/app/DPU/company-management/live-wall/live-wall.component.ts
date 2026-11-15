import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { WebrtcVideoSurfaceComponent } from '../../../shared/components/webrtc-video-surface/webrtc-video-surface.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TokenService } from '../../../shared/services/token.service';
import type { CameraRow } from '../cameras/cameras.component';

type WallLayout = '1x1' | '2x2' | '3x3';

@Component({
    selector: 'app-live-wall',
    imports: [
        CommonModule,
        FormsModule,
        RouterLink,
        TranslateModule,
        PageToolbarComponent,
        WebrtcVideoSurfaceComponent,
        EmptyStateComponent,
    ],
    templateUrl: './live-wall.component.html',
    styleUrl: './live-wall.component.css',
    encapsulation: ViewEncapsulation.None,
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class LiveWallComponent implements OnInit {
  companyId = '';
  cameras: CameraRow[] = [];
  layout: WallLayout = '2x2';
  focusId: string | null = null;
  useHlsFallback = false;
  loading = false;
  error = '';
  presetSavedMsg = '';
  snapshotPreviewUrl: string | null = null;
  snapshotCameraName = '';

  readonly layouts: WallLayout[] = ['1x1', '2x2', '3x3'];

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.loadPreset();
    this.focusId = this.route.snapshot.queryParamMap.get('cameraId');
    if (this.focusId) this.layout = '1x1';
    this.load();
  }

  savePreset(): void {
    if (!this.companyId) return;
    try {
      localStorage.setItem(
        `sv_livewall_preset_${this.companyId}`,
        JSON.stringify({ layout: this.layout, useHlsFallback: this.useHlsFallback }),
      );
      this.presetSavedMsg = `บันทึก Preset ${this.layout} แล้ว`;
      setTimeout(() => (this.presetSavedMsg = ''), 3000);
    } catch {
      // ignore storage errors
    }
  }

  private loadPreset(): void {
    if (!this.companyId) return;
    try {
      const raw = localStorage.getItem(`sv_livewall_preset_${this.companyId}`);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { layout?: WallLayout; useHlsFallback?: boolean };
      if (parsed.layout && this.layouts.includes(parsed.layout)) {
        this.layout = parsed.layout;
      }
      if (typeof parsed.useHlsFallback === 'boolean') {
        this.useHlsFallback = parsed.useHlsFallback;
      }
    } catch {
      // ignore storage errors
    }
  }

  snapshotCam(cam: CameraRow): void {
    if (!this.companyId) return;
    this.http
      .post<{ imageBase64: string; contentType: string }>(
        `/cameras/company/${this.companyId}/cameras/${cam.cameraId}/snapshot`,
        {},
      )
      .subscribe({
        next: (res) => {
          this.snapshotCameraName = cam.name;
          this.snapshotPreviewUrl = `data:${res.contentType};base64,${res.imageBase64}`;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.error = err?.error?.detail || `ไม่สามารถดึง Snapshot จาก ${cam.name}`;
          this.cdr.markForCheck();
        },
      });
  }

  get slots(): CameraRow[] {
    const active = this.cameras.filter((c) => c.isActive !== false);
    if (this.focusId) {
      const hit = active.find((c) => c.cameraId === this.focusId);
      if (hit) return [hit];
    }
    const n = this.layout === '1x1' ? 1 : this.layout === '2x2' ? 4 : 9;
    return active.slice(0, n);
  }

  load(): void {
    if (!this.companyId) return;
    this.loading = true;
    this.error = '';
    this.http.get<CameraRow[]>(`/cameras/company/${this.companyId}/cameras`).subscribe({
      next: (rows) => {
        this.cameras = rows || [];
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Failed to load cameras';
        this.cdr.markForCheck();
      },
    });
  }

  setLayout(layout: WallLayout): void {
    this.layout = layout;
    if (layout !== '1x1') this.focusId = null;
  }

  /** Multi-camera grids (2x2, 3x3) prefer low-bitrate sub-streams when available. */
  isGridMode(): boolean {
    return this.layout !== '1x1' && !this.focusId;
  }

  streamSrc(cam: CameraRow): string {
    const ext = cam as CameraRow & {
      subWhepPath?: string;
      subHlsPath?: string;
      subStreamPath?: string;
    };
    const grid = this.isGridMode();
    if (this.useHlsFallback) {
      return (grid && (ext.subHlsPath || ext.subStreamPath)) || cam.hlsPath || '';
    }
    return (grid && (ext.subWhepPath || ext.subStreamPath)) || cam.whepPath || '';
  }
}
