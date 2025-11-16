import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../../shared/shared.module';
import { LeafletModule } from '@asymmetrik/ngx-leaflet';
import * as L from 'leaflet';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { NgApexchartsModule } from 'ng-apexcharts';

@Component({
  selector: 'app-widgets',
  standalone: true,
  imports: [SharedModule,NgApexchartsModule,LeafletModule,HttpClientModule],
  templateUrl: './widgets.component.html',
  styleUrl: './widgets.component.scss'
})
export class WidgetsComponent {
  chartOptions:any
  chartOptions1:any
  chartOptions2:any
  chartOptions3:any
  chartOptions4:any
  chartOptions5:any
  chartOptions6:any
  chartOptions7:any

  constructor(){
    this.chartOptions={
      series: [
        {
          data: [34, 55, 41, 67, 22, 43, 21]
        },
      ],
      color: ['#47bbed'],

      chart: {
        events: {
          mounted: (chart:any) => {
            chart.windowResizeHandler();
          }
        },
        sparkline: {
          enabled: true
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 3,
          blur: 3,
          opacity: 0.2
        },
        type: 'line',
        height: 20,
        width: 100
      },
      tooltip: {
        x: {
          show: false
        },
        y: {
          title: {
            formatter: function () {
              return '';
            }
          }
        },
        marker: {
          show: false
        }
      },
      colors: ["#47bbed"],
      stroke: {
        width: [1.5],
        curve: ['smooth'],
      },
      xaxis: {
        crosshairs: {
          show: false,
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          opacityFrom: 0.9,
          opacityTo: 0.9,
          stops: [0, 98],
        }
      },
    }
    this.chartOptions1={
      series: [
        {
          data: [34, 55, 41, 47, 32, 53, 31]
        },
      ],
      color: ['#638aba'],

      chart: {
        events: {
          mounted: (chart:any) => {
            chart.windowResizeHandler();
          }
        },
        sparkline: {
          enabled: true
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 3,
          blur: 3,
          opacity: 0.2
        },
        type: 'line',
        height: 20,
        width: 100
      },
      tooltip: {
        x: {
          show: false
        },
        y: {
          title: {
            formatter: function () {
              return '';
            }
          }
        },
        marker: {
          show: false
        }
      },
      colors: ["#28D193"],
      stroke: {
        width: [1.5],
        curve: ['smooth'],
      },
      xaxis: {
        crosshairs: {
          show: false,
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          opacityFrom: 0.9,
          opacityTo: 0.9,
          stops: [0, 98],
        }
      },
    }
    this.chartOptions2={
      series: [
        {
          data: [31, 53, 32, 47, 41, 55, 44]
        },
      ],
      color: ['#FF534D'],
      chart: {
        events: {
          mounted: (chart:any) => {
            chart.windowResizeHandler();
          }
        },
        sparkline: {
          enabled: true
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 3,
          // right: 6,
          blur: 3,
          opacity: 0.2
        },
        type: 'line',
        height: 20,
        width: 100
      },
      tooltip: {
        x: {
          show: false
        },
        y: {
          title: {
            formatter: function () {
              return '';
            }
          }
        },
        marker: {
          show: false
        }
      },
      colors: ["#FF534D"],
      stroke: {
        width: [1.5],
        curve: ['smooth'],
      },
      xaxis: {
        crosshairs: {
          show: false,
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          opacityFrom: 0.9,
          opacityTo: 0.9,
          stops: [0, 98],
        }
      },
    }
    this.chartOptions3={
      series: [
        {
          data: [21, 43, 22, 45, 35, 55, 34]
        },
      ],
      color: ['#FFBE14'],
      chart: {
        events: {
          mounted: (chart:any) => {
            chart.windowResizeHandler();
          }
        },
        sparkline: {
          enabled: true
        },
        dropShadow: {
          enabled: true,
          enabledOnSeries: undefined,
          top: 3,
          // right: 6,
          blur: 3,
          opacity: 0.2
        },
        type: 'line',
        height: 20,
        width: 100
      },
      tooltip: {
        x: {
          show: false
        },
        y: {
          title: {
            formatter: function () {
              return '';
            }
          }
        },
        marker: {
          show: false
        }
      },
      colors: ["#FFBE14"],
      stroke: {
        width: [1.5],
        curve: ['smooth'],
      },
      xaxis: {
        crosshairs: {
          show: false,
        }
      },
      fill: {
        type: 'gradient',
        gradient: {
          opacityFrom: 0.9,
          opacityTo: 0.9,
          stops: [0, 98],
        }
      },
    }
    this.chartOptions4={
      series: [{
        name: "Revenue",
        data: [55, 55, 52, 52, 55, 55, 58, 58, 53, 53, 55, 55],
        colors: ["#60a5fa"],

      }],
  
        chart: {
          events: {
            mounted: (chart:any) => {
              chart.windowResizeHandler();
            }
          },
          height: 180,
          type: "area",
          sparkline: {
            enabled: true
          }
        },
        dataLabels: {
          enabled: false
        },
        stroke: {
          width: [1.4],
          show: true,
          curve: ['smooth'],
        },
        xaxis: {
          crosshairs: {
            show: false,
          }
        },
        legend: {
          show: false
        },
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        markers: {
          size: 0
        },
        colors: ["#81b8fb"],
        fill: {
          type: 'gradient',
          gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.4,
            opacityTo: 0.7,
            stops: [0, 100]
          }
        },
    }
    this.chartOptions5={
      series: [{
        name: 'Job Applied',
        type: 'line',
        data: [25, 50, 30, 55, 20, 45, 30]
      }, {
        name: 'Job Viewed',
        type: 'area',
        data: [35, 25, 40, 30, 45, 35, 60]
      }],
      
        colors: ["#845adf", "rgba(132, 90, 223, 0.1)"],
        chart: {
          events: {
            mounted: (chart:any) => {
              chart.windowResizeHandler();
            }
          },
          height: 348,
          type: 'line',
          stacked: false,
          toolbar: {
            show: false
          },
          dropShadow: {
            enabled: true,
            enabledOnSeries: undefined,
            top: 7,
            left: 1,
            blur: 3,
            color: '#000',
            opacity: 0.2
          },
        },
        grid: {
          borderColor: '#e9edf4',
          padding: {
            top: 10,
            right: 0,
            bottom: 0,
            left: 0
          },
        },
        stroke: {
          width: [2, 2],
          curve: 'smooth',
          dashArray: [0, 4]
        },
        labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        markers: {
          size: 4,
          hover: {
            size: 5
          }
        },
        fill: {
          opacity: [0.85, 0.25, 1],
          gradient: {
            inverseColors: false,
            shadeIntensity: 1,
            shade: 'light',
            type: "vertical",
            opacityFrom: 0.85,
            opacityTo: 0.55,
            stops: [0, 100, 100, 100]
          }
        },
        legend: {
          show: true,
          position: 'top',
          fontFamily: 'Inter, sans-serif',
          markers: {
            width: 10,
            height: 10,
          }
        },
        xaxis: {
          // type: 'week',
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
            // width: 6,
            offsetX: 0,
            offsetY: 0
          },
          labels: {
            rotate: -90
          }
        },
        yaxis: {
          title: {
            style: {
              color: '#adb5be',
              fontSize: '14px',
              fontFamily: 'Inter, sans-serif',
              fontWeight: 600
            },
          },
          labels: {
            formatter: function (y: number) {
              return y.toFixed(0) + "";
            }
          }
        },
        tooltip: {
          shared: true,
          intersect: false,
          y: {
            formatter: function (y: number) {
              if (typeof y !== "undefined") {
                return y.toFixed(0) + " points";
              }
              return y;

            }
          }
        }
  }
  this.chartOptions6={
    series: [
      {
        name: "Tablet",
        data: [[10, 35, 80]]
      },
      {
        name: "Mobile",
        data: [[22, 10, 80]]
      },
      {
        name: "Desktop",
        data: [[25, 25, 150]]
      },
      
    ],
    
    chart: {
      events: {
        mounted: (chart:any) => {
          chart.windowResizeHandler();
        }
      },
      height: 350,
      type: "bubble",
      toolbar: {
        show: false
      }
    },
    grid: {
      borderColor: '#f3f3f3',
      strokeDashArray: 3
    },
    colors: ["#f65c7a", "#78b2fb", "#7a7df3"],
    dataLabels: {
      enabled: false
    },
    legend: {
      show: true,
      fontSize: '13px',
      labels: {
        colors: '#959595',
      },
      markers: {
        width: 10,
        height: 10,
      },
    },
    xaxis: {
      min: 0,
      max: 50,
      labels: {
        show: false,
      },
      axisBorder: {
        show: false,
      },
    },
    yaxis: {
      max: 50,
      labels: {
        show: false,
      },
    }
}
this.chartOptions7={
  series: [{
    data: [17, 22, 37, 47, 39, 28, 14],
    name: 'Revenue',
  }],
  chart: {
    events: {
      mounted: (chart:any) => {
        chart.windowResizeHandler();
      }
    },
    type: 'bar',
    height: 235,
    toolbar: {
      show: false
    },
    dropShadow: {
      enabled: true,
      enabledOnSeries: undefined,
      top: 6,
      left: 6,
      blur: 3,
      color: '#000',
      opacity: 0.05
    },
  },
  plotOptions: {
    bar: {
      columnWidth: '35%',
      borderRadius: 4,
      horizontal: false,
      colors: {
        ranges: [{
          from: 41,
          to: Infinity,
          color: '#5f40a3'
        },
        {
          from: 0,
          to: 40,
          color: '#e4dcf8'
        }]
      },
    }
  },
  dataLabels: {
    enabled: false
  },
  grid: {
    show: false,
    borderColor: 'transparent',
    padding: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    },
    yaxis: {
      lines: {
        show: false
      }
    },
  },
  xaxis: {
    categories: ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    axisBorder: {
      show: false
    },
    axisTicks: {
      show: false
    },
    labels: {
      rotate: -90,
      style: {
        fontFamily: 'Inter, sans-serif',
      },
    }
  },
  yaxis: {
    axisBorder: {
      show: false
    },
    axisTicks: {
      show: false
    },
    labels: {
      show: false
    }
  }
}
}

      // maps
      map!: L.Map;
      json:any;
      options1 = {
        layers: [
          L.tileLayer("http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: ""
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
}
