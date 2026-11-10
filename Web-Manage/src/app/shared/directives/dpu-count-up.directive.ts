import { Directive, ElementRef, Input, OnDestroy, OnInit } from '@angular/core';

@Directive({
  selector: '[dpuCountUp]',
  standalone: true,
})
export class DpuCountUpDirective implements OnInit, OnDestroy {
  @Input('dpuCountUp') target = 0;
  @Input() duration = 1400;
  @Input() decimals = 0;
  @Input() suffix = '';
  @Input() prefix = '';

  private observer?: IntersectionObserver;
  private frame = 0;
  private fallback?: ReturnType<typeof setTimeout>;
  private started = false;

  constructor(private readonly el: ElementRef<HTMLElement>) {}

  ngOnInit(): void {
    const node = this.el.nativeElement;
    node.textContent = `${this.prefix}0${this.suffix}`;

    if (typeof IntersectionObserver === 'undefined') {
      this.animate();
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          this.animate();
          this.observer?.disconnect();
        }
      },
      { threshold: 0.45 },
    );
    this.observer.observe(node);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    cancelAnimationFrame(this.frame);
    if (this.fallback) {
      clearTimeout(this.fallback);
    }
  }

  private animate(): void {
    if (this.started) {
      return;
    }
    this.started = true;

    const to = Number(this.target) || 0;
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      this.render(to);
      return;
    }

    const start = performance.now();
    const from = 0;
    const duration = this.duration || 1400;

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      this.render(from + (to - from) * eased);
      if (t < 1) {
        this.frame = requestAnimationFrame(tick);
      }
    };

    this.frame = requestAnimationFrame(tick);
    this.fallback = setTimeout(() => {
      cancelAnimationFrame(this.frame);
      this.render(to);
    }, duration + 100);
  }

  private render(value: number): void {
    const fixed = value.toFixed(this.decimals || 0);
    this.el.nativeElement.textContent = `${this.prefix}${fixed}${this.suffix}`;
  }
}
