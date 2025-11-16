import { Component } from '@angular/core';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { NgApexchartsModule } from 'ng-apexcharts';
import { NgSelectModule } from '@ng-select/ng-select';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
const DATA=[
  {
    name:'Design New Landing Page',
    id:'SPK - 01',
    date:' 02-06-2023',
    status:'New',
    dueDate:' 10-06-2023',
    prority:'Medium',
    bg:'primary',
    bg1:'secondary',
    text:'secondary',
    images:[

     "./assets/images/faces/2.jpg",
     "./assets/images/faces/8.jpg",
    "./assets/images/faces/2.jpg",
    ],
    number:' +2'
  },
  {
    name:'New Project Buleprint',
    id:'SPK - 04',
    date:' 05-06-2023',
    status:'Inprogress',
    dueDate:' 15-06-2023',
    prority:'High',
    bg:'secondary',
    bg1:'danger',
    text:'danger',
    images:[
      "./assets/images/faces/12.jpg",
      "./assets/images/faces/11.jpg",
     ],
    number:' +4'
  },
  {
    name:'Server Side Validation',
    id:'SPK - 11',
    date:' 12-06-2023',
    status:'Pending',
    dueDate:' 16-06-2023',
    prority:'Low',
    bg:'warning',
    bg1:'success',
    text:'success',
    images:[
      "./assets/images/faces/5.jpg",
      "./assets/images/faces/9.jpg",
      "./assets/images/faces/13.jpg",

     ],
    number:' +5'
  },
  {
    name:'New Plugin Development',
    id:'SPK - 24',
    date:' 08-06-2023',
    status:'Completed',
    dueDate:' 17-06-2023',
    prority:'Low',
    bg:'success',
    bg1:'success',
    text:'success',
    images:[
      "./assets/images/faces/2.jpg",
      "./assets/images/faces/8.jpg",
      "./assets/images/faces/2.jpg",

     ],
    number:'+2'
  },
  {
    name:'Designing New Authentication Page',
    id:'SPK - 16',
    date:' 03-06-2023',
    status:'Inprogress',
    dueDate:'  08-06-2023',
    prority:'Medium',
    bg:'secondary',
    bg1:'secondary',
    text:'secondary',
    images:[
      "./assets/images/faces/10.jpg",
      "./assets/images/faces/15.jpg",

     ],
    number:'+3'
  },
  {
    name:'Documentation For New Template',
    id:'SPK - 07',
    date:' 12-06-2023',
    status:'New',
    dueDate:'  25-06-2023',
    prority:'High',
    bg:'primary',
    bg1:'danger',
    text:'danger',
    images:[
      "./assets/images/faces/12.jpg",

     ],
     number:'+1'

  },
  {
    name:'Updating Old UI',
    id:'SPK - 13',
    date:' 06-06-2023',
    status:'Completed',
    dueDate:'  12-06-2023',
    prority:'Low',
    bg:'success',
    bg1:'success',
    text:'success',
    images:[
      "./assets/images/faces/11.jpg",
      "./assets/images/faces/1.jpg",
      "./assets/images/faces/10.jpg",

     ],
     number:'+1'
  },
  {
    name:'Developing New Events In Plugins',
    id:'SPK - 20',
    date:' 14-06-2023',
    status:'Pending',
    dueDate:'  19-06-2023',
    prority:'High',
    bg:'warning',
    bg1:'danger',
    text:'danger',
    images:[
      "./assets/images/faces/3.jpg",
      "./assets/images/faces/9.jpg",

     ],
     number:'+2'
  },
]
@Component({
  selector: 'app-list-view',
  standalone: true,
  imports: [SharedModule,FlatpickrModule,NgApexchartsModule,NgSelectModule,MaterialModuleModule,FormsModule,ReactiveFormsModule],
  providers:[FlatpickrDefaults],
  templateUrl: './list-view.component.html',
  styleUrls: ['./list-view.component.scss']
})
export class ListViewComponent {
lists=DATA;
click(id:string){
  const data = this.lists.filter((x: { id: string }) => {
    return x.id != id;
  });
  this.lists = data;

}
chartOptions:any
constructor() {
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
      width:342,
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
selectedTags=['Angelina May'];
tags=[
  {id:1,name:'Angelina May'},
  {id:2,name:'Kiara advain'},
  {id:3,name:'Hercules Jhon'},
  {id:4,name:'Mayor Kim'},
  
]
flatpickrOptions: any = {
  inline: true,
};
ngOnInit(): void{

  this.flatpickrOptions = {
    enableTime: true,
    noCalendar: true,
    dateFormat: 'H:i',
  };

  flatpickr('#inlinetime', this.flatpickrOptions);

    this.flatpickrOptions = {
      enableTime: true,
      dateFormat: 'Y-m-d H:i', // Specify the format you want
      defaultDate: '2023-11-07 14:30', // Set the default/preloaded time (adjust this to your desired time)
    };

    flatpickr('#pretime', this.flatpickrOptions);
}
}
