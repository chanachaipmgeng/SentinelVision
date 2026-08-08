import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import { DashboardService, DashboardStats } from '../../services/dashboard.service';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    NgxEchartsModule,
    SharedModule,
    PageToolbarComponent,
    StatChipComponent,
    EmptyStateComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: [
    '../../../shared/styles/dpu-list-page.css',
    './dashboard.component.css',
  ],
  encapsulation: ViewEncapsulation.None,
})
export class DashboardComponent implements OnInit {
  stats: DashboardStats | null = null;
  isLoading = true;
  error: string | null = null;
  chartOption!: EChartsOption;

  get weekTotal(): number {
    if (!this.stats?.chartData?.checkInsLast7Days) return 0;
    return this.stats.chartData.checkInsLast7Days.reduce((sum, d) => sum + (d.count || 0), 0);
  }

  get outsideAreaCount(): number {
    if (!this.stats?.recentActivity?.length) return 0;
    return this.stats.recentActivity.filter((a) => a.timestampType !== 1).length;
  }

  constructor(private dashboardService: DashboardService) {}

  ngOnInit(): void {
    this.loadStats();
  }

  loadStats(): void {
    this.isLoading = true;
    this.error = null;
    this.dashboardService.getStats().subscribe({
      next: (data) => {
        this.stats = data;
        this.setupChart();
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'โหลดข้อมูลแดชบอร์ดไม่สำเร็จ';
        console.error(err);
        this.isLoading = false;
      },
    });
  }

  setupChart(): void {
    if (!this.stats) return;

    const chartData = this.stats.chartData.checkInsLast7Days;
    const brand = '#0f766e';

    this.chartOption = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: 'rgba(15,118,110,0.2)',
        textStyle: { color: '#0f172a' },
      },
      grid: { left: 36, right: 16, top: 24, bottom: 28 },
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
  }
}
