import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, HostListener, Inject, Renderer2 } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-scrollspy',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './scrollspy.component.html',
  styleUrls: ['./scrollspy.component.scss']
})
export class ScrollspyComponent {
  constructor(
    @Inject(DOCUMENT) private document: Document,private elementRef: ElementRef,
    private renderer: Renderer2,  private el: ElementRef,

  ) { }
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
}
