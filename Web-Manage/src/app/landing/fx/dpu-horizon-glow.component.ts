import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnDestroy,
  ViewChild,
} from '@angular/core';

interface Particle {
  x: number;
  y: number;
  radius: number;
  speedY: number;
  speedX: number;
  alpha: number;
}

@Component({
  selector: 'app-dpu-horizon-glow',
  standalone: true,
  template: `
    <div class="dpu-horizon" aria-hidden="true">
      <div class="dpu-horizon__bloom"></div>
      <canvas #canvas class="dpu-horizon__canvas"></canvas>
      <div class="dpu-horizon__line"></div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
    `,
  ],
})
export class DpuHorizonGlowComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;
  @Input() count = 65;

  private ctx: CanvasRenderingContext2D | null = null;
  private particles: Particle[] = [];
  private width = 0;
  private height = 0;
  private frame = 0;
  private running = false;
  private resizeObserver?: ResizeObserver;
  private visibilityObserver?: IntersectionObserver;

  constructor(private readonly zone: NgZone) {}

  ngAfterViewInit(): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d');
    if (!this.ctx) {
      return;
    }

    this.zone.runOutsideAngular(() => {
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(canvas);
      this.resize();
      this.particles = Array.from({ length: this.count || 65 }, () => this.createParticle(false));

      this.visibilityObserver = new IntersectionObserver(([entry]) =>
        entry.isIntersecting ? this.start() : this.stop(),
      );
      this.visibilityObserver.observe(canvas);
    });
  }

  ngOnDestroy(): void {
    this.stop();
    this.resizeObserver?.disconnect();
    this.visibilityObserver?.disconnect();
  }

  private resize(): void {
    const canvas = this.canvasRef.nativeElement;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = canvas.offsetWidth;
    this.height = canvas.offsetHeight;
    canvas.width = this.width * dpr;
    canvas.height = this.height * dpr;
    this.ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  private createParticle(atHorizon: boolean): Particle {
    return {
      x: this.width * 0.15 + Math.random() * this.width * 0.7,
      y: atHorizon ? this.height : Math.random() * this.height,
      radius: Math.random() * 1.5 + 0.8,
      speedY: Math.random() * 0.35 + 0.1,
      speedX: (Math.random() - 0.5) * 0.15,
      alpha: Math.random() * 0.8 + 0.2,
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
      // Teal remapped particle (was indigo rgba(115,130,255))
      ctx.fillStyle = `rgba(94, 234, 212, ${p.alpha * (p.y / Math.max(this.height, 1))})`;
      ctx.fill();

      if (p.y <= 10) {
        this.particles[i] = this.createParticle(true);
      }
    }

    this.frame = requestAnimationFrame(this.tick);
  };
}
