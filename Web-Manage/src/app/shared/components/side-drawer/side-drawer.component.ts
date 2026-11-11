import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Inject,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule, DOCUMENT } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

let nextId = 0;
let openDrawers = 0;
let savedBodyOverflow = '';

const FOCUSABLE =
  'a[href], area[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
  'select:not([disabled]), textarea:not([disabled]), iframe, [tabindex]:not([tabindex="-1"]), ' +
  '[contenteditable="true"]';

/**
 * Right-hand detail drawer (full-screen sheet below 640px).
 *
 * The host element is re-parented to `<body>` so `position: fixed` is not trapped by
 * transformed ancestors (`animate-in`, `modern-card`). Projected content therefore cannot
 * rely on page-ancestor CSS selectors.
 *
 * Slots: default content, `[drawerHeaderActions]`, `[drawerFooter]` (sticky).
 */
@Component({
    selector: 'app-side-drawer',
    imports: [CommonModule, TranslateModule],
    templateUrl: './side-drawer.component.html',
    styleUrls: ['./side-drawer.component.css']
})
export class SideDrawerComponent implements OnChanges, AfterViewInit, OnDestroy {
  @Input() open = false;
  @Input() title = '';
  @Input() subtitle = '';
  @Input() size: 'md' | 'lg' = 'md';
  @Input() closeOnBackdrop = true;
  /** Show the sticky footer region (content via `[drawerFooter]`). */
  @Input() showFooter = true;
  @Output() openChange = new EventEmitter<boolean>();
  @Output() closed = new EventEmitter<void>();

  @ViewChild('panel') panel?: ElementRef<HTMLElement>;

  readonly titleId = `dpu-drawer-title-${++nextId}`;
  private restoreFocus: HTMLElement | null = null;
  private locked = false;

  constructor(
    private host: ElementRef<HTMLElement>,
    @Inject(DOCUMENT) private doc: Document
  ) {}

  ngAfterViewInit(): void {
    this.doc.body.appendChild(this.host.nativeElement);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes['open']) return;
    if (this.open) this.onOpened();
    else if (!changes['open'].firstChange) this.onClosed();
  }

  ngOnDestroy(): void {
    if (this.open) this.onClosed();
    this.host.nativeElement.remove();
  }

  close(): void {
    if (!this.open) return;
    this.open = false;
    this.onClosed();
    this.openChange.emit(false);
    this.closed.emit();
  }

  onBackdrop(): void {
    if (this.closeOnBackdrop) this.close();
  }

  @HostListener('document:keydown.escape', ['$event'])
  onEscape(ev: Event): void {
    if (!this.open) return;
    // Leave Esc to overlays stacked above the drawer (sweetalert, ng-select, flatpickr).
    const active = this.doc.activeElement;
    if (active && active !== this.doc.body && !this.panel?.nativeElement.contains(active)) return;
    ev.preventDefault();
    this.close();
  }

  onPanelKeydown(ev: KeyboardEvent): void {
    if (ev.key !== 'Tab' || !this.panel) return;
    const nodes = this.focusables();
    if (!nodes.length) {
      ev.preventDefault();
      this.panel.nativeElement.focus();
      return;
    }
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    const active = this.doc.activeElement;
    if (ev.shiftKey && (active === first || active === this.panel.nativeElement)) {
      ev.preventDefault();
      last.focus();
    } else if (!ev.shiftKey && active === last) {
      ev.preventDefault();
      first.focus();
    }
  }

  private onOpened(): void {
    const active = this.doc.activeElement;
    if (!this.restoreFocus && active instanceof HTMLElement && active !== this.doc.body) {
      this.restoreFocus = active;
    }
    this.lockScroll();
    setTimeout(() => {
      if (!this.open || !this.panel) return;
      const panel = this.panel.nativeElement;
      if (panel.contains(this.doc.activeElement)) return;
      const preferred = panel.querySelector<HTMLElement>('[cdkFocusInitial], [data-autofocus]');
      (preferred || panel.querySelector<HTMLElement>('.dpu-drawer__close') || panel).focus();
    });
  }

  private onClosed(): void {
    this.unlockScroll();
    const target = this.restoreFocus;
    this.restoreFocus = null;
    if (target && this.doc.contains(target)) setTimeout(() => target.focus());
  }

  private focusables(): HTMLElement[] {
    const panel = this.panel?.nativeElement;
    if (!panel) return [];
    return Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null || el === this.doc.activeElement
    );
  }

  private lockScroll(): void {
    if (this.locked) return;
    this.locked = true;
    if (openDrawers++ === 0) {
      savedBodyOverflow = this.doc.body.style.overflow;
      this.doc.body.style.overflow = 'hidden';
    }
  }

  private unlockScroll(): void {
    if (!this.locked) return;
    this.locked = false;
    if (--openDrawers === 0) this.doc.body.style.overflow = savedBodyOverflow;
  }
}
