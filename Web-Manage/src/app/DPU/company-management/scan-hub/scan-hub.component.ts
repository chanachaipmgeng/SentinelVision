import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

/**
 * Minimal Phase-2 placeholder for `/company/scan-hub`.
 * Phase 3 replaces this with the full Scan & Action Hub UI.
 */
@Component({
  selector: 'app-scan-hub',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="box modern-card glass p-6">
      <h1 class="text-xl font-semibold mb-2">Scan &amp; Action Hub</h1>
      <p class="text-sm text-dpu-muted mb-4">
        ศูนย์เลือกโหมดสแกนและตั้งค่าโมดูล (Phase 3 จะเติม UI เต็มรูปแบบ)
      </p>
      <ul class="list-disc ps-5 space-y-1 text-sm">
        <li><a routerLink="/company/scan/attendance" class="text-teal-700 underline">Attendance</a></li>
        <li><a routerLink="/company/scan/access-control" class="text-teal-700 underline">Access Control</a></li>
        <li><a routerLink="/company/scan/watchlist" class="text-teal-700 underline">Watchlist</a></li>
        <li><a routerLink="/company/scan/visitor" class="text-teal-700 underline">Visitor</a></li>
        <li><a routerLink="/company/scan/event" class="text-teal-700 underline">Event</a></li>
      </ul>
    </div>
  `,
})
export class ScanHubComponent {}
