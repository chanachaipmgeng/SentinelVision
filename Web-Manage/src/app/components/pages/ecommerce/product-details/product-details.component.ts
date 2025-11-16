import { Component } from '@angular/core';
import { GalleryModule, Image } from '@ks89/angular-modal-gallery';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-product-details',
  standalone: true,
  imports: [SharedModule,GalleryModule,RouterModule],
  templateUrl: './product-details.component.html',
  styleUrls: ['./product-details.component.scss']
})
export class ProductDetailsComponent {
  dotsConfig!: false;

  imagesRect: Image[] = [

    new Image( 0, { img: './assets/images/ecommerce/png/15.png', },
      { img: './assets/images/ecommerce/png/15.png',
    }
    ),
    new Image(1, { img: './assets/images/ecommerce/png/13.png' }),
    new Image(
      2,
      {
        img: './assets/images/ecommerce/png/17.png',
       
      },
      {
        img: './assets/images/ecommerce/png/17.png',
     
      }
    ),
    new Image(
      3,
      {
        img: './assets/images/ecommerce/png/14.png',
       
      },
      { img: './assets/images/ecommerce/png/14.png',
      }
    ),
   
  ];
}
