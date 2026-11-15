import { Directive, ElementRef, OnDestroy, OnInit, inject, input } from '@angular/core';

import { preferReducedMotion } from '../utils/motion';

function coercePx(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (value === '' || value === true || value == null) {
    return fallback;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/** Soft magnetic pull toward pointer (max ~6px). For CTA buttons/links. */
@Directive({
  selector: '[dpuMagnetic]',
  standalone: true,
})
export class MagneticDirective implements OnInit, OnDestroy {
  /** Max displacement in px. */
  readonly dpuMagnetic = input(6, { transform: (v: unknown) => coercePx(v, 6) });

  private readonly el = inject(ElementRef<HTMLElement>);
  private raf = 0;
  private readonly onMove = (event: PointerEvent) => this.schedule(event);
  private readonly onLeave = () => {
    const node = this.el.nativeElement;
    node.style.transform = '';
    node.classList.remove('is-magnetic');
  };

  ngOnInit(): void {
    if (preferReducedMotion()) {
      return;
    }
    const node = this.el.nativeElement;
    node.classList.add('magnetic-host');
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
    const max = this.dpuMagnetic();
    const dx = ((event.clientX - rect.left) / rect.width - 0.5) * 2 * max;
    const dy = ((event.clientY - rect.top) / rect.height - 0.5) * 2 * max;
    if (this.raf) {
      cancelAnimationFrame(this.raf);
    }
    this.raf = requestAnimationFrame(() => {
      this.raf = 0;
      node.style.transform = `translate3d(${dx.toFixed(2)}px, ${dy.toFixed(2)}px, 0)`;
      node.classList.add('is-magnetic');
    });
  }
}
