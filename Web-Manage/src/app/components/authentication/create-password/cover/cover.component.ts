import { Component, ElementRef, Inject, Renderer2 } from '@angular/core';
import { CommonModule, DOCUMENT } from '@angular/common';
import { CarouselModule, OwlOptions, SlidesOutputData } from 'ngx-owl-carousel-o';
import { fromEvent } from 'rxjs';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-cover',
  standalone: true,
  imports: [SharedModule,CarouselModule,RouterModule],
  templateUrl: './cover.component.html',
  styleUrl: './cover.component.scss'
})
export class CoverComponent {
index: any;
  constructor(
    @Inject(DOCUMENT) private document: Document,private elementRef: ElementRef,
    private renderer: Renderer2


  ) {}
  ngOnInit(): void {
 
    this.renderer.addClass(this.document.body, 'bg-white');
    this.renderer.addClass(this.document.body, 'dark:bg-!bodybg');
    this.renderer.addClass(this.document.body, 'text-defaulttextcolor');
    this.renderer.addClass(this.document.body, 'dark:text-defaulttextcolor/70');
    this.renderer.addClass(this.document.body, 'text-defaultsize');
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
    this.renderer.removeClass(this.document.body, 'bg-white');
    this.renderer.removeClass(this.document.body, 'dark:bg-!bodybg');
    this.renderer.removeClass(this.document.body, 'text-defaulttextcolor');
    this.renderer.removeClass(this.document.body, 'dark:text-defaulttextcolor/70');
    this.renderer.removeClass(this.document.body, 'text-defaultsize');

}


customOptions: OwlOptions = {
  loop: true,
  rtl:false,
  mouseDrag: true,
  touchDrag: true,
  pullDrag: false,
  dots: true,
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
  {img:'./assets/images/authentication/2.png'},
  { img:'./assets/images/authentication/3.png'},
  { img:"./assets/images/authentication/2.png"},
];

getPassedData(data: SlidesOutputData) {
  this.activeSlides = data;
}
showPassword = false;
toggleClass = "off-line";
toggleVisibility() {
  this.showPassword = !this.showPassword;
  if (this.toggleClass === "off-line") {
    this.toggleClass = "line";
  } else {
    this.toggleClass = "off-line";
  }
}
showPassword1 = false;
toggleClass1 = "off-line";
toggleVisibility1() {
  this.showPassword1 = !this.showPassword1;
  if (this.toggleClass1 === "off-line") {
    this.toggleClass1 = "line";
  } else {
    this.toggleClass1 = "off-line";
  }
}
}
