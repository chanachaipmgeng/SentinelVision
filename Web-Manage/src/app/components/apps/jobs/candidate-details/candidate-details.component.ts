import { Component, ElementRef } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';
import { CarouselModule, OwlOptions, SlidesOutputData } from 'ngx-owl-carousel-o';
import { fromEvent } from 'rxjs';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-candidate-details',
  standalone: true,
  imports: [SharedModule,  CarouselModule,RouterModule],
  templateUrl: './candidate-details.component.html',
  styleUrls: ['./candidate-details.component.scss']
})
export class CandidateDetailsComponent {

  customOptions: OwlOptions = {
    loop: true,
    rtl:false,
    mouseDrag: true,
    touchDrag: true,
    pullDrag: false,
    dots: false,
    navSpeed: 700,
    autoplay: true,
    navText: ['<', '>'],
    autoHeight: true,
    autoWidth: true,
    responsive: {
      0: {items: 1},
      400: { items: 1 },
      740: {  items: 1},
      1000: { items: 1},
    },
    nav: true,
  };
  activeSlides!: SlidesOutputData;

  slidesStore: any[] = [
    {
      // company: 'Spotech Technical Solutions',
      img:'./assets/images/faces/1.jpg',
      role:'Software Developer',
      name:'Brenda Simpson',
      location:'Kondapur, Hyderabad',
      rating:"bi bi-star-fill",
      rating1:"bi bi-star-half",
      ratings:'(142)',
     degree:'Graduate',
     shift:'sm:flexible-shift',
     notice:'Immediate Joinee',
     language:'Good at English',
     skill1:'HTML',
     skill2:'CSS',
     skill3:'Javascript',
     skill4:'Angular',
     bond:'1 year bond accepted',
     exp:'Exp : 2 Years'
    },
    {
      // company: 'Dwayne Stort',
      img:'./assets/images/faces/3.jpg',
      role:'Web Developer',
      name:'Brenda Simpson',
      location:'Gachibowli, Hyderabad',
      rating:"bi bi-star",
      rating1:"bi bi-star",
      ratings:'(35)',
     degree:'Post Graduate',
     shift:'sm:flexible-shift',
     notice:'Within 10 Days',
     language:'Good at English',
     skill1:'React',
     skill2:'CSS',
     skill3:'Javascript',
     skill4:'React Navtive',
     bond:'2 years bond accepted',
     exp:'Exp : 4 Years'
    },
    {
      // company: 'Dwayne Stort',
      img:'./assets/images/faces/21.jpg',
      role:'Python Developer',
      name:'Dwayne Stort',
      location:'Gachibowli, Chennai',
      rating:"bi bi-star",
      rating1:"bi bi-star",
      ratings:'(56)',
     degree:'MBA',
     shift:'Day-shift',
     notice:'Within 30 Days',
     language:'Avg at English',
     skill1:'Python',
     skill2:'Java',
     skill3:'React',
     skill4:'React Navtive',
     exp:'Exp : 5 Years'
    },
  ];
  constructor(private sanitizer: DomSanitizer,private elementRef: ElementRef, ) {}

  getPassedData(data: SlidesOutputData) {
    this.activeSlides = data;
    console.log(this.activeSlides);
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
}
