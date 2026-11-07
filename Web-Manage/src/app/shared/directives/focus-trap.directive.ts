import {
  AfterViewInit,
  Directive,
  ElementRef,
  HostListener,
  Input,
  OnDestroy,
} from '@angular/core';

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Traps Tab focus inside the host while `appFocusTrap` is truthy (dialogs / consent). */
@Directive({
  selector: '[appFocusTrap]',
  standalone: true,
})
export class FocusTrapDirective implements AfterViewInit, OnDestroy {
  @Input('appFocusTrap') enabled: boolean | '' = true;

  private previouslyFocused: HTMLElement | null = null;

  constructor(private readonly host: ElementRef<HTMLElement>) {}

  private isActive(): boolean {
    return this.enabled !== false && this.enabled !== null;
  }

  ngAfterViewInit(): void {
    if (!this.isActive()) {
      return;
    }
    this.previouslyFocused = document.activeElement as HTMLElement | null;
    queueMicrotask(() => this.focusFirst());
  }

  ngOnDestroy(): void {
    this.previouslyFocused?.focus?.();
  }

  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (!this.isActive() || event.key !== 'Tab') {
      return;
    }
    const nodes = this.focusable();
    if (nodes.length === 0) {
      event.preventDefault();
      return;
    }
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    const active = document.activeElement as HTMLElement | null;
    if (event.shiftKey) {
      if (active === first || !this.host.nativeElement.contains(active)) {
        event.preventDefault();
        last.focus();
      }
    } else if (active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  private focusable(): HTMLElement[] {
    return Array.from(
      this.host.nativeElement.querySelectorAll<HTMLElement>(FOCUSABLE),
    ).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1 && el.offsetParent !== null);
  }

  private focusFirst(): void {
    const nodes = this.focusable();
    (nodes[0] || this.host.nativeElement).focus();
  }
}
