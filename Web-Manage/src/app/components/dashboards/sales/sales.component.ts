import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Renderer2, SimpleChanges, ViewChild } from '@angular/core';
import { RouterModule } from '@angular/router';
import * as L from 'leaflet';
import {
  ApexAxisChartSeries,
  ApexChart,
  ChartComponent,
  ApexDataLabels,
  ApexPlotOptions,
  ApexYAxis,
  ApexTitleSubtitle,
  ApexXAxis,
  ApexFill,
  NgApexchartsModule,
} from 'ng-apexcharts';
import { SharedModule } from '../../../shared/shared.module';
import { LeafletModule } from '@asymmetrik/ngx-leaflet';

export type ChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  dataLabels: ApexDataLabels;
  plotOptions: ApexPlotOptions;
  yaxis: ApexYAxis;
  xaxis: ApexXAxis;
  fill: ApexFill;
  title: ApexTitleSubtitle;
};
@Component({
  selector: 'app-sales',
  standalone: true,
  imports: [RouterModule,SharedModule,NgApexchartsModule,LeafletModule],
  templateUrl: './sales.component.html',
  styleUrls: ['./sales.component.scss']
})
export class SalesComponent  {
  @ViewChild('chart') chart!: ChartComponent;
  public chartOptions: Partial<ChartOptions> | any;
  optionsCircle1:any
  constructor(private el: ElementRef, private renderer: Renderer2,private cdr: ChangeDetectorRef) {
    this.optionsCircle1 = {
      series: [60],
      chart: {
        height: 229,
        type: 'radialBar',
      },
      colors: ['rgb(132, 90, 223)'],
      plotOptions: {
        radialBar: {
          hollow: {
            margin: 0,
            size: '70%',
            background: '#fff',
          },
          track: {
            dropShadow: {
              enabled: true,
              top: 2,
              left: 0,
              blur: 2,
              opacity: 0.15,
            },
          },
          dataLabels: {
            name: {
              offsetY: -10,
              color: '#4b9bfa',
              fontSize: '16px',
              show: false,
            },
            value: {
              color: '#4b9bfa',
              fontSize: '30px',
              show: true,
            },
          },
        },
        colors: [132, 90, 223],
      },
      stroke: {
        lineCap: 'round',
      },
      labels: ['Cart'],
    }
      this.chartOptions = {
        series: [
          { name: 'Sales', data: [44, 42, 57, 86, 58, 55, 70, 43, 23, 54, 77, 34] },
          { name: 'OPEX Ratio', data: [74, 72, 87, 116, 88, 85, 100, 73, 53, 84, 107, 64] },
          { name: 'General & Admin', data: [84, 82, 97, 126, 98, 95, 110, 83, 63, 94, 117, 74] },
          { name: 'Marketing', data: [-34, -22, -37, -56, -21, -35, -60, -34, -56, -78, -89, -53] }
        ],
        chart: {
          stacked: true,
          type: 'bar',
          height: 325,
        
        },
        grid: {
          borderColor: '#f5f4f4',
          strokeDashArray: 5,
          yaxis: { lines: { show: true } }
        },
        colors: ['rgb(132, 90, 223)', 'rgba(132, 90, 223, 0.6)', 'rgba(132, 90, 223, 0.3)', '#ebeff5'],
        plotOptions: {
          bar: {
            colors: {
              ranges: [
                { from: -100, to: -46, color: '#ebeff5' },
                { from: -45, to: 0, color: '#ebeff5' }
              ],
            },
            columnWidth: '20%',
          },
        },
        dataLabels: { enabled: false },
        legend: { show: true, position: 'top' },
    
     
    
    }
};
    // maps
  map!: L.Map;
  json:any;
  options1:any = {
    layers: [
      L.tileLayer("http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
      }),
      L.circleMarker([40.3, -101.38]).bindTooltip("Usa").openTooltip(),
      L.circleMarker([20.5937, 78.9629]).bindTooltip("India").openTooltip(),
      L.circleMarker([7.35, 134.46]).bindTooltip("Palau").openTooltip(),

      L.circleMarker([41.9, 12.45]).bindTooltip("Vatican City").openTooltip(),
      L.circleMarker([56.1304, -106.3468]).bindTooltip("Canada").openTooltip(),
      L.circleMarker([-20.2, 57.5]).bindTooltip("Mauritius").openTooltip(),
      L.circleMarker([1.3, 103.8]).bindTooltip("Singapore").openTooltip(),

      L.circleMarker([0.33, 6.73]).bindTooltip("São Tomé and Príncipe").openTooltip(),
      L.circleMarker([3.2, 73.22]).bindTooltip("Maldives").openTooltip(),
    ],
    circleMarker: {
      hover: {
        stroke: "#DDD",
        strokeWidth: 3,
        fill: "#FFF",
      },
      selected: {
        fill: "#ff525d",
      },
    },
    circleMarkerLabelStyle: {
      initial: {
        fontFamily: "Poppins",
        fontSize: 13,
        fontWeight: 500,
        fill: "#35373e",
      },
    },
    zoom: 0.5,
    center: L.latLng(0.33, 6.73)
  };
  
  // ngAfterViewInit(): void {
  //     this.setChartWidth();
  //   this.cdr.detectChanges();
  // }

  // private setChartWidth(): void {
  //   const chartContainer = this.el.nativeElement.querySelector('.chart-container');
  //   const chartContainer1 = this.el.nativeElement.querySelector('.chart-container1');
  //   const chart = new ApexCharts(chartContainer, this.chartOptions);
  //   const chart1 = new ApexCharts(chartContainer1, this.optionsCircle1);
  //    chart.render();
  //   chart1.render();
  
  // }

  
  
  ngOnInit(): void {
    

  }


}