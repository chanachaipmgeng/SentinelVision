import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { EChartsOption } from 'echarts';
import { NgxEchartsModule } from 'ngx-echarts';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../shared/services/token.service';

export interface AnalyticsSummary {
  companyId: string;
  timezone: string;
  start: string;
  end: string;
  kpis: {
    totalEvents: number;
    peakOccupancy: number;
    camerasTotal: number;
    camerasOnline: number;
    camerasOffline: number;
    avgDwellSeconds: number;
    busySlots: { label: string; count: number }[];
  };
  heatmap: {
    cells: { weekday: number; hour: number; count: number }[];
    maxCount: number;
    totalEvents: number;
    source: string;
  };
  occupancy: {
    points: { bucket: string; subjects: number; events: number }[];
    peakOccupancy: number;
  };
  dwell: {
    cameras: {
      cameraId?: string | null;
      cameraName?: string | null;
      zoneName?: string | null;
      avgDwellSeconds: number;
      totalDwellSeconds: number;
      sessions: number;
    }[];
  };
  cameraHealth: {
    summary: {
      total: number;
      online: number;
      offline: number;
      unknown: number;
      stale: number;
      active: number;
      analysisEnabled: number;
    };
    cameras: {
      cameraId: string;
      name: string;
      status?: string;
      health: string;
      isActive: boolean;
      analysisEnabled: boolean;
      lastPingAt?: string | null;
      lastPingLatencyMs?: number | null;
      eventsInRange: number;
      stalePing?: boolean;
    }[];
  };
}

@Component({
  selector: 'app-face-monitor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    NgxEchartsModule,
    PageToolbarComponent,
    StatChipComponent,
    EmptyStateComponent,
  ],
  templateUrl: './face-monitor.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css', './face-monitor.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class FaceMonitorComponent implements OnInit {
  companyId = '';
  loading = false;
  exporting = false;
  error: string | null = null;
  summary: AnalyticsSummary | null = null;
  source: 'incidents' | 'attendance' | 'both' = 'both';
  rangeDays = 7;

  heatmapChart: EChartsOption = {};
  occupancyChart: EChartsOption = {};

  readonly weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    if (!this.companyId) {
      this.error = 'no-company';
      return;
    }
    this.loading = true;
    this.error = null;
    const { start, end } = this.rangeIso();
    const params = new HttpParams()
      .set('start', start)
      .set('end', end)
      .set('source', this.source);
    this.http
      .get<AnalyticsSummary>(`/analytics/company/${this.companyId}/summary`, { params })
      .subscribe({
        next: (data) => {
          this.summary = data;
          this.buildCharts(data);
          this.loading = false;
        },
        error: (err) => {
          console.error(err);
          this.error = 'load';
          this.loading = false;
        },
      });
  }

  exportPdf(): void {
    if (!this.companyId || this.exporting) return;
    this.exporting = true;
    const { start, end } = this.rangeIso();
    const params = new HttpParams()
      .set('start', start)
      .set('end', end)
      .set('source', this.source);
    this.http
      .get(`/analytics/company/${this.companyId}/export/pdf`, {
        params,
        responseType: 'blob',
      })
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `face-monitor-${this.companyId}.pdf`;
          a.click();
          URL.revokeObjectURL(url);
          this.exporting = false;
        },
        error: (err) => {
          console.error(err);
          this.exporting = false;
        },
      });
  }

  healthTone(health: string): 'ok' | 'warn' | 'danger' | 'soft' {
    switch (health) {
      case 'healthy':
        return 'ok';
      case 'degraded':
      case 'stale':
        return 'warn';
      case 'offline':
        return 'danger';
      default:
        return 'soft';
    }
  }

  private rangeIso(): { start: string; end: string } {
    const end = new Date();
    const start = new Date(end.getTime() - this.rangeDays * 24 * 60 * 60 * 1000);
    return { start: start.toISOString(), end: end.toISOString() };
  }

  private buildCharts(data: AnalyticsSummary): void {
    const brand = '#0f766e';
    const max = Math.max(1, data.heatmap?.maxCount || 1);
    const heatData = (data.heatmap?.cells || []).map((c) => [
      c.hour,
      c.weekday,
      c.count,
    ]);

    this.heatmapChart = {
      tooltip: {
        position: 'top',
        formatter: (p: any) => {
          const hour = p?.value?.[0];
          const wd = p?.value?.[1];
          const cnt = p?.value?.[2] ?? 0;
          return `${this.weekdayLabels[wd] || wd} ${String(hour).padStart(2, '0')}:00 — ${cnt}`;
        },
      },
      grid: { left: 48, right: 24, top: 16, bottom: 40 },
      xAxis: {
        type: 'category',
        data: Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')),
        splitArea: { show: true },
        axisLabel: { color: '#64748b' },
      },
      yAxis: {
        type: 'category',
        data: this.weekdayLabels,
        splitArea: { show: true },
        axisLabel: { color: '#64748b' },
      },
      visualMap: {
        min: 0,
        max,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: { color: ['#ecfdf5', brand, '#134e4a'] },
      },
      series: [
        {
          type: 'heatmap',
          data: heatData,
          label: { show: false },
          emphasis: {
            itemStyle: { shadowBlur: 8, shadowColor: 'rgba(15,118,110,0.35)' },
          },
        },
      ],
    };

    const points = data.occupancy?.points || [];
    this.occupancyChart = {
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: points.map((p) => {
          const d = new Date(p.bucket);
          return Number.isNaN(d.getTime())
            ? p.bucket
            : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' });
        }),
        axisLabel: { color: '#64748b', hideOverlap: true },
      },
      yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#64748b' } },
      series: [
        {
          name: 'subjects',
          type: 'line',
          smooth: true,
          areaStyle: { color: 'rgba(15,118,110,0.15)' },
          lineStyle: { color: brand, width: 2 },
          itemStyle: { color: brand },
          data: points.map((p) => p.subjects),
        },
      ],
    };
  }
}
