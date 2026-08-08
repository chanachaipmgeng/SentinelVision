import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-page-toolbar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="box dpu-toolbar modern-card glass animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div class="box-header dpu-toolbar__header">
        <div class="dpu-toolbar__inner">
          <div class="dpu-toolbar__title">
            <div class="box-title !mb-0">{{ title }}</div>
            <ng-content select="[chips]"></ng-content>
          </div>
          <div class="dpu-toolbar__controls">
            <ng-content select="[controls]"></ng-content>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .dpu-toolbar .box-header,
      .dpu-toolbar__header {
        border-bottom: none !important;
        padding: 0.9rem 1.1rem !important;
        display: block !important;
      }
      .dpu-toolbar__inner {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.75rem 1rem;
        width: 100%;
      }
      .dpu-toolbar__title {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.4rem 0.5rem;
      }
      .dpu-toolbar__controls {
        display: flex;
        flex: 1 1 16rem;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.5rem;
        justify-content: flex-end;
        min-width: 0;
      }
    `,
  ],
})
export class PageToolbarComponent {
  @Input() title = '';
}
