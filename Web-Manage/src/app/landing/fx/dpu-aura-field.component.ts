import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
    selector: 'app-dpu-aura-field',
    imports: [CommonModule],
    template: `
    <div class="dpu-aura" aria-hidden="true">
      <span
        class="dpu-aura__blob dpu-aura__blob--a"
        [class.dpu-aura__blob--strong]="intensity === 'strong'"
      ></span>
      <span
        class="dpu-aura__blob dpu-aura__blob--b"
        [class.dpu-aura__blob--strong]="intensity === 'strong'"
      ></span>
      <span class="dpu-aura__blob dpu-aura__blob--c"></span>

      @if (withParticles) {
        @for (spark of sparks; track $index) {
          <span
            class="dpu-aura__spark"
            [class.dpu-aura__spark--sm]="spark.small"
            [style.left.%]="spark.x"
            [style.top.%]="spark.y"
            [style.animation-delay.s]="spark.delay"
          ></span>
        }
      }
    </div>
  `,
    styles: [
        `
      :host {
        display: block;
        pointer-events: none;
      }
    `,
    ]
})
export class DpuAuraFieldComponent {
  @Input() intensity: 'soft' | 'strong' = 'soft';
  @Input() withParticles = true;

  readonly sparks = [
    { x: 18, y: 42, delay: 0.1, small: false },
    { x: 28, y: 58, delay: 0.7, small: true },
    { x: 42, y: 36, delay: 1.2, small: false },
    { x: 55, y: 62, delay: 0.4, small: true },
    { x: 66, y: 40, delay: 1.6, small: false },
    { x: 74, y: 55, delay: 0.9, small: true },
    { x: 36, y: 70, delay: 2, small: false },
    { x: 61, y: 30, delay: 1.4, small: true },
  ];
}
