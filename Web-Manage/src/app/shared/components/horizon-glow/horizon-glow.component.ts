import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  input,
  viewChild,
} from '@angular/core';

import { preferReducedMotion } from '../../utils/motion';

interface HorizonParticle {
  x: number;
  y: number;
  radius: number;
  speedY: number;
  speedX: number;
  alpha: number;
}

/** Rising cyan/teal particles + horizon hairline for Login / Landing / Kiosk idle. */
@Component({
  selector: 'app-horizon-glow',
  standalone: true,
  template: `
    <div class="sv-horizon" aria-hidden="true">
      <div class="sv-horizon__pulse"></div>
      <canvas #canvas class="sv-horizon__canvas"></canvas>
      <div class="sv-horizon__line"></div>
    </div>
  `,
  styles: `
    :host {
      display: block;
      pointer-events: none;
    }
    .sv-horizon {
      position: relative;
      display: flex;
      height: 220px;
      width: 100%;
      flex-direction: column;
      justify-content: flex-end;
      overflow: hidden;
      user-select: none;
      pointer-events: none;
    }
    .sv-horizon__pulse {
      position: absolute;
      bottom: 0;
      left: 50%;
      height: 180px;
      width: min(760px, 100%);
      translate: -50% 0;
      background: radial-gradient(
        ellipse at bottom,
        rgba(20, 184, 166, 0.28) 0%,
        rgba(56, 189, 248, 0.08) 45%,
        transparent 75%
      );
      animation: sv-pulse-horizon 6s ease-in-out infinite;
    }
    .sv-horizon__canvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      mask-image: radial-gradient(ellipse at bottom, black 30%, transparent 72%);
      -webkit-mask-image: radial-gradient(ellipse at bottom, black 30%, transparent 72%);
    }
    .sv-horizon__line {
      position: relative;
      height: 1px;
      width: 100%;
      background: linear-gradient(to right, transparent, var(--dpu-brand-hover, #14b8a6), transparent);
      opacity: 0.85;
      box-shadow: 0 0 20px 2px rgba(20, 184, 166, 0.55);
    }
    @keyframes sv-pulse-horizon {
      0%,
      100% {
        opacity: 0.72;
        transform: scaleX(0.96);
      }
      50% {
        opacity: 1;
        transform: scaleX(1.04);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .sv-horizon__pulse {
        animation: none;
      }
    }
  `,
})
export class HorizonGlowComponent implements AfterViewInit, OnDestroy {
  readonly count = input(55);
  private readonly canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');

  private ctx: CanvasRenderingContext2D | null = null;
  private particles: HorizonParticle[] = [];
  private width = 0;
  private height = 0;
  private frame = 0;
  private running = false;
  private resizeObserver?: ResizeObserver;
  private visibilityObserver?: IntersectionObserver;

  ngAfterViewInit(): void {
    if (typeof window === 'undefined' || preferReducedMotion()) {
      return;
    }

    const canvas = this.canvasRef().nativeElement;
    this.ctx = canvas.getContext('2d');
    if (!this.ctx) {
      return;
    }

    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(canvas);
    }
    this.resize();
    this.particles = Array.from({ length: this.count() }, () => this.createParticle(false));

    if (typeof IntersectionObserver !== 'undefined') {
      this.visibilityObserver = new IntersectionObserver(([entry]) =>
        entry?.isIntersecting ? this.start() : this.stop(),
      );
      this.visibilityObserver.observe(canvas);
    } else {
      this.start();
    }
  }

  ngOnDestroy(): void {
    this.stop();
    this.resizeObserver?.disconnect();
    this.visibilityObserver?.disconnect();
  }

  private resize(): void {
    const canvas = this.canvasRef().nativeElement;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = Math.max(1, canvas.offsetWidth);
    this.height = Math.max(1, canvas.offsetHeight);
    canvas.width = this.width * dpr;
    canvas.height = this.height * dpr;
    this.ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  private createParticle(atHorizon: boolean): HorizonParticle {
    return {
      x: this.width * 0.12 + Math.random() * this.width * 0.76,
      y: atHorizon ? this.height : Math.random() * this.height,
      radius: Math.random() * 1.5 + 0.7,
      speedY: Math.random() * 0.35 + 0.12,
      speedX: (Math.random() - 0.5) * 0.14,
      alpha: Math.random() * 0.75 + 0.2,
    };
  }

  private start(): void {
    if (this.running) {
      return;
    }
    this.running = true;
    this.frame = requestAnimationFrame(this.tick);
  }

  private stop(): void {
    this.running = false;
    cancelAnimationFrame(this.frame);
  }

  private readonly tick = (): void => {
    const ctx = this.ctx;
    if (!ctx || !this.running) {
      return;
    }

    ctx.clearRect(0, 0, this.width, this.height);
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      p.y -= p.speedY;
      p.x += p.speedX;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(45, 212, 191, ${p.alpha * (p.y / Math.max(this.height, 1))})`;
      ctx.fill();

      if (p.y <= 10) {
        this.particles[i] = this.createParticle(true);
      }
    }

    this.frame = requestAnimationFrame(this.tick);
  };
}
