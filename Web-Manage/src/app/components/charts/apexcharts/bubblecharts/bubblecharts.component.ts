import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../../../shared/shared.module';
import { NgApexchartsModule } from 'ng-apexcharts';

@Component({
  selector: 'app-bubblecharts',
  standalone: true,
  imports: [CommonModule,SharedModule,NgApexchartsModule],
  templateUrl: './bubblecharts.component.html',
  styleUrl: './bubblecharts.component.scss'
})
export class BubblechartsComponent {
  chartOptions:any;
  chartOptions1:any;
  constructor() {
    this.chartOptions = {
      series: [
        {
          name: 'Bubble1',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Bubble2',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Bubble3',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Bubble4',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
      ],
      colors:['#845adf','#4fc5ea','#f7c66d'],
      chart: {
        height: 350,
        type: 'bubble',
      },
      dataLabels: {
        enabled: false,
      },
      fill: {
        opacity: 0.8,
      },
      title: {
        text: 'Simple Bubble Chart',
      },
      xaxis: {
        tickAmount: 12,
        type: 'category',
      },
      yaxis: {
        max: 70,
      },
    };
    this.chartOptions1 = {
      series: [
        {
          name: 'Product1',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Product2',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Product3',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
        {
          name: 'Product4',
          data: this.generateData(new Date('11 Feb 2017 GMT').getTime(), 20, {
            min: 10,
            max: 60,
          }),
        },
      ],
      colors:['#d0c0f2','#a0e0f4','#f6cf88'],
      chart: {
        height: 350,
        type: 'bubble',
      },
      dataLabels: {
        enabled: false,
      },
      fill: {
        type: 'gradient',
      },
      title: {
        text: '3D Bubble Chart',
      },
      xaxis: {
        tickAmount: 12,
        type: 'datetime',
        labels: {
          rotate: 0,
        },
      },
      yaxis: {
        max: 70,
      },
      theme: {
        palette: 'palette2',
      },
    };
  }

  public generateData(
    baseval: number,
    count: number,
    yrange: { min: any; max: any }
  ) {
    var i = 0;
    var series = [];
    while (i < count) {
      var x = Math.floor(Math.random() * (750 - 1 + 1)) + 1;
      var y =
        Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min;
      var z = Math.floor(Math.random() * (75 - 15 + 1)) + 15;

      series.push([x, y, z]);
      baseval += 86400000;
      i++;
    }
    return series;
  }
}
