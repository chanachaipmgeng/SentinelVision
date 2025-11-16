import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { RouterModule } from '@angular/router';
const DATA=[
  {
    id:'1',
    img:"./assets/images/company-logos/1.png",
    name:'Spruko Technologies',
    mail:'sprukotechnologies2981@gmail.com',
    phnum:'1678-28993-223',
    type:'Information Technology',
    bg:'primary/10',
    text:'primary',
    size:'Corporate',
    img2:'./assets/images/faces/4.jpg',
    name2:'Lisa Convay',
    deals:'258'
  },
  {
    id:'2',
    img:"./assets/images/company-logos/3.png",
    name:'Spice Infotech',
    mail:'spiceinfotech289@gmail.com',
    phnum:'8122-2342-4453',
    type:'Telecommunications',
    bg:'danger/10',
    text:'danger',
    size:'Small Business',
    img2:'./assets/images/faces/12.jpg',
    name2:'Jacob Smith',
    deals:'335'
  },
  {
    id:'3',
    img:"./assets/images/company-logos/4.png",
    name:'Logitech ecostics',
    mail:'logitecheco789@gmail.com',
    phnum:'1902-2001-3023',
    type:'Logistics',
    bg:'success/10',
    text:'success',
    size:'Micro Business',
    img2:'./assets/images/faces/14.jpg',
    name2:'Jake Sully',
    deals:'685'
  },
  {
    id:'4',
    img:"./assets/images/company-logos/5.png",
    name:'Initech Info',
    mail:'initechinfo290@gmail.com',
    phnum:'1603-2032-1123',
    type:'Information Technology',
    bg:'light',
    text:'default',
    size:'Startup',
    img2:'./assets/images/faces/6.jpg',
    name2:'Kiara Advain',
    deals:'425'
  },
  {
    id:'5',
    img:"./assets/images/company-logos/6.png",
    name:'Massive Dynamic',
    mail:'massivedynamic1993@gmail.com',
    phnum:'1129-2302-1092',
    type:'Professional Services',
    bg:'pink/10',
    text:'pink',
    size:'Large Enterprise',
    img2:'./assets/images/faces/8.jpg',
    name2:'Brenda Simpson',
    deals:'516'
  },
  {
    id:'6',
    img:"./assets/images/company-logos/7.png",
    name:'Globex Corporation',
    mail:'globexcorp345@gmail.com',
    phnum:'9923-2344-2003',
    type:'Education',
    bg:'danger/10',
    text:'danger',
    size:'Small Business',
    img2:'./assets/images/faces/9.jpg',
    name2:'ชนะชัย โอดพิมพ์',
    deals:'127'
  },
  {
    id:'7',
    img:"./assets/images/company-logos/8.png",
    name:'Acme Corporation',
    mail:'acmecorporation78@gmail.com',
    phnum:'7891-2093-1994',
    type:'Telecommunications',
    bg:'primary/10',
    text:'primary',
    size:'Corporate',
    img2:'./assets/images/faces/15.jpg',
    name2:'Dwayne Jhonson',
    deals:'368'
  },
  {
    id:'8',
    img:"./assets/images/company-logos/9.png",
    name:'Soylent Corp',
    mail:'soylentcorp678@gmail.com',
    phnum:'1899-2993-0923',
    type:' Manufacturing',
    bg:'warning/10',
    text:'warning',
    size:'Medium Size',
    img2:'./assets/images/faces/1.jpg',
    name2:'Emiley Jackson',
    deals:'563'
  },
  {
    id:'9',
    img:"./assets/images/company-logos/10.png",
    name:'Umbrella Corporation',
    mail:'umbrellacorp289@gmail.com',
    phnum:'1768-2332-4934',
    type:'  Healthcare',
    bg:'success/10',
    text:'success',
    size:'Micro Business',
    img2:'./assets/images/faces/3.jpg',
    name2:'Jessica Morris',
    deals:'185'
  },
  {
    id:'10',
    img:"./assets/images/company-logos/2.png",
    name:'Hooli Technologies',
    mail:'hoolitech186@gmail.com',
    phnum:'4788-7822-4786',
    type:'   Information Technology',
    bg:'success/10',
    text:'success',
    size:'default',
    img2:'./assets/images/faces/9.jpg',
    name2:'Michael Jeremy',
    deals:'240'
  },
]
@Component({
  selector: 'app-companies',
  standalone: true,
  imports: [SharedModule,NgSelectModule,RouterModule],
  templateUrl: './companies.component.html',
  styleUrls: ['./companies.component.scss']
})
export class CompaniesComponent {
  companies=DATA;
  click(id:string){
    const data = this.companies.filter((x: { id: string }) => {
      return x.id != id;
    });
    this.companies = data;
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
