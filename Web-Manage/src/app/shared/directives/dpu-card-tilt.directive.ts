import { Directive, ElementRef, HostListener, Input, OnDestroy, OnInit } from '@angular/core';

@Directive({
  selector: '[dpuCardTilt]',
  standalone: true,
})
export class DpuCardTiltDirective implements OnInit, OnDestroy {
  @Input('dpuCardTilt') enabled: boolean | string = true;
  @Input() maxTilt = 8;

  private frame = 0;
  private reduced = false;

  constructor(private readonly el: ElementRef<HTMLElement>) {}

  ngOnInit(): void {
    this.reduced =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const node = this.el.nativeElement;
    node.classList.add('dpu-tilt');
    if (this.isEnabled()) {
      node.classList.add('dpu-tilt--enabled');
    }
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.frame);
  }

  @HostListener('pointermove', ['$event'])
  onMove(event: PointerEvent): void {
    if (this.reduced || !this.isEnabled()) {
      return;
    }
    const node = this.el.nativeElement;
    const rect = node.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    const max = this.maxTilt || 8;
    const rotateY = (px - 0.5) * max * 2;
    const rotateX = (0.5 - py) * max * 2;

    cancelAnimationFrame(this.frame);
    this.frame = requestAnimationFrame(() => {
      node.style.setProperty('--tilt-x', `${rotateX.toFixed(2)}deg`);
      node.style.setProperty('--tilt-y', `${rotateY.toFixed(2)}deg`);
      node.style.setProperty('--tilt-mx', `${(px * 100).toFixed(1)}%`);
      node.style.setProperty('--tilt-my', `${(py * 100).toFixed(1)}%`);
      node.classList.add('is-tilting');
    });
  }

  @HostListener('pointerleave')
  onLeave(): void {
    const node = this.el.nativeElement;
    cancelAnimationFrame(this.frame);
    node.classList.remove('is-tilting');
    node.style.setProperty('--tilt-x', '0deg');
    node.style.setProperty('--tilt-y', '0deg');
  }

  private isEnabled(): boolean {
    return this.enabled !== false && this.enabled !== 'false';
  }
}
