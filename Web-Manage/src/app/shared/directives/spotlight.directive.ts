import { Directive, ElementRef, OnDestroy, OnInit, inject } from '@angular/core';

import { preferReducedMotion } from '../utils/motion';

/** Tracks pointer as `--mx` / `--my` (%) for CSS spotlight overlays. */
@Directive({
  selector: '[dpuSpotlight]',
  standalone: true,
})
export class SpotlightDirective implements OnInit, OnDestroy {
  private readonly el = inject(ElementRef<HTMLElement>);
  private raf = 0;
  private pendingX = 50;
  private pendingY = 50;
  private readonly onMove = (event: PointerEvent) => this.schedule(event);
  private readonly onLeave = () => {
    const node = this.el.nativeElement;
    node.style.setProperty('--mx', '50%');
    node.style.setProperty('--my', '50%');
    node.classList.remove('is-spotlight');
  };

  ngOnInit(): void {
    if (preferReducedMotion()) {
      return;
    }
    const node = this.el.nativeElement;
    node.classList.add('spotlight-host');
    node.addEventListener('pointermove', this.onMove, { passive: true });
    node.addEventListener('pointerleave', this.onLeave, { passive: true });
  }

  ngOnDestroy(): void {
    const node = this.el.nativeElement;
    node.removeEventListener('pointermove', this.onMove);
    node.removeEventListener('pointerleave', this.onLeave);
    if (this.raf) {
      cancelAnimationFrame(this.raf);
    }
  }

  private schedule(event: PointerEvent): void {
    const node = this.el.nativeElement;
    const rect = node.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return;
    }
    this.pendingX = ((event.clientX - rect.left) / rect.width) * 100;
    this.pendingY = ((event.clientY - rect.top) / rect.height) * 100;
    if (this.raf) {
      return;
    }
    this.raf = requestAnimationFrame(() => {
      this.raf = 0;
      node.style.setProperty('--mx', `${this.pendingX.toFixed(2)}%`);
      node.style.setProperty('--my', `${this.pendingY.toFixed(2)}%`);
      node.classList.add('is-spotlight');
    });
  }
}
