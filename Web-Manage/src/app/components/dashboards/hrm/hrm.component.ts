import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Renderer2 } from '@angular/core';
import { RouterModule } from '@angular/router';
import  ApexCharts from 'apexcharts';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../shared/shared.module';
@Component({
  selector: 'app-hrm',
  standalone: true,
  imports: [RouterModule,SharedModule,NgApexchartsModule],
  templateUrl: './hrm.component.html',
  styleUrls: ['./hrm.component.scss']
})
export class HrmComponent  {

  optionsCircle1:any
  chartOptions:any
  constructor(private el: ElementRef, private renderer: Renderer2,private cdr: ChangeDetectorRef){
    this.optionsCircle1 = {
        series: [1754, 544, 682, 263],
        labels: ["Published", "Private", "Closed", "On Hold"],
        chart: {
           
            height: 250,
            type: 'donut',
          
        },
        dataLabels: {
            enabled: false,
        },
    
        legend: {
            show: false,
        },
        stroke: {
            show: true,
            curve: 'smooth',
            lineCap: 'round',
            colors: "#fff",
            width: 0,
            dashArray: 0,
        },
        plotOptions: {
    
            pie: {
                expandOnClick: false,
                donut: {
                    size: '70%',
                    background: 'transparent',
                    labels: {
                        show: true,
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
                                return val + "%"
                            }
                        },
                        total: {
                            show: true,
                            showAlways: true,
                            label: 'Total',
                            fontSize: '22px',
                            fontWeight: 600,
                            color: '#495057',
                        }
    
                    }
                }
            }
        },
        colors: ["rgb(132, 90, 223)", "rgba(132, 90, 223, 0.7)", "rgba(132, 90, 223,0.4)", "rgba(243, 246, 248, 0.1)"], 
    }
 
  this.chartOptions= {
    series: [{
      name: 'Designing',
      data: [44, 55, 41, 67, 22, 43, 44, 55, 41, 67, 22, 43]
  }, {
      name: 'Development',
      data: [13, 23, 20, 8, 13, 27, 13, 23, 20, 8, 13, 27]
  }, {
      name: 'SEO',
      data: [11, 17, 15, 15, 21, 14, 11, 17, 15, 15, 21, 14]
  }],
  chart: {
   
    type: 'bar',
    height: 310,
    stacked: true,
    toolbar: {
        show: true
    },
    zoom: {
        enabled: true
    }
},
grid: {
    borderColor: '#f1f1f1',
    strokeDashArray: 3
},
responsive: [{
    breakpoint: 480,
    options: {
        legend: {
            position: 'bottom',
            offsetX: -10,
            offsetY: 0
        }
    }
}],
colors: ["rgba(132, 90, 223, 1)", "rgba(132, 90, 223, 0.5)", "rgba(132, 90, 223, 0.2)"],
legend: {
    show: false,
    position: 'top'
},
plotOptions: {
    bar: {
        columnWidth: "20%",
    }
},
dataLabels: {
    enabled: false
},
xaxis: {
    categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
},
fill: {
    opacity: 1
}
}

}
  
ngAfterViewInit(): void {
      this.setChartWidth();
    this.cdr.detectChanges();
  }
  
    private setChartWidth(): void {
        const chartContainer = this.el.nativeElement.querySelector('.chart-container');
        const chartContainer1 = this.el.nativeElement.querySelector('.chart-container1');
        const chart = new ApexCharts(chartContainer, this.chartOptions);
        const chart1 = new ApexCharts(chartContainer1, this.optionsCircle1);
        chart.render();
        chart1.render();
      
      }
  }
  

