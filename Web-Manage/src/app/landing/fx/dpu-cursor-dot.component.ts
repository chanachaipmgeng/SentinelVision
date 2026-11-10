import { AfterViewInit, Component, ElementRef, HostBinding, NgZone, OnDestroy } from '@angular/core';

const BALL_SIZE = 20;
const EASE = 0.18;
const HOVER_SCALE = 1.4;

@Component({
  selector: 'app-dpu-cursor-dot',
  standalone: true,
  template: '',
})
export class DpuCursorDotComponent implements AfterViewInit, OnDestroy {
  private targetX = 0;
  private targetY = 0;
  private x = 0;
  private y = 0;
  private scale = 1;
  private targetScale = 1;
  private frame = 0;
  private visible = false;
  private enabled = false;

  @HostBinding('class.dpu-cursor-dot')
  readonly hostClass = true;

  @HostBinding('attr.aria-hidden')
  readonly ariaHidden = 'true';

  constructor(
    private readonly el: ElementRef<HTMLElement>,
    private readonly zone: NgZone,
  ) {}

  ngAfterViewInit(): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (window.matchMedia('(pointer: coarse), (prefers-reduced-motion: reduce)').matches) {
      return;
    }
    this.enabled = true;
    document.documentElement.classList.add('dpu-landing-cursor');

    this.zone.runOutsideAngular(() => {
      document.addEventListener('pointermove', this.onMove, { passive: true });
      document.documentElement.addEventListener('pointerleave', this.onLeave);
    });
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.frame);
    document.removeEventListener('pointermove', this.onMove);
    document.documentElement.removeEventListener('pointerleave', this.onLeave);
    if (this.enabled) {
      document.documentElement.classList.remove('dpu-landing-cursor');
    }
  }

  private readonly onMove = (event: PointerEvent): void => {
    this.targetX = event.clientX - BALL_SIZE / 2;
    this.targetY = event.clientY - BALL_SIZE / 2;
    const target = event.target as Element | null;
    this.targetScale = target?.closest('a, button, input, textarea, [role="button"]')
      ? HOVER_SCALE
      : 1;

    if (!this.visible) {
      this.visible = true;
      this.x = this.targetX;
      this.y = this.targetY;
      this.el.nativeElement.style.opacity = '0.85';
      this.frame = requestAnimationFrame(this.tick);
    }
  };

  private readonly onLeave = (): void => {
    this.visible = false;
    cancelAnimationFrame(this.frame);
    this.el.nativeElement.style.opacity = '0';
  };

  private readonly tick = (): void => {
    this.x += (this.targetX - this.x) * EASE;
    this.y += (this.targetY - this.y) * EASE;
    this.scale += (this.targetScale - this.scale) * EASE;
    this.el.nativeElement.style.transform = `translate3d(${this.x}px, ${this.y}px, 0) scale(${this.scale})`;
    if (this.visible) {
      this.frame = requestAnimationFrame(this.tick);
    }
  };
}
