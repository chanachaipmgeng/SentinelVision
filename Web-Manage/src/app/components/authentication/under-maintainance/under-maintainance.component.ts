import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, Inject, Renderer2 } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-under-maintainance',
  standalone: true,
  imports: [SharedModule,RouterModule],
  templateUrl: './under-maintainance.component.html',
  styleUrls: ['./under-maintainance.component.scss']
})
export class UnderMaintainanceComponent {
  public days: unknown;
  public hours: unknown;
  public minutes: unknown;
  public seconds: unknown;
  constructor(
    @Inject(DOCUMENT) private document: Document,private elementRef: ElementRef,
    private renderer: Renderer2
  ) {}
  ngOnInit(): void {
    const countDown = new Date('Dec 1, 2025 00:00:00').getTime();
    const time = setInterval(() => {
      const now = new Date().getTime();
      const distance = countDown - now;
      this.days = Math.floor(distance / (1000 * 60 * 60 * 24));
      this.hours = Math.floor(
        (distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
      );
      this.minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      this.seconds = Math.floor((distance % (1000 * 60)) / 1000);

      if (distance < 0) {
        clearInterval(time);
      }
    }, 1000);
    this.renderer.addClass(this.document.body, 'bg-white');
    this.renderer.addClass(this.document.body, 'dark:bg-!bodybg');

  }
  ngOnDestroy(): void {
    this.renderer.removeClass(this.document.body, 'bg-white');
    this.renderer.removeClass(this.document.body, 'dark:bg-!bodybg');
}

}
