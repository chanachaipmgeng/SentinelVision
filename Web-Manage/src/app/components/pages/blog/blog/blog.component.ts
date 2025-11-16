import { Component, ElementRef } from '@angular/core';
import { CarouselModule, OwlOptions, SlidesOutputData } from 'ngx-owl-carousel-o';
import { fromEvent } from 'rxjs';
import { SharedModule } from '../../../../shared/shared.module';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-blog',
  standalone: true,
  imports: [SharedModule,CarouselModule,CommonModule,RouterModule],
  templateUrl: './blog.component.html',
  styleUrls: ['./blog.component.scss']
})
export class BlogComponent {
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
    animateOut: 'fadeOut',
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
      src: './assets/images/media/media-70.jpg',
      src1: './assets/images/faces/15.jpg',
    text:"The agency has a diverse workforce of just under 18,000 civil servants, and works with many more U.S.",
    text1:"N.A.S.A",
    text2:"ชนะชัย โอดพิมพ์ -",
    text3:"12,Dec 2022 - 04:34PM"
    },
    {
      src: './assets/images/media/media-71.jpg',
      src1: './assets/images/faces/15.jpg',
    text:"NASA is committed to providing all categories of businesses in both NASA prime contracts and subcontracts.",
    text1:"NASA Businesses",
    text2:"Elisha Keens -",
    text3:"23,Dec 2022 - 11:27AM"
    },
    {
      src: './assets/images/media/media-72.jpg',
      src1: './assets/images/faces/4.jpg',
    text:"NASA Nelson served in the U.S. Senate for 18 years from Florida space shuttle mission 61-C in 1986.",
    text1:"NASA Leadership",
    text2:"Melissa Blue - ",
    text3:"16,Dec 2022 - 9:45AM"
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
  constructor(private elementRef: ElementRef){

  }
}
