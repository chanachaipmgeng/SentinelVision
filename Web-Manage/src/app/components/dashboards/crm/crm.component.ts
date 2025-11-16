import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../shared/shared.module';
import { NgChartsModule } from 'ng2-charts';
@Component({
  selector: 'app-crm',
  standalone: true,
  imports: [RouterModule,NgApexchartsModule,SharedModule,NgChartsModule],
  templateUrl: './crm.component.html',
  styleUrl: './crm.component.scss'
})
export class CrmComponent {
  optionsCircle1: any;
  optionsCircle: any;
  chartOptions1:any
  chartOptions2:any
  chartOptions3:any
  chartOptions4:any
  chartOptions5:any
  chartOptions7:any
  
  constructor() {
    this.optionsCircle1 = {
      series: [32, 27, 25, 16],
      colors: ["rgb(132, 90, 223)", "rgb(35, 183, 229)",  "rgb(245, 184, 73)", "rgb(38, 191, 148)",],
      chart: {
        events: {
          mounted: (chart:any) => {
            chart.windowResizeHandler();
          }
        },
        height: 300,
        type: 'donut',
        dropShadow: {
          enabled: false,
          top: 5,
          left: 0,
          blur: 3,
          color: '#525050',
          opacity: 0.1,
        },
      },
      dataLabels: {
        enabled: false,
      },
      plotOptions: {

        pie: {
            expandOnClick: false,
            donut: {
                size: '80%',
                labels: {
                    show: false,
                    name: {
                        show: true,
                        fontSize: '20px',
                        color: '#495057',
                        offsetY: -4
                    },
                    value: {
                        show: true,
                        fontSize: '18px',
                        offsetY: 8,
                        formatter: function (val: string) {
                            return val + "%";
                        }
                    },

                }
            }
        }
    },
        
      legend: {
        show: false,
      },
      stroke: {
        show: true,
        curve: 'smooth',
        lineCap: 'round',
        colors: '#fff',
        width: 0,
        dashArray: 0,
      },
  
    };
    this.optionsCircle={
      chart: {
        height: 127,
        width: 100,
        type: 'radialBar',
      },

      series: [48],
      // colors: ['#fff'],
      plotOptions: {
        radialBar: {
          hollow: {
            margin: 0,
            size: '55%',
            background: '#fff',
          },
          dataLabels: {
            name: {
              offsetY: -10,
              color: '#4b9bfa',
              fontSize: '.625rem',
              show: false,
            },
            value: {
              offsetY: 5,
              color: '#4b9bfa',
              fontSize: '.875rem',
              show: true,
              fontWeight: 600,
            },
          },
        },
      },
      stroke: {
        lineCap: 'round',
      },
      labels: ['Status'],
      colors:['#fff']
    }
    this.chartOptions1 = {
    
      series: [{
        name: 'Value',
        data: [20, 14, 19, 10, 23, 20, 22, 9, 12]
    }],
    colors: ["rgb(132, 90, 223)"],
    chart: {
        type: 'line',
        height: 30,
        width: 100,
        sparkline: {
            enabled: true
        },
      
    },
    stroke: {
        show: true,
        curve: 'smooth',
        lineCap: 'butt',
        width: 1.5,
        dashArray: 0,
    },
    fill: {
        type: 'gradient',
        gradient: {
            opacityFrom: 0.9,
            opacityTo: 0.9,
            stops: [0, 98],
        }
    },
    yaxis: {
        min: 0,
        show: false,
        axisBorder: {
            show: false
        },
    },
    xaxis: {
        // show: false,
        axisBorder: {
            show: false
        },
    },
    tooltip: {
        enabled: false,
    }, 
  }
  this.chartOptions2 = {
    chart: {
      type: 'line',
      height: 40,
      width: 100,
      sparkline: {
        enabled: true,
      },
    },
    stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
    },
    fill: {
      type: 'gradient',
      gradient: {
        opacityFrom: 0.9,
        opacityTo: 0.9,
        stops: [0, 98],
      },
    },
    series: [
      {
        name: 'Value',
        data: [20, 14, 20, 22, 9, 12, 19, 10, 25],
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
      show: false,
      axisBorder: {
        show: false,
      },
    },
    tooltip: {
      enabled: false,
    },
    colors: ['rgb(35, 183, 229)'],
  };
  this.chartOptions3 = {
    chart: {
      type: 'line',
      height: 40,
      width: 100,
      sparkline: {
        enabled: true,
      },
    },
    stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
    },
    fill: {
      type: 'gradient',
      gradient: {
        opacityFrom: 0.9,
        opacityTo: 0.9,
        stops: [0, 98],
      },
    },
    series: [
      {
        name: 'Value',
        data: [20, 20, 22, 9, 14, 19, 10, 25, 12],
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
      show: false,
      axisBorder: {
        show: false,
      },
    },
    tooltip: {
      enabled: false,
    },
    colors: ['rgb(38, 191, 148)'],
  };
  this.chartOptions4 = {
    chart: {
      type: 'line',
      height: 40,
      width: 100,
      sparkline: {
        enabled: true,
      },
    },
    stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
    },
    fill: {
      type: 'gradient',
      gradient: {
        opacityFrom: 0.9,
        opacityTo: 0.9,
        stops: [0, 98],
      },
    },
    series: [
      {
        name: 'Value',
        data: [20, 20, 22, 9, 12, 14, 19, 10, 25],
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
      show: false,
      axisBorder: {
        show: false,
      },
    },
    tooltip: {
      enabled: false,
    },
    colors: ['rgb(245, 184, 73)'],
  };
  this.chartOptions5 = {
    series: [
      {
          type: 'line',
          name: 'Profit',
          data: [
              {
                  x: 'Jan',
                  y: 100
              },
              {
                  x: 'Feb',
                  y: 210
              },
              {
                  x: 'Mar',
                  y: 180
              },
              {
                  x: 'Apr',
                  y: 454
              },
              {
                  x: 'May',
                  y: 230
              },
              {
                  x: 'Jun',
                  y: 320
              },
              {
                  x: 'Jul',
                  y: 656
              },
              {
                  x: 'Aug',
                  y: 830
              },
              {
                  x: 'Sep',
                  y: 350
              },
              {
                  x: 'Oct',
                  y: 350
              },
              {
                  x: 'Nov',
                  y: 210
              },
              {
                  x: 'Dec',
                  y: 410
              }
          ]
      },
      {
          type: 'line',
          name: 'Revenue',
          data: [
              {
                  x: 'Jan',
                  y: 180
              },
              {
                  x: 'Feb',
                  y: 620
              },
              {
                  x: 'Mar',
                  y: 476
              },
              {
                  x: 'Apr',
                  y: 220
              },
              {
                  x: 'May',
                  y: 520
              },
              {
                  x: 'Jun',
                  y: 780
              },
              {
                  x: 'Jul',
                  y: 435
              },
              {
                  x: 'Aug',
                  y: 515
              },
              {
                  x: 'Sep',
                  y: 738
              },
              {
                  x: 'Oct',
                  y: 454
              },
              {
                  x: 'Nov',
                  y: 525
              },
              {
                  x: 'Dec',
                  y: 230
              }
          ]
      },
      {
          type: 'area',
          name: 'Sales',
          data: [
              {
                  x: 'Jan',
                  y: 200
              },
              {
                  x: 'Feb',
                  y: 530
              },
              {
                  x: 'Mar',
                  y: 110
              },
              {
                  x: 'Apr',
                  y: 130
              },
              {
                  x: 'May',
                  y: 480
              },
              {
                  x: 'Jun',
                  y: 520
              },
              {
                  x: 'Jul',
                  y: 780
              },
              {
                  x: 'Aug',
                  y: 435
              },
              {
                  x: 'Sep',
                  y: 475
              },
              {
                  x: 'Oct',
                  y: 738
              },
              {
                  x: 'Nov',
                  y: 454
              },
              {
                  x: 'Dec',
                  y: 480
              }
          ]
      }
  ],
    chart: {
      height: 350,
      animations: {
          speed: 500
      },
      dropShadow: {
          enabled: true,
          top: 8,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      },
  
  },
  colors: ["rgb(132, 90, 223)", "rgba(35, 183, 229, 0.85)", "rgba(119, 119, 142, 0.05)"],
  dataLabels: {
      enabled: false
  },
  grid: {
      borderColor: '#f1f1f1',
      strokeDashArray: 3
  },
  stroke: {
      curve: 'smooth',
      width: [2, 2, 0],
      dashArray: [0, 5, 0],
  },
  xaxis: {
      axisTicks: {
          show: false,
      },
  },
  yaxis: {
      labels: {
          formatter: function (value: string) {
              return "$" + value;
          }
      },
  },
  tooltip: {
      y: [{
          formatter: function (e: number ) {
              return void 0 !== e ? "$" + e.toFixed(0) : e;
          }
      }, {
          formatter: function (e: number ) {
              return void 0 !== e ? "$" + e.toFixed(0) : e;
          }
      }, {
          formatter: function (e: number ) {
              return void 0 !== e ? e.toFixed(0) : e;
          }
      }]
  },
  legend: {
      show: true,
      customLegendItems: ['Profit', 'Revenue', 'Sales'],
      inverseOrder: true
  },
  title: {
      text: 'Revenue Analytics with sales & profit (USD)',
      align: 'left',
      style: {
          fontSize: '.8125rem',
          fontWeight: 'semibold',
          color: '#8c9097'
      },
  },
  markers: {
      hover: {
          sizeOffset: 5
      }
  },

  };
  this.chartOptions7 = {
    series: [
      {
        name: 'Profit Earned',
        data: [44, 42, 57, 86, 58, 55, 70],
      },
      {
        name: 'Total Sales',
        data: [34, 22, 37, 56, 21, 35, 60],
      },
    ],
    chart: {
      type: 'bar',
      height: 180,
      toolbar: {
        show: false,
      },
    },
    grid: {
      borderColor: '#f1f1f1',
      strokeDashArray: 3,
    },
    colors: ['rgb(132, 90, 223)', '#e4e7ed'],
    plotOptions: {
      bar: {
        colors: {
          ranges: [
            {
              from: -100,
              to: -46,
              color: '#ebeff5',
            },
            {
              from: -45,
              to: 0,
              color: '#ebeff5',
            },
          ],
        },
        columnWidth: '60%',
        borderRadius: 5,
      },
    },
    dataLabels: {
      enabled: false,
    },
    stroke: {
      show: true,
      width: 2,
    },
    legend: {
      show: false,
      position: 'top',
    },
    yaxis: {
      title: {
        style: {
          color: '#adb5be',
          fontSize: '13px',
          fontFamily: 'poppins, sans-serif',
          fontWeight: 600,
          cssClass: 'apexcharts-yaxis-label',
        },
      },
      labels: {
        formatter: function (y: number) {
          return y.toFixed(0) + '';
        },
      },
    },
    xaxis: {
      type: 'week',
      categories: ['S', 'M', 'T', 'W', 'T', 'F', 'S'],
      axisBorder: {
        show: true,
        color: 'rgba(119, 119, 142, 0.05)',
        offsetX: 0,
        offsetY: 0,
      },
      axisTicks: {
        show: true,
        borderType: 'solid',
        color: 'rgba(119, 119, 142, 0.05)',
        width: 6,
        offsetX: 0,
        offsetY: 0,
      },
      labels: {
        rotate: -90,
      },
    },
  };
}
}
