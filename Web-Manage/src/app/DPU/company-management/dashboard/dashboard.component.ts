import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import {
  DashboardActivity,
  DashboardService,
  DashboardStats,
} from '../../services/dashboard.service';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { CheckinMapComponent } from '../../../shared/components/checkin-map/checkin-map.component';
import { SetupChecklistComponent } from '../../../shared/components/setup-checklist/setup-checklist.component';
import { WelcomeWizardComponent } from '../../../shared/components/welcome-wizard/welcome-wizard.component';
import { environment } from '../../../../environments/environment';

@Component({
    selector: 'app-dashboard',
    imports: [
        CommonModule,
        RouterModule,
        NgxEchartsModule,
        SharedModule,
        PageToolbarComponent,
        StatChipComponent,
        EmptyStateComponent,
        CheckinMapComponent,
        SetupChecklistComponent,
        WelcomeWizardComponent,
    ],
    templateUrl: './dashboard.component.html',
    styleUrls: [
        '../../../shared/styles/dpu-list-page.css',
        './dashboard.component.css',
    ],
    encapsulation: ViewEncapsulation.None
})
export class DashboardComponent implements OnInit, OnDestroy {
  stats: DashboardStats | null = null;
  isLoading = true;
  isRefreshing = false;
  error: string | null = null;
  liveOn = true;
  lastUpdated: Date | null = null;
  trendChart!: EChartsOption;
  mixChart!: EChartsOption;

  private pollTimer?: ReturnType<typeof setInterval>;
  private readonly pollMs = 12000;
  private knownIds = new Set<string>();
  newHighlightIds = new Set<string>();

  get weekTotal(): number {
    if (!this.stats?.chartData?.checkInsLast7Days) return 0;
    return this.stats.chartData.checkInsLast7Days.reduce(
      (sum, d) => sum + (d.count || 0),
      0
    );
  }

  get outsideToday(): number {
    return this.stats?.summary?.outsideToday ?? 0;
  }

  get inAreaToday(): number {
    return this.stats?.summary?.inAreaToday ?? 0;
  }

  get pendingApproval(): number {
    return this.stats?.summary?.pendingApproval ?? 0;
  }

  get mapPoints() {
    return this.stats?.mapPoints || [];
  }

  get companyLocations() {
    return this.stats?.companyLocations || [];
  }

  constructor(private dashboardService: DashboardService) {}

  ngOnInit(): void {
    this.loadStats(true);
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  toggleLive(): void {
    this.liveOn = !this.liveOn;
    if (this.liveOn) {
      this.startPolling();
      this.loadStats(false);
    } else {
      this.stopPolling();
    }
  }

  loadStats(initial = false): void {
    if (initial) {
      this.isLoading = true;
    } else {
      this.isRefreshing = true;
    }
    this.error = null;
    this.dashboardService.getStats().subscribe({
      next: (data) => {
        this.applyLiveDiff(data.recentActivity || []);
        this.stats = data;
        this.setupCharts();
        this.lastUpdated = new Date();
        this.isLoading = false;
        this.isRefreshing = false;
      },
      error: (err) => {
        this.error = 'โหลดข้อมูลแดชบอร์ดไม่สำเร็จ';
        console.error(err);
        this.isLoading = false;
        this.isRefreshing = false;
      },
    });
  }

  photoUrl(activity: DashboardActivity): string {
    if (activity.photoTimestamp) {
      return `${environment.baseUrl}/images/${activity.photoTimestamp}`;
    }
    if (activity.picture) {
      return `${environment.baseUrl}/images/${activity.picture}`;
    }
    return './assets/images/faces/1.jpg';
  }

  isInArea(activity: DashboardActivity): boolean {
    return activity.timestampType === 1;
  }

  isNew(activity: DashboardActivity): boolean {
    return !!(activity.timestampId && this.newHighlightIds.has(activity.timestampId));
  }

  private applyLiveDiff(activities: DashboardActivity[]): void {
    const nextIds = new Set<string>();
    const fresh = new Set<string>();
    for (const a of activities) {
      if (!a.timestampId) continue;
      nextIds.add(a.timestampId);
      if (this.knownIds.size && !this.knownIds.has(a.timestampId)) {
        fresh.add(a.timestampId);
      }
    }
    if (this.knownIds.size === 0) {
      this.knownIds = nextIds;
      this.newHighlightIds = new Set();
      return;
    }
    this.newHighlightIds = fresh;
    this.knownIds = nextIds;
    if (fresh.size) {
      setTimeout(() => {
        this.newHighlightIds = new Set();
      }, 8000);
    }
  }

  private startPolling(): void {
    this.stopPolling();
    if (!this.liveOn) return;
    this.pollTimer = setInterval(() => this.loadStats(false), this.pollMs);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = undefined;
    }
  }

  private setupCharts(): void {
    if (!this.stats) return;
    const brand = '#0f766e';
    const warn = '#c2410c';
    const chartData = this.stats.chartData.checkInsLast7Days || [];

    this.trendChart = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: 'rgba(15,118,110,0.2)',
      },
      grid: { left: 36, right: 16, top: 28, bottom: 28 },
      xAxis: {
        type: 'category',
        data: chartData.map((d) => d.date),
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
        axisLabel: { color: '#64748b' },
      },
      series: [
        {
          name: 'ลงเวลา',
          type: 'line',
          data: chartData.map((d) => d.count),
          smooth: true,
          symbol: 'circle',
          symbolSize: 7,
          lineStyle: { width: 3, color: brand },
          itemStyle: { color: brand },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(15,118,110,0.28)' },
                { offset: 1, color: 'rgba(15,118,110,0.02)' },
              ],
            },
          },
        },
      ],
    };

    const inArea = this.inAreaToday;
    const outside = this.outsideToday;
    this.mixChart = {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { color: '#64748b' } },
      series: [
        {
          name: 'วันนี้',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { color: '#0f172a' },
          data: [
            { value: inArea, name: 'ในพื้นที่', itemStyle: { color: brand } },
            { value: outside, name: 'นอกพื้นที่', itemStyle: { color: warn } },
          ],
        },
      ],
    };
  }
}
