import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import { DashboardService, DashboardStats } from '../../services/dashboard.service';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule, SharedModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {

  stats: DashboardStats | null = null;
  isLoading = true;
  error: string | null = null;
  chartOption!: EChartsOption;

  constructor(private dashboardService: DashboardService) { }

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
        this.error = "Failed to load dashboard data.";
        console.error(err);
        this.isLoading = false;
      }
    });
  }

  setupChart(): void {
    if (!this.stats) return;

    const chartData = this.stats.chartData.checkInsLast7Days;

    this.chartOption = {
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        data: chartData.map(d => d.date),
        boundaryGap: false,
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: 'Check-ins',
          type: 'line',
          data: chartData.map(d => d.count),
          smooth: true,
          areaStyle: {},
          color: '#4f46e5' // Example color
        }
      ]
    };
  }
}
