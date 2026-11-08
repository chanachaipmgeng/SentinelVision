import { Component, EventEmitter, HostListener, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../services/token.service';
import { PermissionService } from '../../services/permission.service';

export const WELCOME_SEEN_PREFIX = 'sv_welcome_seen:';

/** First-run 3-step intro for company admins (once per user, stored in localStorage). */
@Component({
  selector: 'app-welcome-wizard',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './welcome-wizard.component.html',
  styleUrl: './welcome-wizard.component.css',
})
export class WelcomeWizardComponent implements OnInit {
  /** Fired when the user picks "open checklist" on the final step. */
  @Output() openChecklist = new EventEmitter<void>();

  open = false;
  step = 0;
  readonly lastStep = 2;

  readonly modules = [
    { icon: 'ri-building-2-line', title: 'shell.welcome.mod.core.title', hint: 'shell.welcome.mod.core.hint' },
    { icon: 'ri-time-line', title: 'shell.welcome.mod.attendance.title', hint: 'shell.welcome.mod.attendance.hint' },
    { icon: 'ri-door-lock-line', title: 'shell.welcome.mod.access.title', hint: 'shell.welcome.mod.access.hint' },
    { icon: 'ri-shield-star-line', title: 'shell.welcome.mod.watchlist.title', hint: 'shell.welcome.mod.watchlist.hint' },
    { icon: 'ri-user-shared-line', title: 'shell.welcome.mod.visitor.title', hint: 'shell.welcome.mod.visitor.hint' },
    { icon: 'ri-calendar-event-line', title: 'shell.welcome.mod.events.title', hint: 'shell.welcome.mod.events.hint' },
  ];

  constructor(private tokenService: TokenService, private permissions: PermissionService) {}

  private get storageKey(): string | null {
    const memberId = this.tokenService.getUser()?.member?.memberId;
    return memberId ? WELCOME_SEEN_PREFIX + memberId : null;
  }

  ngOnInit(): void {
    const key = this.storageKey;
    if (!key) return;
    if (!(this.permissions.isCompanyAdmin() || this.permissions.isSystemAdmin())) return;
    try {
      this.open = localStorage.getItem(key) !== '1';
    } catch {
      this.open = false;
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) this.finish();
  }

  next(): void {
    if (this.step < this.lastStep) this.step++;
  }

  back(): void {
    if (this.step > 0) this.step--;
  }

  finish(goToChecklist = false): void {
    this.open = false;
    const key = this.storageKey;
    if (key) {
      try {
        localStorage.setItem(key, '1');
      } catch {
        /* ignore */
      }
    }
    if (goToChecklist) this.openChecklist.emit();
  }
}
