import { Component, ElementRef, ViewChild} from '@angular/core';
import KeenSlider, { KeenSliderInstance, KeenSliderPlugin} from "keen-slider"
import { SharedModule } from '../../../shared/shared.module';
import { SwiperModule } from 'swiper/angular';
import SwiperCore, {
  Navigation,
  Pagination,
  Scrollbar,
  A11y,
  Virtual,
  Zoom,
  Autoplay,
  Thumbs,
  Mousewheel,
  Keyboard,
  EffectCube,
  EffectFade,
  EffectFlip,
  EffectCoverflow,
  SwiperOptions,
} from 'swiper';
import { CommonModule, NgFor } from '@angular/common';

SwiperCore.use([
  Navigation,
  Pagination,
  Scrollbar,
  A11y,
  Virtual,
  Mousewheel,
  Zoom,
  Autoplay,
  Thumbs,
  Keyboard,
  EffectCube,
  EffectFade,
  EffectFlip,
  EffectCoverflow,
]);

@Component({
  selector: 'app-swiperjs',
  standalone: true,
  imports: [SharedModule,SwiperModule,CommonModule],
  templateUrl: './swiperjs.component.html',
  styleUrls: ['./swiperjs.component.scss']
})
export class SwiperjsComponent {
  indexNumber = 1;
  thumbsSwiper: any;

  setThumbsSwiper(swiper: any) {
    this.thumbsSwiper = swiper;
  }

  swiperOptions: SwiperOptions = {
    slidesPerView: 1,
    zoom: true,
    autoplay: { delay: 1000, disableOnInteraction: false },
    navigation: false,
    watchSlidesProgress: true,
    effect: 'fade',
  };

  @ViewChild('sliderRef') sliderRef!: ElementRef<HTMLElement>;
  opacities: number[] = [];
  slider!: KeenSliderInstance;
  
  public currentSlide = 1;

  ngAfterViewInit() {
    setTimeout(() => {
      if (this.sliderRef && this.sliderRef.nativeElement) {
        this.slider = new KeenSlider(this.sliderRef.nativeElement, {
          slides: this.imageData.length,
          loop: true,
          defaultAnimation: {
            duration: 3000,
          },
          detailsChanged: (s) => {
            this.opacities = s.track.details.slides.map(
              (slide) => slide.portion
            );
          },
        });
      }
    });

    if (this.sliderRef && this.sliderRef.nativeElement) {
      this.slider = new KeenSlider(this.sliderRef.nativeElement);
    }

  }

  ngOnDestroy() {
    if (this.slider) this.slider.destroy();
  }
  images = [
    {
      src: './assets/images/media/media-27.jpg',
    },
    {
      src: './assets/images/media/media-26.jpg',
    },
    {
      src: './assets/images/media/media-25.jpg',
    },
   
  ];
  imageData = [
    {
      src: './assets/images/media/media-12.jpg',
    },
    {
      src: './assets/images/media/media-8.jpg',
    },
    {
      src: './assets/images/media/media-28.jpg',
    },
    {
      src: './assets/images/media/media-31.jpg',
    },
  ];
  imageData1 = [
    {
      src: './assets/images/media/media-29.jpg',
    },
    {
      src: './assets/images/media/media-28.jpg',
    },
    {
      src: './assets/images/media/media-30.jpg',
    },
  ];
  imageData2 = [
    {
      src: './assets/images/media/media-32.jpg',
    },
    {
      src: './assets/images/media/media-31.jpg',
    },
    {
      src: './assets/images/media/media-33.jpg',
    },
  ];
  imageData3 = [
    {
      src: './assets/images/media/media-21.jpg',
    },
    {
      src: './assets/images/media/media-17.jpg',
    },
    {
      src: './assets/images/media/media-16.jpg',
    },
  ];
  imageData4 = [
    {
      src: './assets/images/media/media-12.jpg',
    },
    {
      src: './assets/images/media/media-8.jpg',
    },
    {
      src: './assets/images/media/media-5.jpg',
    },
  
  ];
  imageData5 = [
    {
      src: './assets/images/media/media-16.jpg',
    },
    {
      src: './assets/images/media/media-30.jpg',
    },
    {
      src: './assets/images/media/media-31.jpg',
    },

  ];
  imageData6 = [
    {
      src: './assets/images/media/media-25.jpg',
    },
    {
      src: './assets/images/media/media-5.jpg',
    },
    {
      src: './assets/images/media/media-33.jpg',
    },
   
  ];
  imageData0 = [
    {
      src: './assets/images/media/media-30.jpg',
    },
    {
      src: './assets/images/media/media-28.jpg',
    },
    {
      src: './assets/images/media/media-29.jpg',
    },
   
  ];
  imageData7 = [
    {
      src: './assets/images/media/media-8.jpg',
    },
    {
      src: './assets/images/media/media-32.jpg',
    },
    {
      src: './assets/images/media/media-7.jpg',
    },
 
  ];
  imageData8 = [
    {
      src: './assets/images/media/media-28.jpg',
    },
    {
      src: './assets/images/media/media-30.jpg',
    },
    {
      src: './assets/images/media/media-32.jpg',
    },
    
  ];
  imageData9 = [
    {
      src: './assets/images/media/media-31.jpg',
    },
    {
      src: './assets/images/media/media-12.jpg',
    },
    {
      src: './assets/images/media/media-8.jpg',
    },
  ]
}
