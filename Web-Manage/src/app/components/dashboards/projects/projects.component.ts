import { AfterViewInit, Component, ElementRef, Renderer2 } from '@angular/core';
import { RouterModule } from '@angular/router';
import ApexCharts from 'apexcharts';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../shared/shared.module';
@Component({
  selector: 'app-projects',
    standalone: true,
  imports: [RouterModule,SharedModule,NgApexchartsModule],
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.scss']
})
export class ProjectsComponent  {
  chartOptions1:any
  chartOptions2:any
  chartOptions3:any
  chartOptions4:any
  chartOptions5:any
  chartOptions:any



  constructor(private el: ElementRef, private renderer: Renderer2,){
    this.chartOptions1 = {
      series: [{
        name: 'Value',
        data: [54, 38, 56, 24, 65]
    }],
    chart: {
     
      type: 'line',
      height: 20,
      width: 80,
      sparkline: {
          enabled: true
      },
      dropShadow: {
          enabled: true,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      }
  },
  grid: {
      show: false,
      xaxis: {
          lines: {
              show: false
          }
      },
      yaxis: {
          lines: {
              show: false
          }
      },
  },
  stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
  },


  yaxis: {
      min: 0,
      show: false,
      axisBorder: {
          show: false
      },
  },
  xaxis: {
      axisTicks: {
          show: false
      },
      axisBorder: {
          show: false
      }
  },
  colors: ['#09ad95'],
    };
    this.chartOptions2 = {
      series: [{
        name: 'Value',
        data: [24, 54, 15, 42, 16]
      }],
    chart: {
      type: 'line',
      height: 20,
      width: 80,
      sparkline: {
          enabled: true
      },
      dropShadow: {
          enabled: true,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      }
  },
  grid: {
      show: false,
      xaxis: {
          lines: {
              show: false
          }
      },
      yaxis: {
          lines: {
              show: false
          }
      },
  },
  stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
  },


  yaxis: {
      min: 0,
      show: false,
      axisBorder: {
          show: false
      },
  },
  xaxis: {
      axisTicks: {
          show: false
      },
      axisBorder: {
          show: false
      }
  },
  colors: ['#fb6b27'],
};
    this.chartOptions3 = {
      series: [{
        name: 'Value',
        data: [15, 42, 16, 44, 24]
      }],
    chart: {
      type: 'line',
      height: 20,
      width: 80,
      sparkline: {
          enabled: true
      },
      dropShadow: {
          enabled: true,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      }
  },
  grid: {
      show: false,
      xaxis: {
          lines: {
              show: false
          }
      },
      yaxis: {
          lines: {
              show: false
          }
      },
  },
  stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
  },


  yaxis: {
      min: 0,
      show: false,
      axisBorder: {
          show: false
      },
  },
  xaxis: {
      axisTicks: {
          show: false
      },
      axisBorder: {
          show: false
      }
  },
  colors: ['#1170e4'],
};
    this.chartOptions4 = {
      series: [{
        name: 'Value',
        data: [54, 38, 56, 24, 65]
      }],
    chart: {
      type: 'line',
      height: 20,
      width: 80,
      sparkline: {
          enabled: true
      },
      dropShadow: {
          enabled: true,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      }
  },
  grid: {
      show: false,
      xaxis: {
          lines: {
              show: false
          }
      },
      yaxis: {
          lines: {
              show: false
          }
      },
  },
  stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
  },


  yaxis: {
      min: 0,
      show: false,
      axisBorder: {
          show: false
      },
  },
  xaxis: {
      axisTicks: {
          show: false
      },
      axisBorder: {
          show: false
      }
  },
  colors: ['#fb6b27'],
};
    this.chartOptions5 = {
      series: [{
        name: 'Value',
        data: [15, 42, 16, 44, 24]
      }],
    chart: {
      
      type: 'line',
      height: 20,
      width: 80,
      sparkline: {
          enabled: true
      },
      dropShadow: {
          enabled: true,
          top: 0,
          left: 0,
          blur: 3,
          color: '#000',
          opacity: 0.1
      }
  },
  grid: {
      show: false,
      xaxis: {
          lines: {
              show: false
          }
      },
      yaxis: {
          lines: {
              show: false
          }
      },
  },
  stroke: {
      show: true,
      curve: 'smooth',
      lineCap: 'butt',
      width: 1.5,
      dashArray: 0,
  },


  yaxis: {
      min: 0,
      show: false,
      axisBorder: {
          show: false
      },
  },
  xaxis: {
      axisTicks: {
          show: false
      },
      axisBorder: {
          show: false
      }
  },
  colors: ['#f7b731'],
};
this.chartOptions = {
  series: [
    {
      name: 'Projects',
      type: 'column',
      data: [1.8, 2.5, 2.5, 1.5, 2.5, 2.8, 3.8],
    },
    {
      name: 'Tasks',
      type: 'column',
      data: [1.1, 2.2, 3.1, 4, 4.1, 4.9, 6.5],
    },
    {
      name: 'Revenue',
      type: 'line',
      data: [20, 29, 37, 35, 44, 43, 50],
    },
    
  ],
  chart: {
    toolbar: {
      show: false,
    },
    height: 320,
    type: 'line',
    stacked: false,
    fontFamily: 'Poppins, Arial, sans-serif',
  },
  grid: {
    borderColor: '#f5f4f4',
    strokeDashArray: 3,
  },
  dataLabels: {
    enabled: false,
  },

  xaxis: {
    categories: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  },
  yaxis: [
    {
      show: true,
   
    },
    {
      seriesName: 'Projects',
      opposite: true,
      axisTicks: {
        show: true,
      },
      axisBorder: {
        show: false,
      },
      labels: {
        style: {
          colors: '#00E396',
        },
      },
     
    },
    {
      seriesName: 'Revenue',
      opposite: true,
      axisTicks: {
        show: true,
      },
      axisBorder: {
        show: false,
      },
      labels: {
        show: false,
      },
   
    },
  ],
  tooltip: {
    enabled: true,
  },
  legend: {
    show: true,
    position:'top'
  },
  stroke: {
    width: [0, 0, 1.5],
    curve: 'straight',
    dashArray: [0, 0, 0],
  },
  plotOptions: {
    bar: {
      columnWidth: '35%',
      borderRadius: 3,
    },
    
  },
  colors: ["rgb(132, 90, 223)", "#ededed", "#23b7e5"]
 
};
  }
  
 
  
}

