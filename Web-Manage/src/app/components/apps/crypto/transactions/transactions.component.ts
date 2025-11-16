import { Component, ElementRef } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../../shared/shared.module';
import { CountUpModule } from 'ngx-countup';
const DATA=[
  {
    img:"./assets/images/faces/10.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'ชนะชัย โอดพิมพ์',
    id:'#1242232401',
    img2:"./assets/images/crypto-currencies/regular/Bitcoin.svg",
    coin:'Bitcoin',
    date:'24,Jul 2023 - 4:23PM',
    amount:'+0.041',
    text:'success',
    receiver:'Texas Steel',
    status:'Success',
     bg:"badge bg-success/10 text-success"
  },
  {
    img:"./assets/images/faces/5.jpg",
    class:"ti ti-arrow-narrow-down text-danger font-semibold text-[1rem]",
    name:'Samantha Taylor',
    id:'#1242232402',
    img2:"./assets/images/crypto-currencies/regular/Dash.svg",
    coin:'Dashcoin',
    date:'24,Jul 2023 - 4:23PM',
    amount:'-0.284',
    text:'danger',
    receiver:'Stuart Little',
    status:'Pending',
     bg:"badge bg-warning/10 text-warning"
  },
  {
    img:"./assets/images/faces/12.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Brian Jhonson',
    id:'#1242232403',
    img2:"./assets/images/crypto-currencies/regular/Euro.svg",
    coin:'Euro',
    date:'14,Aug 2023 - 10:25AM',
    amount:'+0.943',
    text:'success',
    receiver:'Melissa Smith',
    status:'Success',
     bg:"badge bg-success/10 text-success"
  },
  {
    img:"./assets/images/faces/15.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Liam Anderson',
    id:'#1242232404',
    img2:"./assets/images/crypto-currencies/regular/Ethereum.svg",
    coin:'Ethereum',
    date:'10,Jul 2023 - 4:14PM',
    amount:'+0.582',
    text:'success',
    receiver:'Alexander Clark',
    status:'Failed',
     bg:"badge bg-danger/10 text-danger"
  },
  {
    img:"./assets/images/faces/4.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Isabella Brown',
    id:'#1242232405',
    img2:"./assets/images/crypto-currencies/regular/Golem.svg",
    coin:'Golem',
    date:'19,Aug 2023 - 11:35AM',
    amount:'+0.290',
    text:'success',
    receiver:'Elijah Davis',
    status:'Success',
     bg:"badge bg-success/10 text-success"
  },
  {
    img:"./assets/images/faces/7.jpg",
    class:"ti ti-arrow-narrow-down text-danger font-semibold text-[1rem]",
    name:'Sophia Lee',
    id:'#1242232406',
    img2:"./assets/images/crypto-currencies/regular/litecoin.svg",
    coin:'Litecoin',
    date:'12,Jun 2023 - 2:45PM',
    amount:'-0.147',
    text:'danger',
    receiver:'Harper Taylor',
    status:'Success',
     bg:"badge bg-success/10 text-success"
  },
  {
    img:"./assets/images/faces/6.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Evelyn Clark',
    id:'#1242232407',
    img2:"./assets/images/crypto-currencies/regular/Ripple.svg",
    coin:'Ripple',
    date:'27,Jul 2023 - 10:18AM',
    amount:'+1.05',
    text:'success',
    receiver:'William Brown',
    status:'Success',
     bg:"badge bg-success/10 text-success"
  },
  {
    img:"./assets/images/faces/11.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Liam Anderson',
    id:'#1242232408',
    img2:"./assets/images/crypto-currencies/regular/monero.svg",
    coin:'Monero',
    date:'16,Aug 2023 - 9:25PM',
    amount:'+0.625',
    text:'success',
    receiver:'Amelia Davis',
    status:'Success',
     bg:"badge bg-info/10 text-info"
  },
  {
    img:"./assets/images/faces/2.jpg",
    class:"ti ti-arrow-narrow-down text-danger font-semibold text-[1rem]",
    name:'Harper Taylor',
    id:'#1242232409',
    img2:"./assets/images/crypto-currencies/regular/Zcash.svg",
    coin:'Zcash',
    date:'24,Jul 2023 - 12:47PM',
    amount:'-0.293',
    text:'danger',
    receiver:'Benjamin Martinez',
    status:'Inprogress',
     bg:"badge bg-info/10 text-info"
  },
  {
    img:"./assets/images/faces/16.jpg",
    class:"ti ti-arrow-narrow-up text-success font-semibold text-[1rem]",
    name:'Lucas Taylor',
    id:'#1242232410',
    img2:"./assets/images/crypto-currencies/regular/Decred.svg",
    coin:'Decred',
    date:'24,Jul 2023 - 12:47PM',
    amount:'+0.893',
    text:'success',
    receiver:'Benjamin Martinez',
    status:'Inprogress',
     bg:"badge bg-success/10 text-success"
  }
]
@Component({
  selector: 'app-transactions',
  standalone: true,
  imports: [SharedModule,NgSelectModule,NgApexchartsModule,CountUpModule],
  templateUrl: './transactions.component.html',
  styleUrls: ['./transactions.component.scss']
})
export class TransactionsComponent {
transactions=DATA;
click(id:string){
const data=this.transactions.filter((x:{id:string})=>{
  return x.id!=id
})
this.transactions=data;
}
chartOptions:any
constructor(private elementref:ElementRef) {
  this.chartOptions = {
    series: [
      {
        name: 'New',
        data: [76, 85, 101, 98, 87, 105],
      },
      {
        name: 'Pending',
        data: [35, 41, 36, 26, 45, 48],
      },
      {
        name: 'Completed',
        data: [44, 55, 57, 56, 61, 58],
      },
      {
        name: 'Inprogress',
        data: [13, 27, 31, 29, 35, 25],
      },
    ],
    chart: {
      type: 'bar',
      height: 210,
      stacked: true,

    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: '25%',
        endingShape: 'rounded',
      },
    },
    grid: {
      borderColor: '#f2f5f7',
    },
    dataLabels: {
      enabled: false,
    },
    colors: ['#845adf', '#28d193', '#ffbe14', '#23b7e5'],
    stroke: {
      show: true,
      colors: ['transparent'],
    },
    xaxis: {
      categories: ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'],
      labels: {
        show: true,
        style: {
          colors: '#8c9097',
          fontSize: '11px',
          fontWeight: 600,
          cssClass: 'apexcharts-xaxis-label',
        },
      },
    },
    yaxis: {
      title: {
        style: {
          color: '#8c9097',
        },
      },
      labels: {
        show: true,
        style: {
          colors: '#8c9097',
          fontSize: '11px',
          fontWeight: 600,
          cssClass: 'apexcharts-xaxis-label',
        },
      },
    },
    fill: {
      opacity: 1,
    },
  };
}
ngAfterViewInit(): void {
  this.setChartWidth();

}

private setChartWidth(): void {
  const chartContainer = this.elementref.nativeElement.querySelector('.chart-container');


  const chart1 = new ApexCharts(chartContainer, this.chartOptions);
  chart1.render();

}
}
