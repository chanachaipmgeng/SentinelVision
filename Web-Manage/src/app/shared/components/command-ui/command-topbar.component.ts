import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

export type CommandAccent = 'cyan' | 'purple' | 'violet' | 'emerald' | 'amber' | 'sky';

/**
 * Reusable theme-aware operational hero topbar for SentinelVision command screens.
 * Supports VaultX Obsidian Glass (Dark) and Porcelain Glass (Light) automatically.
 */
@Component({
  selector: 'app-command-topbar',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sv-command-topbar sv-surface-topbar sv-motion-enter flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl shadow-xl">
      <div class="flex items-center gap-3 min-w-0">
        <div
          class="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0 border"
          [ngClass]="iconTileClass"
        >
          <i [class]="icon"></i>
        </div>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold border"
              [ngClass]="badgeClass"
            >
              <span class="w-1.5 h-1.5 rounded-full animate-pulse" [ngClass]="dotClass"></span>
              {{ badgeText }}
            </span>
            <span *ngIf="lastUpdated" class="text-[11px] sv-text-muted">
              อัปเดตล่าสุด: {{ lastUpdated | date: 'HH:mm:ss' }}
            </span>
          </div>
          <h2 class="text-base font-bold sv-text-primary mt-0.5 mb-0 truncate">{{ title }}</h2>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <ng-content select="[actions]"></ng-content>
      </div>
    </div>
  `,
})
export class CommandTopbarComponent {
  @Input() icon = 'ri-pulse-line';
  @Input() accent: CommandAccent = 'cyan';
  @Input() badgeText = 'LIVE TELEMETRY';
  @Input() title = '';
  @Input() lastUpdated: Date | string | null = null;

  get iconTileClass(): string {
    switch (this.accent) {
      case 'purple':
        return 'bg-purple-500/10 border-purple-500/30 text-purple-500 dark:text-purple-400';
      case 'violet':
        return 'bg-violet-500/10 border-violet-500/30 text-violet-500 dark:text-violet-400';
      case 'emerald':
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400';
      case 'amber':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400';
      case 'sky':
        return 'bg-sky-500/10 border-sky-500/30 text-sky-600 dark:text-sky-400';
      default:
        return 'bg-cyan-500/10 border-cyan-500/30 text-cyan-600 dark:text-cyan-400';
    }
  }

  get badgeClass(): string {
    return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30';
  }

  get dotClass(): string {
    return 'bg-emerald-500 dark:bg-emerald-400';
  }
}
