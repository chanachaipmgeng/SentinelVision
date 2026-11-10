import { Component, HostBinding, HostListener } from '@angular/core';

@Component({
  selector: 'app-dpu-mouse-glow',
  standalone: true,
  template: `
    <div class="dpu-mouse-glow__orb" aria-hidden="true"></div>
  `,
  host: {
    class: 'dpu-mouse-glow',
  },
})
export class DpuMouseGlowComponent {
  x = 0;
  y = 0;
  active = false;

  @HostBinding('class.is-active')
  get isActive(): boolean {
    return this.active;
  }

  @HostBinding('style.--mx.px')
  get mx(): number {
    return this.x;
  }

  @HostBinding('style.--my.px')
  get my(): number {
    return this.y;
  }

  @HostListener('document:pointermove', ['$event'])
  onMove(event: PointerEvent): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (
      window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
      window.matchMedia('(pointer: coarse)').matches
    ) {
      this.active = false;
      return;
    }
    this.x = event.clientX;
    this.y = event.clientY;
    this.active = true;
  }
}
