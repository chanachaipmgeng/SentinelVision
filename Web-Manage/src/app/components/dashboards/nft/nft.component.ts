import { ChangeDetectorRef, Component, ElementRef, OnInit, Renderer2 } from '@angular/core';
import { RouterModule } from '@angular/router';
import { NgApexchartsModule } from 'ng-apexcharts';
import  ApexCharts from 'apexcharts';
import { CarouselModule, OwlOptions, SlidesOutputData } from 'ngx-owl-carousel-o';
import { fromEvent } from 'rxjs';
import { SharedModule } from '../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';
import { CommonModule, NgFor } from '@angular/common';

@Component({
  selector: 'app-nft',
  standalone: true,
  imports: [RouterModule,SharedModule,NgApexchartsModule,CarouselModule,SimplebarAngularModule,CommonModule],
  templateUrl: './nft.component.html',
  styleUrls: ['./nft.component.scss'],
  animations:[]
})
export class NftComponent implements OnInit {
  chartOptions:any;
  chartOptions1:any
  constructor(private elementRef: ElementRef,private el: ElementRef, private renderer: Renderer2,private cdr: ChangeDetectorRef) {
    this.chartOptions = {
      series: [{
        name: "Price",
        data: [20, 38, 38, 72, 55, 63, 43, 76, 55, 80, 40, 80]
    }, {
        name: "Volume",
        data: [85, 65, 75, 38, 85, 35, 62, 40, 40, 64, 50, 89]
    }],
      chart: {
        height: 338,
        type: 'line',
        zoom: {
            enabled: false
        },
        
        dropShadow: {
            enabled: true,
            top: 5,
            left: 0,
            blur: 3,
            color: '#000',
            opacity: 0.1
        },
    },
    dataLabels: {
        enabled: false
    },
    legend: {
        position: "top",
        horizontalAlign: "center",
        offsetX: -15,
        fontWeight: "bold",
    },
    stroke: {
        curve: 'smooth',
        dashArray: [0, 5],
        width:2.5
    },
    grid: {
        borderColor: '#f2f6f7',
    },
    colors: ["rgb(132, 90, 223)", "rgba(132, 90, 223, 0.3)"],
    yaxis: {
        title: {
            text: 'Statistics',
            style: {
                color: '#adb5be',
                fontSize: '14px',
                fontFamily: 'poppins, sans-serif',
                fontWeight: 600,
                cssClass: 'apexcharts-yaxis-label',
            },
        },
     
    },
    xaxis: {
        categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
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
            offsetX: 0,
            offsetY: 0
        },
        labels: {
            rotate: -90
        }
    }
    };
    this.chartOptions1 = {
      chart: {
        type: 'line',
        height: 80,
        sparkline: {
          enabled: true,
        },
       
      },
      stroke: {
        show: true,
        curve: 'smooth',
        lineCap: 'butt',
        width: 2.5,
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
          data: [20, 14, 19, 10, 25, 20, 22, 9, 12],
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
      colors: ['rgb(132, 90, 223)'],
    };
  }
  customOptions: OwlOptions = {
    loop: true,
    rtl: false,
    mouseDrag: true,
    touchDrag: true,
    pullDrag: false,
    dots: false,
    navSpeed: 8000,
    autoplay: true,
    autoplayTimeout: 5000,
    autoplayHoverPause: false,
    navText: ['', ''],
    responsive: {
      0: {
        items: 1,
      },
      400: {
        items: 1,
      },
      740: {
        items: 1,
      },
      940: {
        items: 1,
      },
    },
    nav: false,
  };

  activeSlides!: SlidesOutputData;

  slidesStore: any[] = [
    {
      src: './assets/images/nft-images/6.png',
      src1: './assets/images/nft-images/7.png',
      src2: './assets/images/nft-images/8.png',
      src3: './assets/images/nft-images/9.png',
      Rank: '#1',
      value: '1.0979ETH',
      src4: './assets/images/faces/9.jpg',
      name: 'Simon Cowell',
      mail: '@sman',
    },
    {
      src: './assets/images/nft-images/10.png',
      src1: './assets/images/nft-images/15.png',
      src2: './assets/images/nft-images/17.png',
      src3: './assets/images/nft-images/16.png',
      Rank: '#2',
      value: '1.0466ETH',
      src4: './assets/images/faces/5.jpg',
      name: 'Melissa Smith',
      mail: '@sman',
    },
    {
      src: './assets/images/nft-images/8.png',
      src1: './assets/images/nft-images/9.png',
      src2: './assets/images/nft-images/10.png',
      src3: './assets/images/nft-images/11.png',
      Rank: '#3',
      value: '1.0355ETH',
      src4: './assets/images/faces/10.jpg',
      name: 'Json Talor',
      mail: '@sman',
    },
  ];

  getPassedData(data: SlidesOutputData) {
    this.activeSlides = data;
  }
  ngOnInit(): void {
    const ltr = this.elementRef.nativeElement.querySelectorAll('#switcher-ltr');
    const rtl = this.elementRef.nativeElement.querySelectorAll('#switcher-rtl');

    fromEvent(ltr, 'click').subscribe(() => {
      this.customOptions = { ...this.customOptions, rtl: false };
    });

    fromEvent(rtl, 'click').subscribe(() => {
      this.customOptions = { ...this.customOptions, rtl: true, autoplay: true };
    });
  }
  
  
  // ngAfterViewInit(): void {
  //     this.setChartWidth();
  //   this.cdr.detectChanges();
  // }
  

  // private setChartWidth(): void {
  //   const chartContainer = this.el.nativeElement.querySelector('.chart-container');
  //   const chart = new ApexCharts(chartContainer, this.chartOptions);
  
  //   chart.render();
  //   const chartContainer1 = this.el.nativeElement.querySelector('.chart-container1');
  //   const chart1 = new ApexCharts(chartContainer1, this.chartOptions1);
  
  //   chart1.render();
  
  // }
  
}
