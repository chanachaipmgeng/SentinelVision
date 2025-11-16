import { Component } from '@angular/core';
import { Image } from '@ks89/angular-modal-gallery';
import { GalleryModule } from '@ks89/angular-modal-gallery';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-nft-details',
  standalone: true,
  imports: [SharedModule,GalleryModule],
  templateUrl: './nft-details.component.html',
  styleUrls: ['./nft-details.component.scss']
})
export class NftDetailsComponent {
  dotsConfig!: false;
  
  imagesRect: Image[] = [

    new Image(
      0,
      { img: './assets/images/nft-images/32.png', },
      { img: './assets/images/nft-images/32.png',}
    ),
    new Image(1, { img: './assets/images/nft-images/33.png' }),
    new Image(
      2,
      {
        img: './assets/images/nft-images/31.png',
       
      },
      {
        img: './assets/images/nft-images/31.png',
     
      }
    ),
    new Image(
      3,
      {
        img: './assets/images/nft-images/30.png',
       
      },
      { img: './assets/images/nft-images/30.png',
      }
    ),
    // new Image(4, { img: './assets/images/nft-images/33.png' }),
   
  ];

}
