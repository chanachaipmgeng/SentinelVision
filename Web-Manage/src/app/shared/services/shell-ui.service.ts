import { Injectable, signal } from '@angular/core';
import { Subject } from 'rxjs';

/** Open/close state for shell overlays shared between header and content-layout. */
@Injectable({ providedIn: 'root' })
export class ShellUiService {
  readonly paletteOpen = signal(false);
  readonly shortcutsOpen = signal(false);
  readonly notificationsOpen = signal(false);

  /** Emits when notification read state changes so the header badge can refresh. */
  readonly notificationsChanged$ = new Subject<void>();

  openPalette(): void {
    this.closeAll();
    this.paletteOpen.set(true);
  }

  openShortcuts(): void {
    this.closeAll();
    this.shortcutsOpen.set(true);
  }

  toggleNotifications(): void {
    const next = !this.notificationsOpen();
    this.closeAll();
    this.notificationsOpen.set(next);
  }

  closeAll(): void {
    this.paletteOpen.set(false);
    this.shortcutsOpen.set(false);
    this.notificationsOpen.set(false);
  }
}
