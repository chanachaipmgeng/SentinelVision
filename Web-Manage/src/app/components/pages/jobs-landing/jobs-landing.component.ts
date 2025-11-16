import { CommonModule, DOCUMENT } from '@angular/common';
import { Component, ElementRef, HostListener, Inject, Renderer2 } from '@angular/core';
import { CarouselModule, OwlOptions, SlidesOutputData } from 'ngx-owl-carousel-o';
import { fromEvent } from 'rxjs';
import { SharedModule } from '../../../shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-jobs-landing',
  standalone: true,
  imports: [CommonModule,SharedModule,CarouselModule,FormsModule,ReactiveFormsModule,RouterModule],
  templateUrl: './jobs-landing.component.html',
  styleUrls: ['./jobs-landing.component.scss']
})
export class JobsLandingComponent {
  constructor(
    @Inject(DOCUMENT) private document: Document,private elementRef: ElementRef,
    private renderer: Renderer2,  private el: ElementRef,

  ) {    const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;
  const bodyElement = document.body;
  this.renderer.setAttribute(htmlElement, 'data-nav-style', 'menu-click');
  this.renderer.setAttribute(htmlElement, 'data-toggled', 'close');
  this.renderer.removeClass(bodyElement, 'sidebar-mini');
  this.renderer.setAttribute(htmlElement, 'data-nav-layout', 'horizontal');}
  ngOnInit(): void {

    this.renderer.addClass(this.document.body, 'landing-body');

    const ltr = this.elementRef.nativeElement.querySelectorAll('#switcher-ltr');
    const rtl = this.elementRef.nativeElement.querySelectorAll('#switcher-rtl');

    fromEvent(ltr, 'click').subscribe(() => {
      this.customOptions = { ...this.customOptions, rtl: false };
    });

    fromEvent(rtl, 'click').subscribe(() => {
      this.customOptions = { ...this.customOptions, rtl: true, autoplay: true };
    });

  }
  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, 'landing-body');
    const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;
  this.renderer.setAttribute(htmlElement, 'data-nav-layout', 'vertical');
  this.renderer.removeAttribute(htmlElement, 'data-toggled');
  this.renderer.setAttribute(htmlElement, 'data-menu-styles', 'dark');

}
themeChange(type: string, type1: string) {
  const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;

  this.renderer.setAttribute(htmlElement, 'class', type);
  localStorage.setItem('synto-theme-mode', type);

  this.renderer.setAttribute(htmlElement, 'data-header-styles', type1);
  localStorage.setItem('synto-header-mode', type1);

  if (localStorage.getItem('synto-header-mode') === type1) {
    this.renderer.removeAttribute(htmlElement, 'style');
  }
}
public localDark = localStorage;
public localRtl = localStorage;
public darkchecked: any;
public RtlChecked: any;

scroll(el: HTMLElement) {
  el.scrollIntoView({ behavior: 'smooth' });
}

scrolled = false;

@HostListener('window:scroll', [])
onWindowScroll() {
  this.scrolled = window.scrollY > 10;
  const sections = this.el.nativeElement.querySelectorAll('.side-menu__item');
  const scrollPos =
    window.scrollY ||
    this.elementRef.nativeElement.ownerDocument.documentElement.scrollTop ||
    document.body.scrollTop;
  sections.forEach((el: any, i: string | number) => {
    const currLink = sections[i];
    const val: any = currLink.getAttribute('value');
    const refElement: any = this.el.nativeElement.querySelector('#' + val);

    if (refElement !== null) {
      const scrollTopMinus = scrollPos + 73;
      if (
        refElement.offsetTop <= scrollTopMinus &&
        refElement.offsetTop + refElement.offsetHeight > scrollTopMinus
      ) {
        const activeNav =
          this.el.nativeElement.querySelector('.nav-scroll.active');
        if (activeNav) {
          this.renderer.removeClass(activeNav, 'active');
        }
        this.renderer.addClass(currLink, 'active');
      } else {
        this.renderer.removeClass(currLink, 'active');
      }
    }
  });
}

expande = false;
expande1 = false;
expande2 = false;
expande3=false;
toggleExpand(): void {
  this.expande = !this.expande;
 if (localStorage.getItem('data-menu-styles') == 'light') {
   document
     .querySelector('html')
     ?.setAttribute('data-menu-styles', 'light');
 } else if (localStorage.getItem('data-menu-styles') == 'dark') {
   document
     .querySelector('html')
     ?.setAttribute('data-menu-styles', 'dark');
 }
}
bodyclick() {
  this.expande1 = false;
  this.expande2 = false;
  this.expande3 = false;
  this.expande = false;
  const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;
  this.renderer.setAttribute(htmlElement, 'data-toggled', 'close');
}
customOptions: OwlOptions = {
  loop: true,
  mouseDrag: true,
  touchDrag: true,
  pullDrag: false,
  dots: true,
  navSpeed: 700,
  autoplay: true,
  navText: ['<', '>'],
  responsive: {
    0: {
      items: 1, // 1 item visible for screen width less than 400 pixels
    },
    400: {
      items: 1, // 1 item visible for screen width 400 pixels or more
    },
    740: {
      items: 1, // 2 items visible for screen width 740 pixels or more
    },
    1000: {
      items: 3, // 2 items visible for screen width 1000 pixels or more
    },
  },
  nav: false,
};

activeSlides!: SlidesOutputData;

slidesStore: any[] = [
  {
    img:'./assets/images/faces/15.jpg',
    role:'CEO OF NORJA',
    name:'ชนะชัย โอดพิมพ์',

  },
  {
    img:'./assets/images/faces/4.jpg',
    role:'MANAGER CHO',
    name:'Melissa Blue',

  },
  {
    img:'./assets/images/faces/2.jpg',
    role:'CEO OF EMPIRO',
    name:'Kiara Advain',

  },
  {
    img:'./assets/images/faces/10.jpg',
    role:'CHIEF SECRETARY MBIO',
    name:'Jhonson Smith',

  },
  {
    img:'./assets/images/faces/12.jpg',
    role:'CEO ARMEDILLO',
    name:'Dwayne Stort',

  },
  {
    img:'./assets/images/faces/3.jpg',
    role:'AGGENT AMIO',
    name:'Jasmine Kova',

  },
  {
    img:'./assets/images/faces/16.jpg',
    role:'CEO MR BRAND',
    name:'Dolph MR',
  },
  {
    img:'./assets/images/faces/5.jpg',
    role:'CEO AIBMO',
    name:'Brenda Simpson',

  },
  {
    img:'./assets/images/faces/7.jpg',
    role:'CHIEF SECRETARY BHOL',
    name:'Julia Sams',
    },
];


getPassedData(data: SlidesOutputData) {
  this.activeSlides = data;
  console.log(this.activeSlides);
}
toggleSidebar() {
  const htmlElement =
    this.elementRef.nativeElement.ownerDocument.documentElement;
  const currentToggleValue = htmlElement.getAttribute('data-toggled');

  if (currentToggleValue !== 'open') {
    this.renderer.setAttribute(htmlElement, 'data-toggled', 'open');
  } else {
    this.renderer.setAttribute(htmlElement, 'data-toggled', 'close');
  }
}

}
