import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { firstValueFrom } from 'rxjs';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { PillSearchComponent } from '../../../shared/components/pill-search/pill-search.component';
import { SideDrawerComponent } from '../../../shared/components/side-drawer/side-drawer.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { TokenService } from '../../../shared/services/token.service';

export interface PresenceSearchItem {
  memberId: string;
  employeeId?: string;
  fullName: string;
  status: 'here' | 'last_seen' | 'not_seen';
  cameraId?: string | null;
  cameraName?: string | null;
  zoneId?: string | null;
  siteFloorId?: string | null;
  lastSeenAt?: string | null;
  sessionOpen?: boolean;
}

export interface PresenceSessionRow {
  sessionId: string;
  cameraId: string;
  cameraName?: string | null;
  presenceRole?: string;
  startedAt?: string | null;
  endedAt?: string | null;
  lastSeenAt?: string | null;
  sampleCount: number;
  open: boolean;
  dwellMinutes: number;
}

export interface OtEvidenceItem {
  memberId: string;
  fullName?: string | null;
  cameraOtMinutes: number;
  punchedOtMinutes: number;
  status: 'aligned' | 'punch_without_camera' | 'camera_without_punch';
}

@Component({
  selector: 'app-company-presence',
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    PageToolbarComponent,
    PillSearchComponent,
    StatChipComponent,
    EmptyStateComponent,
    SideDrawerComponent,
  ],
  templateUrl: './presence.component.html',
  styleUrls: ['../../../shared/styles/dpu-list-page.css', './presence.component.css'],
  encapsulation: ViewEncapsulation.None,
})
export class PresenceComponent implements OnInit {
  companyId = '';
  tab: 'locate' | 'ot' = 'locate';
  query = '';
  searching = false;
  loadingTrail = false;
  loadingOt = false;
  detailOpen = false;
  error: string | null = null;
  results: PresenceSearchItem[] = [];
  selected: PresenceSearchItem | null = null;
  trail: PresenceSessionRow[] = [];
  otItems: OtEvidenceItem[] = [];
  workDate = '';
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
    const today = new Date();
    this.workDate = today.toISOString().slice(0, 10);
  }

  ngOnInit(): void {
    // no auto-search
  }

  get hereCount(): number {
    return this.results.filter((r) => r.status === 'here').length;
  }

  onSearch(q: string): void {
    this.query = (q || '').trim();
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
    if (!this.companyId || this.query.length < 2) {
      this.results = [];
      return;
    }
    this.searchTimer = setTimeout(() => {
      void this.runSearch();
    }, 280);
  }

  private async runSearch(): Promise<void> {
    if (!this.companyId || this.query.length < 2) {
      return;
    }
    this.searching = true;
    this.error = null;
    try {
      const params = new HttpParams().set('q', this.query).set('limit', '20');
      const res = await firstValueFrom(
        this.http.get<{ items: PresenceSearchItem[] }>(
          `/presence/company/${this.companyId}/search`,
          { params }
        )
      );
      this.results = res?.items || [];
      if (this.selected) {
        const still = this.results.find((r) => r.memberId === this.selected!.memberId);
        this.selected = still || null;
      }
    } catch {
      this.error = 'presence.error';
      this.results = [];
    } finally {
      this.searching = false;
    }
  }

  async selectMember(item: PresenceSearchItem): Promise<void> {
    this.selected = item;
    this.detailOpen = true;
    this.loadingTrail = true;
    this.trail = [];
    try {
      const res = await firstValueFrom(
        this.http.get<{ sessions: PresenceSessionRow[] }>(
          `/presence/company/${this.companyId}/members/${item.memberId}/trail`
        )
      );
      this.trail = res?.sessions || [];
    } catch {
      this.error = 'presence.error';
    } finally {
      this.loadingTrail = false;
    }
  }

  async loadOt(): Promise<void> {
    if (!this.companyId) {
      return;
    }
    this.tab = 'ot';
    this.loadingOt = true;
    this.error = null;
    try {
      const params = new HttpParams().set('workDate', this.workDate);
      const res = await firstValueFrom(
        this.http.get<{ items: OtEvidenceItem[] }>(
          `/presence/company/${this.companyId}/ot-evidence`,
          { params }
        )
      );
      this.otItems = res?.items || [];
    } catch {
      this.error = 'presence.error';
      this.otItems = [];
    } finally {
      this.loadingOt = false;
    }
  }

  statusTone(status: string): 'ok' | 'warn' | 'soft' {
    if (status === 'here') {
      return 'ok';
    }
    if (status === 'last_seen') {
      return 'warn';
    }
    return 'soft';
  }

  otTone(status: string): 'ok' | 'warn' | 'soft' {
    if (status === 'aligned') {
      return 'ok';
    }
    return 'warn';
  }
}
