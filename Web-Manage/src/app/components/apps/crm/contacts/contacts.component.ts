import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
const DATA=[
  {
    id:'1',
    img:"./assets/images/faces/4.jpg",
    name:'Lisa Convay',
    date:'24, Jul 2023 - 4:45PM',
    deals:'258',
    mail:'lisaconvay2981@gmail.com',
    number:'1678-28993-223',
    img2:'./assets/images/company-logos/1.png',
    company:'Spruko Technologies',
    source:'Social Media',
    bg:'primary/10',
    text:'primary',
    bg2:'primary/10',
    text2:'primary',
    tag1:'New Lead',
    tag2:'Prospect',
  },
  {
    id:'2',
    img:"./assets/images/faces/12.jpg",
    name:'Jacob Smith',
    date:'15, Jul 2023 - 11:45AM',
    deals:'335',
    mail:'jacobsmith289@gmail.com',
    number:'8122-2342-4453',
    img2:'./assets/images/company-logos/3.png',
    company:'Spice Infotech',
    source:'Direct mail',
    bg:'primary/10',
    text:'primary',
    bg2:'danger/10',
    text2:'danger',
    tag1:'Customer',
    tag2:'Hot Lead'
  },
  {
    id:'3',
    img:"./assets/images/faces/14.jpg",
    name:'Jake Sully',
    date:'10, Aug 2023 - 3:25PM',
    deals:'685',
    mail:'jakesully789@gmail.com',
    number:'1902-2001-3023',
    img2:'./assets/images/company-logos/4.png',
    company:'Logitech ecostics',
    source:'Blog Articles',
    bg:'success/10',
    text:'success',
    tag1:'Partner',
  },
  {
    id:'4',
    img:"./assets/images/faces/6.jpg",
    name:'Kiara Advain',
    date:'18, Aug 2023 - 10:10AM',
    deals:'425',
    mail:'kiaraadvain290@gmail.com',
    number:'1603-2032-1123',
    img2:'./assets/images/company-logos/5.png',
    company:'Initech Info',
    source:'Affiliates',
    bg:'light',
    text:'defaulttextcolor',
    tag1:'LostCustomer',
    tag2:'Influencer',
    bg2:'secondary/10',
    text2:'secondary',

  },
  {
    id:'5',
    img:"./assets/images/faces/8.jpg",
    name:'Brenda Simpson',
    date:'19, Jul 2023 - 12:41PM',
    deals:'516',
    mail:'brendasimpson1993@gmail.com',
    number:'1129-2302-1092',
    img2:'./assets/images/company-logos/5.png',
    company:'Massive Dynamic',
    source:'Organic search',
    bg:'pink/10',
    text:'pink',
    tag1:'Subscriber',
    tag2:'Influencer',
    bg2:'success/10',
    text2:'success',

  },
  {
    id:'6',
    img:"./assets/images/faces/9.jpg",
    name:'ชนะชัย โอดพิมพ์',
    date:'14, Aug 2023 - 5:18PM',
    deals:'127',
    mail:'jsontaylor345@gmail.com',
    number:'9923-2344-2003',
    img2:'./assets/images/company-logos/7.png',
    company:'Globex Corporation',
    source:'Social media',
    bg:'danger/10',
    text:'danger',
    tag1:'Hot Lead',
    tag2:'Referral',
    bg2:'info/10',
    text2:'info',
  },
  {
    id:'7',
    img:"./assets/images/faces/15.jpg",
    name:'Dwayne Jhonson',
    date:'12, Jun 2023 - 11:38AM',
    deals:'368',
    mail:'dwayenejhonson78@gmail.com',
    number:'7891-2093-1994',
    img2:'./assets/images/company-logos/8.png',
    company:'Acme Corporation',
    source:'Blog Articles',
    bg:'warning/10',
    text:'warning',
    tag1:'Trial User',
    tag2:'Cold Lead',
    bg2:'purple/10',
    text2:'purple',
  },
  {
    id:'8',
    img:"./assets/images/faces/1.jpg",
    name:'Emiley Jackson',
    date:'19, May 2023 - 1:57PM',
    deals:'563',
    mail:'emileyjackson678@gmail.com',
    number:'1899-2993-0923',
    img2:'./assets/images/company-logos/9.png',
    company:'Soylent Corp',
    source:'Organic search',
    bg:'success/10',
    text:'success',
    tag1:'Influencer',
    tag2:'Partner',
    bg2:'info/10',
    text2:'info',
  },
  {
    id:'9',
    img:"./assets/images/faces/3.jpg",
    name:'Jessica Morris',
    date:'28, Jul 2023 - 9:31AM',
    deals:'240',
    mail:'emileyjackson678@gmail.com',
    number:'1899-2993-0923',
    img2:'./assets/images/company-logos/10.png',
    company:'Umbrella Corporation',
    source:'Affiliates',
    bg:'primary/10',
    text:'primary',
    tag1:'New Lead',
    tag2:'Lost Customer',
    bg2:'light',
    text2:'default',
  },
  {
    id:'10',
    img:"./assets/images/faces/9.jpg",
    name:'Michael Jeremy',
    date:'28, Jul 2023 - 9:31AM',
    deals:'240',
    mail:'michaeljeremy186@gmail.com',
    number:'4788-7822-4786',
    img2:'./assets/images/company-logos/2.png',
    company:'Hooli Technologies',
    source:' Direct mail',
    bg:'primary/10',
    text:'primary',
    tag1:'New Lead',
    tag2:'Subscriber',
    bg2:'pink/10',
    text2:'pink',
  },
]
@Component({
  selector: 'app-contacts',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FlatpickrModule,FormsModule,ReactiveFormsModule],
  providers:[FlatpickrDefaults],
  templateUrl: './contacts.component.html',
  styleUrls: ['./contacts.component.scss']
})
export class ContactsComponent {
contacts=DATA;
click(id:string){
  const data=this.contacts.filter((x: { id: string }) => {
    return x.id != id;
  });
  this.contacts = data;
}
selectedTags=['Select Tag'];
  tags=[
    {id:1,name:'Kiara advain'},
    {id:2,name:'New Lead'},
    {id:3,name:'Prospect'},
    {id:4,name:'Customer'},
    {id:5,name:'Hot Lead'},
    {id:6,name:'Partner'},
    {id:7,name:'LostCustomer'},
    {id:8,name:'Influencer'},
    {id:9,name:'Subscriber'},
    {id:10,name:'Alex Carey'},

  ]

flatpickrOptions: any = {
  inline: true,
};
// flatpickrOptions: FlatpickrOptions;

constructor() {}

ngOnInit() {
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
url1:string = '';
handleFileInput(event: any): void {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.url1 = e.target.result;
    };
    reader.readAsDataURL(file);
  }
}
}

