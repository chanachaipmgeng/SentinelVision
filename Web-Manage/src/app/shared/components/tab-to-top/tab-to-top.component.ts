import { ViewportScroller } from '@angular/common';
import { Component, HostListener } from '@angular/core';

@Component({
  selector: 'app-tab-to-top',
  templateUrl: './tab-to-top.component.html',
  styleUrl: './tab-to-top.component.scss'
})
export class TabToTopComponent {
  public show: boolean = false;

  constructor(
    private viewScroller: ViewportScroller
  ) { }

  ngOnInit(): void {
  }

  @HostListener("window:scroll", [])

  onWindowScroll(){
    let number = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    if (number > 600) {
      this.show = true;
    } else {
      this.show = false;
    }
  }

  taptotop(){
    let body:any = document.querySelector('body')
    body.style. scrollBehavior = 'smooth';
    this.viewScroller.scrollToPosition([0,0]);
  }
}
