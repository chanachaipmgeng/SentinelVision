import { Directive, ElementRef, Input, OnDestroy, OnInit } from '@angular/core';

export type DpuRevealPreset = 'up' | 'left' | 'right' | 'dashboard' | 'fade';

@Directive({
  selector: '[dpuReveal]',
  standalone: true,
})
export class DpuRevealDirective implements OnInit, OnDestroy {
  @Input('dpuReveal') preset: DpuRevealPreset = 'up';
  @Input() dpuRevealDelay = '0s';
  @Input() dpuRevealOnce = true;

  private observer?: IntersectionObserver;

  constructor(private readonly el: ElementRef<HTMLElement>) {}

  ngOnInit(): void {
    const node = this.el.nativeElement;
    node.classList.add('dpu-reveal', `dpu-reveal--${this.preset || 'up'}`);
    node.style.setProperty('--dpu-reveal-delay', this.dpuRevealDelay || '0s');

    if (typeof IntersectionObserver === 'undefined') {
      node.classList.add('is-visible');
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            node.classList.add('is-visible');
            if (this.dpuRevealOnce !== false) {
              this.observer?.unobserve(entry.target);
            }
          } else if (this.dpuRevealOnce === false) {
            node.classList.remove('is-visible');
          }
        }
      },
      {
        threshold: this.preset === 'dashboard' ? 0.05 : 0.28,
        rootMargin: this.preset === 'dashboard' ? '0px' : '0px 0px -8% 0px',
      },
    );

    const watched = this.preset === 'dashboard' ? node.parentElement ?? node : node;
    this.observer.observe(watched);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
