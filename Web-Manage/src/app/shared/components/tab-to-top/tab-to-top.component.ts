import { CommonModule, ViewportScroller } from '@angular/common';
import { Component, HostListener } from '@angular/core';

@Component({
    selector: 'app-tab-to-top',
    imports: [CommonModule],
    templateUrl: './tab-to-top.component.html',
    styleUrl: './tab-to-top.component.scss',
})
export class TabToTopComponent {
  public show: boolean = false;

  constructor(
    private viewScroller: ViewportScroller
  ) { }

  @HostListener("window:scroll", [])

  onWindowScroll(){
    const number = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    if (number > 600) {
      this.show = true;
    } else {
      this.show = false;
    }
  }

  taptotop(){
    const body = document.querySelector('body') as HTMLElement | null;
    if (body) {
      body.style.scrollBehavior = 'smooth';
    }
    this.viewScroller.scrollToPosition([0,0]);
  }
}
