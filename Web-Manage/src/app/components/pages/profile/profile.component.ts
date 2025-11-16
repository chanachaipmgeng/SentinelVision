import { Component } from '@angular/core';
import { Gallery, GalleryItem, GalleryModule, ImageItem, ImageSize, ThumbnailsPosition } from 'ng-gallery';
import {  Lightbox, LightboxModule } from 'ng-gallery/lightbox';
import { SharedModule } from '../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [SharedModule,GalleryModule,LightboxModule,SimplebarAngularModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent {
  constructor(public gallery: Gallery, public lightbox: Lightbox) {}
  items: GalleryItem[] = [];

  imageData=DATA;
  ngOnInit() {
    /** Basic Gallery Example */

    // Creat gallery items
    this.items = this.imageData.map(
      (item) => new ImageItem({ src: item.srcUrl, thumb: item.previewUrl })
    );

    /** Lightbox Example */

    // Get a lightbox gallery ref
    const lightboxRef = this.gallery.ref('lightbox');

    // Add custom gallery config to the lightbox (optional)
    lightboxRef.setConfig({
      imageSize: ImageSize.Cover,
      thumbPosition: ThumbnailsPosition.Top,
    });

    // Load items into the lightbox gallery ref
    lightboxRef.load(this.items);
  }

}


const DATA = [
  {
    srcUrl: './assets/images/media/media-40.jpg',
    previewUrl: './assets/images/media/media-40.jpg',
  },
  {
    srcUrl: './assets/images/media/media-41.jpg',
    previewUrl: './assets/images/media/media-41.jpg',
  },
  {
    srcUrl: './assets/images/media/media-42.jpg',
    previewUrl: './assets/images/media/media-42.jpg',
  },
  {
    srcUrl: './assets/images/media/media-43.jpg',
    previewUrl: './assets/images/media/media-43.jpg',
  },
  {
    srcUrl: './assets/images/media/media-44.jpg',
    previewUrl: './assets/images/media/media-44.jpg',
  },
  {
    srcUrl: './assets/images/media/media-45.jpg',
    previewUrl: './assets/images/media/media-45.jpg',
  },
  {
    srcUrl: './assets/images/media/media-46.jpg',
    previewUrl: './assets/images/media/media-46.jpg',
  },
  {
    srcUrl: './assets/images/media/media-60.jpg',
    previewUrl: './assets/images/media/media-60.jpg',
  },
  {
    srcUrl: './assets/images/media/media-26.jpg',
    previewUrl: './assets/images/media/media-26.jpg',
  },
  {
    srcUrl: './assets/images/media/media-32.jpg',
    previewUrl: './assets/images/media/media-32.jpg',
  },
  {
    srcUrl: './assets/images/media/media-30.jpg',
    previewUrl: './assets/images/media/media-30.jpg',
  },
  {
    srcUrl: './assets/images/media/media-31.jpg',
    previewUrl: './assets/images/media/media-31.jpg',
  },
];
