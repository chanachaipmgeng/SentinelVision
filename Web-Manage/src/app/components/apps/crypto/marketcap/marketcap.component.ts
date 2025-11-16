import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-marketcap',
  standalone: true,
  imports: [SharedModule,NgSelectModule,NgApexchartsModule],
  templateUrl: './marketcap.component.html',
  styleUrls: ['./marketcap.component.scss']
})
export class MarketcapComponent {
  chartOptions:any;
  chartOptions1:any;
  chartOptions2:any;
  chartOptions3:any;
  chartOptions4:any;
  chartOptions5:any;
  chartOptions6:any;
  chartOptions7:any;
  chartOptions8:any;
  chartOptions9:any;
  chartOptions10:any;
  chartOptions11:any;
  chartOptions12:any;

  constructor() {
    this.chartOptions = {
      chart: {
        type: 'line',
        height: 40,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46,
          ],
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

      colors: ['#26bf94'],
    };
    this.chartOptions1 = {
      chart: {
        type: 'line',
        height: 40,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46,
          ],
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
      colors: ['#26bf94'],
    };
    this.chartOptions2 = {
      chart: {
        type: 'line',
        height: 40,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46,
          ],
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
      colors: ['#e6533c'],
    };
    this.chartOptions3 = {
      chart: {
        type: 'line',
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39,
            62, 51, 35, 41, 35, 27, 93, 53, 61, 27, 54, 43, 19, 46, 0, 45, 54,
            38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53, 61, 27,
            54, 43, 19, 46,
          ],
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

      tooltip: {
        enabled: false,
      },
      colors: ['rgb(230, 83, 60)'],
    };
    this.chartOptions4 = {
      chart: {
        type: 'line',
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39,
            62, 51, 35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41,
            35, 27, 93, 53, 61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27,
            54, 43, 19, 46,
          ],
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

      tooltip: {
        enabled: false,
      },
      colors: ['rgb(38, 191, 148)'],
    };
    this.chartOptions5 = {
      chart: {
        type: 'line',
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93,
            53, 61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39,
            62, 51, 35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41,
            35, 27, 93, 53, 61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27,
            54, 43, 19, 46,
          ],
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

      tooltip: {
        enabled: false,
      },
      colors: ['rgb(38, 191, 148)'],
    };
    this.chartOptions6={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
     
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(38, 191, 148)"],
    }
    this.chartOptions7={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
 
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(230, 83, 60)"],

    }
    this.chartOptions8={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
    
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(38, 191, 148)"],

    }
    this.chartOptions9={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(38, 191, 148)"],
    }
    this.chartOptions10={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(230, 83, 60)"],
    }
    this.chartOptions11={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(38, 191, 148)"],

    }
    this.chartOptions12={
      chart: {
        type: "line",
        height: 30,
        width: 120,
        sparkline: {
          enabled: true,
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 0,
          left: 0,
          blur: 3,
          color: "#000",
          opacity: 0.1,
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
          data: [
            0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 38, 56, 24, 65, 31, 37, 39, 62, 51,
            35, 41, 35, 27, 93, 53, 61, 65, 31, 37, 39, 62, 51, 35, 41, 35, 27, 93, 53,
            61, 27, 54, 43, 19, 46, 0, 45, 54, 93, 53, 61, 27, 54, 43, 19,
            46,
          ],
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
     
      tooltip: {
        enabled: false,
      },
      colors: ["rgb(38, 191, 148)"],

    }
  }
}
