import { Directive, ElementRef, HostListener, Inject, OnInit } from '@angular/core';
import { DOCUMENT } from '@angular/common';

type FullscreenElement = HTMLElement & {
  mozRequestFullScreen?: () => Promise<void>;
  webkitRequestFullscreen?: () => Promise<void>;
  msRequestFullscreen?: () => Promise<void>;
};

type FullscreenDocument = Document & {
  mozCancelFullScreen?: () => Promise<void>;
  webkitExitFullscreen?: () => Promise<void>;
  msExitFullscreen?: () => Promise<void>;
};

@Directive({
    selector: '[appFullscreen]',
    standalone: false
})
export class FullscreenDirective implements OnInit {

  public fullScreen = false;
  public elem!: FullscreenElement;

  constructor(
    @Inject(DOCUMENT) private document: FullscreenDocument,
    private elementRef: ElementRef<HTMLElement>
  ) { }

  ngOnInit(): void {
    this.elem = this.elementRef.nativeElement.ownerDocument.documentElement;
  }

  @HostListener('click')
  onClick(): void {
    this.fullScreen = !this.fullScreen;
    if (this.fullScreen) {
      if (this.elem.requestFullscreen) {
        void this.elem.requestFullscreen();
      } else if (this.elem.mozRequestFullScreen) {
        void this.elem.mozRequestFullScreen();
      } else if (this.elem.webkitRequestFullscreen) {
        void this.elem.webkitRequestFullscreen();
      } else if (this.elem.msRequestFullscreen) {
        void this.elem.msRequestFullscreen();
      }
    } else {
      if (this.document.exitFullscreen) {
        void this.document.exitFullscreen();
      } else if (this.document.mozCancelFullScreen) {
        void this.document.mozCancelFullScreen();
      } else if (this.document.webkitExitFullscreen) {
        void this.document.webkitExitFullscreen();
      } else if (this.document.msExitFullscreen) {
        void this.document.msExitFullscreen();
      }
    }
  }

}
