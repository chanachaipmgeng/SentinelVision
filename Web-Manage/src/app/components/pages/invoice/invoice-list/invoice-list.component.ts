import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../../../shared/shared.module';
import { NgApexchartsModule } from 'ng-apexcharts';
import { CountUpModule } from 'ngx-countup';
const DATA=[
  {
    img:"./assets/images/faces/11.jpg",
    name:'ชนะชัย โอดพิมพ์',
    mail:'jsontaylor2416@gmail.com',
    id:'#SPK12032901',
    issueDate:'25,Nov 2022',
    price:'$212.45',
    bg:'success/10',
    text:'success',
    status:'Paid',
    dueDate:'25,Dec 2022'
  },
  {
    img:"./assets/images/faces/7.jpg",
    name:'Suzika Stallone',
    mail:'suzikastallone3214@gmail.com',
    id:'#SPK12032912',
    issueDate:'13,Nov 2022',
    price:'$512.99',
    bg:'warning/10',
    text:'warning',
    status:'Pending',
    dueDate:'13,Dec 2022'
  },
  {
    img:"./assets/images/faces/15.jpg",
    name:'Roman Killon',
    mail:'romankillon143@gmail.com',
    id:'#SPK12032945',
    issueDate:'30,Nov 2022',
    price:'$2199.49',
    bg:'danger/10',
    text:'danger',
    status:'Overdue',
    dueDate:'30,Dec 2022'
  },
  {
    img:"./assets/images/faces/12.jpg",
    name:'Charlie Davieson',
    mail:'charliedavieson@gmail.com',
    id:'#SPK12032922',
    issueDate:'18,Nov 2022',
    price:' $1569.99',
    bg:'success/10',
    text:'success',
    status:'Paid',
    dueDate:'18,Dec 2022'
  },
  {
    img:"./assets/images/faces/4.jpg",
    name:'Selena Deoyl',
    mail:'selenadeoyl114@gmail.com',
    id:'#SPK12032932',
    issueDate:'18,Nov 2022',
    price:'  $4,873.99',
    bg:'primary/10',
    text:'primary',
    status:'Due By 1 Day',
    dueDate:'18,Dec 2022'
  },
  {
    img:"./assets/images/faces/7.jpg",
    name:'Kiara Advensh',
    mail:'kiaraadvensh87@gmail.com',
    id:'#SPK12032978',
    issueDate:'02,Nov 2022',
    price:'  $1923.99',
    bg:'success/10',
    text:'success',
    status:'Paid',
    dueDate:'18,Dec 2022'
  },
  {
    img:"./assets/images/faces/9.jpg",
    name:'Joseph Samurai',
    mail:'josephsamurai@gmail.com',
    id:'#SPK12032919',
    issueDate:'15,Nov 2022',
    price:'$1,623.99',
    bg:'success/10',
    text:'success',
    status:'Paid',
    dueDate:'15,Dec 2022'
  },
  {
    img:"./assets/images/faces/13.jpg",
    name:'Kevin Powell',
    mail:'kevinpowell@gmail.com',
    id:'#SPK12032931',
    issueDate:'21,Nov 2022',
    price:' $3,423.99',
    bg:'warning/10',
    text:'warning',
    status:'Pending',
    dueDate:'21,Dec 2022'
  },
  {
    img:"./assets/images/faces/8.jpg",
    name:'Darla Jung',
    mail:'darlajung555&@gmail.com',
    id:'#SPK12032958',
    issueDate:'15,Oct 2022',
    price:' $2,982.99',
    bg:'success/10',
    text:'success',
    status:'Paid',
    dueDate:'15,Nov 2022'
  }
]
@Component({
  selector: 'app-invoice-list',
  standalone: true,
  imports: [SharedModule,NgApexchartsModule,CountUpModule,CommonModule],
  templateUrl: './invoice-list.component.html',
  styleUrl: './invoice-list.component.scss'
})
export class InvoiceListComponent {
  click(id:string){
    const data = this.invoices.filter((x: { id: string }) => {
      return x.id != id;

    })
    this.invoices = data;

}
invoices=DATA;
chartOptions:any
constructor() {
  this.chartOptions = {
    series: [
      {
        name: 'Total',
        data: [76, 85, 101, 98, 87, 105],
      },
      {
        name: 'Paid',
        data: [35, 41, 36, 26, 45, 48],
      },
      {
        name: 'Pending',
        data: [44, 55, 57, 56, 61, 58],
      },
      {
        name: 'Overdue',
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
    colors: ['#4b9bfa', '#28d193', '#ffbe14', '#f3f6f8'],
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
    tooltip: {
      y: {
        formatter: function (val: string) {
          return '$ ' + val + ' thousands';
        },
      },
    },
  };
}
}
