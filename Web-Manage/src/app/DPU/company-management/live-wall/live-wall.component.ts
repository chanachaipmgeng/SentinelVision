import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
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
    encapsulation: ViewEncapsulation.None
})
export class LiveWallComponent implements OnInit {
  companyId = '';
  cameras: CameraRow[] = [];
  layout: WallLayout = '2x2';
  focusId: string | null = null;
  useHlsFallback = false;
  loading = false;
  error = '';

  readonly layouts: WallLayout[] = ['1x1', '2x2', '3x3'];

  constructor(
    private http: HttpClient,
    private token: TokenService,
    private route: ActivatedRoute,
  ) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.focusId = this.route.snapshot.queryParamMap.get('cameraId');
    if (this.focusId) this.layout = '1x1';
    this.load();
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
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Failed to load cameras';
      },
    });
  }

  setLayout(layout: WallLayout): void {
    this.layout = layout;
    if (layout !== '1x1') this.focusId = null;
  }

  streamSrc(cam: CameraRow): string {
    if (this.useHlsFallback) {
      return cam.hlsPath || '';
    }
    return cam.whepPath || '';
  }
}
