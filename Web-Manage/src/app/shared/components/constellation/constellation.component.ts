import { DOCUMENT } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  inject,
} from '@angular/core';

import { preferReducedMotion } from '../../utils/motion';

interface NodePt {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

/** Interactive biometric/neural constellation canvas for Login / Landing / Kiosk idle. */
@Component({
  selector: 'app-constellation',
  standalone: true,
  template: `<canvas #canvas class="sv-constellation" aria-hidden="true"></canvas>`,
  styles: `
    :host {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 0;
    }
    .sv-constellation {
      width: 100%;
      height: 100%;
      display: block;
    }
  `,
})
export class ConstellationComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  private readonly document = inject(DOCUMENT);
  private readonly host = inject(ElementRef<HTMLElement>);
  private nodes: NodePt[] = [];
  private raf = 0;
  private running = false;
  private width = 0;
  private height = 0;
  private dpr = 1;
  private pointer = { x: 0.5, y: 0.5, active: false };
  private io: IntersectionObserver | null = null;
  private visible = false;
  private readonly onResize = () => this.resize();
  private readonly onVis = () => {
    if (this.document.hidden) {
      this.stopLoop();
    } else if (this.visible) {
      this.startLoop();
    }
  };
  private readonly onPointer = (event: PointerEvent) => {
    const rect = this.host.nativeElement.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return;
    }
    this.pointer.x = (event.clientX - rect.left) / rect.width;
    this.pointer.y = (event.clientY - rect.top) / rect.height;
    this.pointer.active = true;
  };
  private readonly onLeave = () => {
    this.pointer.active = false;
  };

  ngAfterViewInit(): void {
    if (typeof window === 'undefined' || preferReducedMotion()) {
      this.canvasRef.nativeElement.style.display = 'none';
      return;
    }

    this.resize();
    this.seed();
    if (typeof IntersectionObserver !== 'undefined') {
      this.io = new IntersectionObserver(
        (entries) => {
          this.visible = entries.some((e) => e.isIntersecting);
          if (this.visible) {
            this.startLoop();
          } else {
            this.stopLoop();
          }
        },
        { threshold: 0.05 },
      );
      this.io.observe(this.host.nativeElement);
    } else {
      this.visible = true;
      this.startLoop();
    }

    window.addEventListener('resize', this.onResize, { passive: true });
    this.document.addEventListener('visibilitychange', this.onVis);
    this.host.nativeElement.parentElement?.addEventListener('pointermove', this.onPointer, {
      passive: true,
    });
    this.host.nativeElement.parentElement?.addEventListener('pointerleave', this.onLeave, {
      passive: true,
    });
  }

  ngOnDestroy(): void {
    this.stopLoop();
    this.io?.disconnect();
    window.removeEventListener('resize', this.onResize);
    this.document.removeEventListener('visibilitychange', this.onVis);
    this.host.nativeElement.parentElement?.removeEventListener('pointermove', this.onPointer);
    this.host.nativeElement.parentElement?.removeEventListener('pointerleave', this.onLeave);
  }

  private resize(): void {
    const canvas = this.canvasRef.nativeElement;
    const parent = this.host.nativeElement.parentElement;
    if (!parent) {
      return;
    }
    const rect = parent.getBoundingClientRect();
    this.width = Math.max(1, Math.floor(rect.width));
    this.height = Math.max(1, Math.floor(rect.height));
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(this.width * this.dpr);
    canvas.height = Math.floor(this.height * this.dpr);
    canvas.style.width = `${this.width}px`;
    canvas.style.height = `${this.height}px`;
  }

  private seed(): void {
    const count = this.width < 480 ? 24 : this.width < 900 ? 34 : 44;
    this.nodes = Array.from({ length: count }, () => ({
      x: Math.random(),
      y: Math.random(),
      vx: (Math.random() - 0.5) * 0.0003,
      vy: (Math.random() - 0.5) * 0.0003,
      r: 1.1 + Math.random() * 2.0,
    }));
  }

  private startLoop(): void {
    if (this.running) {
      return;
    }
    this.running = true;
    const tick = () => {
      if (!this.running) {
        return;
      }
      this.draw();
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  private stopLoop(): void {
    this.running = false;
    if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    }
  }

  private draw(): void {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);

    const accent =
      getComputedStyle(this.document.documentElement).getPropertyValue('--dpu-brand-hover').trim() ||
      '#14b8a6';
    const brand =
      getComputedStyle(this.document.documentElement).getPropertyValue('--dpu-brand').trim() ||
      '#0f766e';

    for (const n of this.nodes) {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0.02 || n.x > 0.98) {
        n.vx *= -1;
      }
      if (n.y < 0.02 || n.y > 0.98) {
        n.vy *= -1;
      }
      if (this.pointer.active) {
        const dx = this.pointer.x - n.x;
        const dy = this.pointer.y - n.y;
        const dist = Math.hypot(dx, dy) || 1;
        if (dist < 0.12) {
          n.vx -= (dx / dist) * 0.00009;
          n.vy -= (dy / dist) * 0.00009;
        } else if (dist < 0.32) {
          n.vx += (dx / dist) * 0.000035;
          n.vy += (dy / dist) * 0.000035;
        }
      }
      n.vx *= 0.995;
      n.vy *= 0.995;
    }

    const linkDist = 0.2;
    for (let i = 0; i < this.nodes.length; i++) {
      for (let j = i + 1; j < this.nodes.length; j++) {
        const a = this.nodes[i]!;
        const b = this.nodes[j]!;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const d = Math.hypot(dx, dy);
        if (d > linkDist) {
          continue;
        }
        const alpha = (1 - d / linkDist) * 0.42;
        ctx.strokeStyle = withAlpha(accent, alpha);
        ctx.lineWidth = 1 + (1 - d / linkDist) * 0.75;
        ctx.beginPath();
        ctx.moveTo(a.x * this.width, a.y * this.height);
        ctx.lineTo(b.x * this.width, b.y * this.height);
        ctx.stroke();
      }
    }

    for (const n of this.nodes) {
      const px = n.x * this.width;
      const py = n.y * this.height;
      const glow = ctx.createRadialGradient(px, py, 0, px, py, n.r * 5);
      glow.addColorStop(0, withAlpha(accent, 0.26));
      glow.addColorStop(1, withAlpha(accent, 0));
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(px, py, n.r * 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = withAlpha(brand, 0.48);
      ctx.beginPath();
      ctx.arc(px, py, n.r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = withAlpha(accent, 0.82);
      ctx.beginPath();
      ctx.arc(px, py, n.r * 0.45, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function withAlpha(color: string, alpha: number): string {
  if (color.startsWith('#') && (color.length === 7 || color.length === 4)) {
    const hex =
      color.length === 4
        ? `#${color[1]}${color[1]}${color[2]}${color[2]}${color[3]}${color[3]}`
        : color;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return color;
}
