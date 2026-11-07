import { Directive, ElementRef, HostListener, Input } from '@angular/core';

/**
 * Arrow-key navigation for data tables.
 * Host should be a `<table>` (or wrap one). Rows with `[data-row-index]` or `tbody tr` are targets.
 */
@Directive({
  selector: '[appKeyboardTable]',
  standalone: true,
})
export class KeyboardTableDirective {
  /** Optional CSS selector for focusable row cells (default: tbody tr). */
  @Input() appKeyboardTable = 'tbody tr';

  constructor(private readonly host: ElementRef<HTMLElement>) {}

  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      return;
    }
    const rows = Array.from(
      this.host.nativeElement.querySelectorAll<HTMLElement>(
        this.appKeyboardTable || 'tbody tr',
      ),
    ).filter((r) => r.offsetParent !== null);
    if (rows.length === 0) {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    let idx = rows.findIndex((r) => r === active || r.contains(active));
    if (idx < 0) {
      idx = 0;
    }
    if (event.key === 'ArrowDown') {
      idx = Math.min(rows.length - 1, idx + 1);
    } else if (event.key === 'ArrowUp') {
      idx = Math.max(0, idx - 1);
    } else if (event.key === 'Home') {
      idx = 0;
    } else if (event.key === 'End') {
      idx = rows.length - 1;
    }
    event.preventDefault();
    const row = rows[idx];
    if (!row.hasAttribute('tabindex')) {
      row.setAttribute('tabindex', '0');
    }
    row.focus();
  }
}
