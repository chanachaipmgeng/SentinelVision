import { Component, HostListener, input, output } from '@angular/core';

/** Fullscreen VaultX Obsidian Glass lightbox for incident snapshots, face evidence, and diagrams. */
@Component({
  selector: 'app-lightbox',
  standalone: true,
  template: `
    <div
      class="sv-lightbox"
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="label()"
      (click)="closed.emit()"
    >
      <button
        type="button"
        class="sv-lightbox__close"
        (click)="closed.emit(); $event.stopPropagation()"
      >
        <i class="ri-close-line"></i>
        <span>{{ closeLabel() }}</span>
      </button>
      <figure class="sv-lightbox__figure" (click)="$event.stopPropagation()">
        <img [src]="url()" [alt]="alt()" />
        @if (caption()) {
          <figcaption class="sv-lightbox__caption">{{ caption() }}</figcaption>
        }
      </figure>
    </div>
  `,
  styles: [
    `
      .sv-lightbox {
        position: fixed;
        inset: 0;
        z-index: 1200;
        display: grid;
        place-items: center;
        padding: 1.5rem;
        background: rgba(4, 8, 15, 0.86);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
      }

      .sv-lightbox__close {
        position: absolute;
        top: 1rem;
        right: 1rem;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.5rem 0.9rem;
        border-radius: 9999px;
        border: 1px solid rgba(148, 163, 184, 0.28);
        background: rgba(7, 13, 20, 0.92);
        color: #f1f5f9;
        font: inherit;
        font-size: 0.875rem;
        font-weight: 600;
        cursor: pointer;
        transition: border-color 0.2s ease, background 0.2s ease;
      }

      .sv-lightbox__close:hover {
        border-color: var(--dpu-brand-hover, #14b8a6);
        background: rgba(15, 23, 42, 0.96);
      }

      .sv-lightbox__figure {
        margin: 0;
        max-width: min(64rem, 100%);
        max-height: calc(100vh - 3rem);
        overflow: auto;
        border-radius: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: #070d14;
        padding: 0.75rem;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
      }

      .sv-lightbox__figure img {
        display: block;
        width: 100%;
        height: auto;
        max-height: calc(100vh - 7.5rem);
        object-fit: contain;
        border-radius: 0.65rem;
      }

      .sv-lightbox__caption {
        margin-top: 0.65rem;
        padding: 0 0.25rem;
        color: #cbd5e1;
        font-size: 0.875rem;
      }
    `,
  ],
})
export class LightboxComponent {
  readonly url = input.required<string>();
  readonly alt = input('');
  readonly caption = input<string | null | undefined>(null);
  readonly label = input('Image preview');
  readonly closeLabel = input('Close');
  readonly closed = output<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closed.emit();
  }
}
