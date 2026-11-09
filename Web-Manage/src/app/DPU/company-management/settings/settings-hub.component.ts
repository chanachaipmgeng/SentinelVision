import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, ViewEncapsulation } from '@angular/core';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Subscription, combineLatest } from 'rxjs';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { PermissionService } from '../../../shared/services/permission.service';
import { SharedModule } from '../../../shared/shared.module';
import { HrPdpaTabComponent } from '../hr-schedule/tabs/hr-pdpa-tab.component';
import { HrSecurityTabComponent } from '../hr-schedule/tabs/hr-security-tab.component';
import { AiSettingsPanelComponent } from './panels/ai-settings-panel.component';
import { ApiKeysPanelComponent } from './panels/api-keys-panel.component';
import { DevicesSummaryPanelComponent } from './panels/devices-summary-panel.component';
import { IncidentSlaSettingsPanelComponent } from './panels/incident-sla-settings-panel.component';
import { NotificationSettingsPanelComponent } from './panels/notification-settings-panel/notification-settings-panel.component';
import { ScanActionsSummaryPanelComponent } from './panels/scan-actions-summary-panel.component';
import { SessionSettingsPanelComponent } from './panels/session-settings-panel.component';
import {
  SHIFT_LINK_CARDS,
  SettingsSection,
  resolveSettingsSection,
  visibleSettingsSections,
} from './settings-hub.sections';

/** Company settings hub: `/company/settings/:section` with a permission-filtered section rail. */
@Component({
  selector: 'app-settings-hub',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    SharedModule,
    PageToolbarComponent,
    StatChipComponent,
    EmptyStateComponent,
    NotificationSettingsPanelComponent,
    IncidentSlaSettingsPanelComponent,
    AiSettingsPanelComponent,
    SessionSettingsPanelComponent,
    ApiKeysPanelComponent,
    ScanActionsSummaryPanelComponent,
    DevicesSummaryPanelComponent,
    HrSecurityTabComponent,
    HrPdpaTabComponent,
  ],
  templateUrl: './settings-hub.component.html',
  styleUrls: ['./settings-hub.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class SettingsHubComponent implements OnInit, OnDestroy {
  readonly shiftCards = SHIFT_LINK_CARDS;

  sections: SettingsSection[] = [];
  active: SettingsSection | null = null;
  permissionsReady = false;
  statusMsg = '';

  private sub?: Subscription;
  private statusTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private permissions: PermissionService,
  ) {}

  ngOnInit(): void {
    this.permissions.loadForSelectedCompany().subscribe();
    this.sub = combineLatest([this.route.paramMap, this.permissions.watch()]).subscribe(
      ([params, snap]) => {
        this.permissionsReady = snap != null;
        if (!this.permissionsReady) return;
        this.sections = visibleSettingsSections((p) => this.permissions.has(p));
        const requested = params.get('section');
        const resolved = resolveSettingsSection(requested, this.sections);
        if (resolved && resolved !== requested) {
          void this.router.navigate(['/company/settings', resolved], { replaceUrl: true });
          return;
        }
        if (this.active?.id !== resolved) this.statusMsg = '';
        this.active = this.sections.find((s) => s.id === resolved) ?? null;
      },
    );
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    if (this.statusTimer) clearTimeout(this.statusTimer);
  }

  flash(msg: string): void {
    this.statusMsg = msg;
    if (this.statusTimer) clearTimeout(this.statusTimer);
    this.statusTimer = setTimeout(() => {
      if (this.statusMsg === msg) this.statusMsg = '';
    }, 3500);
  }

  trackSection(_: number, s: SettingsSection): string {
    return s.id;
  }
}
