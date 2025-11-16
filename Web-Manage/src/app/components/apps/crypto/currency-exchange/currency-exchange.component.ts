import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import {
  ChartComponent,
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexDataLabels,
  ApexTitleSubtitle,
  ApexStroke,
  ApexGrid,
  NgApexchartsModule,
} from 'ng-apexcharts';
import { SharedModule } from '../../../../shared/shared.module';

export type ChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  dataLabels: ApexDataLabels;
  grid: ApexGrid;
  stroke: ApexStroke;
  title: ApexTitleSubtitle;
};
@Component({
  selector: 'app-currency-exchange',
  standalone: true,
  imports: [SharedModule,NgSelectModule,NgApexchartsModule],
  templateUrl: './currency-exchange.component.html',
  styleUrls: ['./currency-exchange.component.scss']
})
export class CurrencyExchangeComponent {
  chartOptions:any
  chartOptions1:any
  chartOptions2:any
  chartOptions3:any
  chartOptions4:any
  chartOptions5:any
  chartOptions6:any
  chartOptions7:any
  constructor() {
    this.chartOptions = {
      chart: {
        type: 'area',
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: '#fff',
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: 'smooth',
        lineCap: 'butt',
        colors: undefined,
        width: 1.5,
        dashArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: 'Value',
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },

      colors: ['rgba(132, 90, 223,0.5)'],
      tooltip: {
        enabled: false,
      },
    };
    this.chartOptions1 = {
      chart: {
        type: "area",
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: "#fff",
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: "smooth",
        lineCap: "butt",
        colors: undefined,
        width: 1.5,
        dashArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: "Value",
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },
   
      colors: ["rgba(35, 183, 229,0.5)"],
      tooltip: {
        enabled: false,
      },
    };
    this.chartOptions2={
      chart: {
        type: "area",
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: "#fff",
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: "smooth",
        lineCap: "butt",
        colors: undefined,
        width: 1.5,
        dashArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: "Value",
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },
     
      colors: ["rgba(38, 191, 148,0.5)"],
      tooltip: {
        enabled: false,
      },
    }
    this.chartOptions3={
      chart: {
        type: "area",
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: "#fff",
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: "smooth",
        lineCap: "butt",
        colors: undefined,
        width: 1.5,
        ltcArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: "Value",
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },
    
      colors: ["rgba(245, 184, 73,0.5)"],
      tooltip: {
        enabled: false,
      },

    }
    this.chartOptions4={
      chart: {
        type: "area",
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: "#fff",
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: "smooth",
        lineCap: "butt",
        colors: undefined,
        width: 1.5,
        ltcArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: "Value",
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },
      
      colors: ["rgba(231, 145, 188,0.5)"],
      tooltip: {
        enabled: false,
      },

    }
    this.chartOptions5={
      chart: {
        type: "area",
        height: 60,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 1,
          color: "#fff",
          opacity: 0.05,
        },
      },
      stroke: {
        show: true,
        curve: "smooth",
        lineCap: "butt",
        colors: undefined,
        width: 1.5,
        ltcArray: 0,
      },
      fill: {
        gradient: {
          enabled: false,
        },
      },
      series: [
        {
          name: "Value",
          data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
        },
      ],
      yaxis: {
        min: 0,
        show: false,
        axisBorder: {
          show: false,
        },
      },
      xaxis: {
        axisBorder: {
          show: false,
        },
      },
     
      colors: ["rgba(137, 32, 173,0.5)"],
      tooltip: {
        enabled: false,
      },

      }
      this.chartOptions6={
        chart: {
          type: "area",
          height: 60,
          sparkline: {
            enabled: true,
          },
          dropShadow: {
            enabled: true,
            enabledOnSeries: undefined,
            top: 0,
            left: 0,
            blur: 1,
            color: "#fff",
            opacity: 0.05,
          },
        },
        stroke: {
          show: true,
          curve: "smooth",
          lineCap: "butt",
          colors: undefined,
          width: 1.5,
          ltcArray: 0,
        },
        fill: {
          gradient: {
            enabled: false,
          },
        },
        series: [
          {
            name: "Value",
            data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
          },
        ],
        yaxis: {
          min: 0,
          show: false,
          axisBorder: {
            show: false,
          },
        },
        xaxis: {
          axisBorder: {
            show: false,
          },
        },
      
        colors: ["rgba(230, 83, 60,0.5)"],
        tooltip: {
          enabled: false,
        },
      }
      this.chartOptions7={
        chart: {
          type: "area",
          height: 60,
          sparkline: {
            enabled: true,
          },
          dropShadow: {
            enabled: true,
            enabledOnSeries: undefined,
            top: 0,
            left: 0,
            blur: 1,
            color: "#fff",
            opacity: 0.05,
          },
        },
        stroke: {
          show: true,
          curve: "smooth",
          lineCap: "butt",
          colors: undefined,
          width: 1.5,
          ltcArray: 0,
        },
        fill: {
          gradient: {
            enabled: false,
          },
        },
        series: [
          {
            name: "Value",
            data: [54, 38, 56, 35, 65, 43, 53, 45, 62, 80, 35, 48],
          },
        ],
        yaxis: {
          min: 0,
          show: false,
          axisBorder: {
            show: false,
          },
        },
        xaxis: {
          axisBorder: {
            show: false,
          },
        },
        colors: ["rgba(73, 182, 245,0.5)"],
        tooltip: {
          enabled: false,
        },

      }
  }
}
