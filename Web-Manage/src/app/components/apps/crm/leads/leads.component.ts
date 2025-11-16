import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';
import { NgSelectModule } from '@ng-select/ng-select';
const DATA=[
  {
    id:'1',
    img:"./assets/images/faces/4.jpg",
    name:'Lisa Convay',
    mail:'lisaconvay2981&#64;gmail.com',
    number:'1678-28993-223',
    status:'New',
    img2:"./assets/images/company-logos/1.png",
    company:'Spruko Technologies',
    source:'Social Media',
    tag1:'New Lead',
    tag2:'Prospect',
    bg1:"badge bg-primary/10 text-primary",
    bg2:"badge bg-primary/10 text-primary"
  },
  {
    id:'2',
    img:"./assets/images/faces/12.jpg",
    name:'Jacob Smith',
    mail:'jacobsmith289&#64;gmail.com',
    number:'8122-2342-4453',
    status:'Follow-up',
    img2:"./assets/images/company-logos/3.png",
    company:'Spice Infotech',
    source:'Direct mail',
    tag1:'Customer',
    tag2:'Hot Lead',
    bg1:'badge bg-primary/10 text-primary',
    bg2:'badge bg-danger/10 text-danger'
  },
  {
    id:'3',
    img:"./assets/images/faces/14.jpg",
    name:'Jake Sully',
    mail:'jakesully789&#64;gmail.com',
    number:'1902-2001-3023',
    status:'Closed',
    img2:"./assets/images/company-logos/4.png",
    company:'Logitech ecostics',
    source:'Blog Articles',
    tag1:'Partner',
    bg1:'badge bg-success/10 text-success',
  },
  {
    id:'4',
    img:"./assets/images/faces/6.jpg",
    name:'Kiara Advain',
    mail:'kiaraadvain290&#64;gmail.com',
    number:'1603-2032-1123',
    status:'Contacted',
    img2:"./assets/images/company-logos/5.png",
    company:'Initech Info',
    source:'Affiliates',
    tag1:'LostCustomer',
    bg1:"badge bg-light text-default",
    tag2:'Influencer',
    bg2:'badge bg-secondary/10 text-secondary'
  },
  {
    id:'5',
    img:"./assets/images/faces/8.jpg",
    name:'Brenda Simpson',
    mail:'brendasimpson1993&#64;gmail.com',
    number:'1129-2302-1092',
    status:'New',
    img2:"./assets/images/company-logos/6.png",
    company:'Massive Dynamic',
    source:'Organic search',
    tag1:'Subscriber',
    bg1:"badge bg-pink/10 text-pink",
    tag2:'Partner',
    bg2:"badge bg-success/10 text-success"
  },
  {
    id:'6',
    img:"./assets/images/faces/9.jpg",
    name:'ชนะชัย โอดพิมพ์',
    mail:'jsontaylor345&#64;gmail.com',
    number:'9923-2344-2003',
    status:'Follow-up',
    img2:"./assets/images/company-logos/7.png",
    company:'Globex Corporation',
    source:'Social media',
    tag1:'Hot Lead',
    bg1:"badge bg-danger/10 text-danger",
    tag2:'Referral',
    bg2:"badge bg-info/10 text-info"
  },
  {
    id:'7',
    img:"./assets/images/faces/15.jpg",
    name:'Dwayne Jhonson',
    mail:'dwayenejhonson78&#64;gmail.com',
    number:'7891-2093-1994',
    status:'Closed',
    img2:"./assets/images/company-logos/8.png",
    company:'Acme Corporation',
    source:' Blog Articles',
    tag1:'Trial User',
    bg1:"badge bg-warning/10 text-warning",
    tag2:'Cold Lead',
    bg2:"badge bg-purple/10 text-purple"
  },
  {
    id:'8',
    img:"./assets/images/faces/1.jpg",
    name:'Emiley Jackson',
    mail:'emileyjackson678&#64;gmail.com',
    number:'1899-2993-0923',
    status:'Disqualified',
    img2:"./assets/images/company-logos/9.png",
    company:'Soylent Corp',
    source:' Organic search',
    tag1:'Influencer',
    bg1:"badge bg-success/10 text-success",
    tag2:'Partner',
    bg2:"badge bg-info/10 text-info"
  },
  {
    id:'9',
    img:"./assets/images/faces/3.jpg",
    name:'Jessica Morris',
    mail:'jessicamorris289&#64;gmail.com',
    number:'1768-2332-4934',
    status:'Qualified',
    img2:"./assets/images/company-logos/10.png",
    company:'Umbrella Corporation',
    source:' Affiliates',
    tag1:'New Lead',
    bg1:"badge bg-primary/10 text-primary",
    tag2:'Lost Customer',
    bg2:"badge bg-light text-default"
  },
  {
    id:'10',
    img:"./assets/images/faces/9.jpg",
    name:'Michael Jeremy',
    mail:'michaeljeremy186&#64;gmail.com',
    number:'4788-7822-4786',
    status:'Contacted',
    img2:"./assets/images/company-logos/2.png",
    company:'Hooli Technologies',
    source:' Direct mail',
    tag1:'New Lead',
    bg1:"badge bg-primary/10 text-primary",
    tag2:'Subscriber',
    bg2:"badge bg-pink/10 text-pink"
  },
]
@Component({
  selector: 'app-leads',
  standalone: true,
  imports: [SharedModule,MaterialModuleModule,FormsModule,ReactiveFormsModule,NgSelectModule],
  templateUrl: './leads.component.html',
  styleUrls: ['./leads.component.scss']
})
export class LeadsComponent {
leads=DATA;
click(id:string){
  const data=this.leads.filter((x: { id: string })=>{
    return x.id!=id
  })
 this.leads=data
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
