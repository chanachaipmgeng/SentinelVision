import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../../../shared/shared.module';
import { NgApexchartsModule } from 'ng-apexcharts';

@Component({
  selector: 'app-polarareacharts',
  standalone: true,
  imports: [CommonModule,SharedModule,NgApexchartsModule],
  templateUrl: './polarareacharts.component.html',
  styleUrl: './polarareacharts.component.scss'
})
export class PolarareachartsComponent {
  chartOptions:any;
  chartOptions1:any;
  constructor() {
    this.chartOptions = {
      series: [14, 23, 21, 17, 15, 10, 12, 17, 21],
      chart: {
          type: 'polarArea',
          height: 300
      },
      stroke: {
          colors: ['#fff']
      },
      fill: {
          opacity: 0.8
      },
      legend: {
          position: 'bottom'
      },
      colors: ["#845adf", "#23b7e5", "#f5b849", "#49b6f5", "#e6533c", "#26bf94", "#a65e76", "#49b6f5", "#5b67c7"],
      responsive: [{
          breakpoint: 480,
          options: {
              chart: {
                  width: 200
              },
              legend: {
                  position: 'bottom'
              }
          }
      }]
    };
    this.chartOptions1= {
      series: [42, 47, 52, 58, 65],
        chart: {
            height: 300,
            type: 'polarArea'
        },
        labels: ['Rose A', 'Rose B', 'Rose C', 'Rose D', 'Rose E'],
        fill: {
            opacity: 1
        },
        stroke: {
            width: 1,
        },
        yaxis: {
            show: false
        },
        legend: {
            position: 'bottom'
        },
        plotOptions: {
            polarArea: {
                rings: {
                    strokeWidth: 0
                },
                spokes: {
                    strokeWidth: 0
                },
            }
        },
        theme: {
            monochrome: {
                enabled: true,
                shadeTo: 'light',
                shadeIntensity: 0.6,
                color: "#845adf",
            }
        }
    };
  }
}
