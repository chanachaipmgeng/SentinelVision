import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import { downloadMusterCsv } from '../sentinel.helpers';
import { SentinelEdgeManifest, SentinelMusterRollItem, SentinelOverview } from '../sentinel.models';

@Component({
    selector: 'app-sentinel-muster-panel',
    imports: [CommonModule],
    templateUrl: './sentinel-muster-panel.component.html'
})
export class SentinelMusterPanelComponent implements OnInit, OnChanges {
  @Input() overview: SentinelOverview | null = null;

  companyId = '';
  edgeManifest: SentinelEdgeManifest | null = null;
  musterItems: SentinelMusterRollItem[] = [];
  musterTotal = 0;
  musterWorkDate: string | null = null;
  musterLoading = false;
  musterLimit = 100;
  musterOffset = 0;
  safeKeys = new Set<string>();

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEdgeManifest();
    this.applyOverviewMuster(this.overview);
    this.refreshMuster();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['overview'] && changes['overview'].currentValue) {
      this.applyOverviewMuster(changes['overview'].currentValue);
    }
  }

  private applyOverviewMuster(ov: SentinelOverview | null): void {
    if (!ov) return;
    if (Array.isArray(ov.musterRoll)) {
      this.musterItems = ov.musterRoll;
    }
    const meta = ov.musterMeta || {};
    if (meta.total != null) this.musterTotal = Number(meta.total) || this.musterItems.length;
    else this.musterTotal = this.musterItems.length;
    if (meta.workDate) this.musterWorkDate = meta.workDate;
  }

  loadEdgeManifest(): void {
    if (!this.companyId) return;
    this.api.getEdgeSync(this.companyId).subscribe((res) => (this.edgeManifest = res));
  }

  refreshMuster(): void {
    if (!this.companyId) return;
    this.musterLoading = true;
    this.api
      .getMuster(this.companyId, { limit: this.musterLimit, offset: this.musterOffset })
      .subscribe({
        next: (res) => {
          this.musterLoading = false;
          this.musterItems = res?.items || [];
          this.musterTotal = Number(res?.total || 0);
          this.musterWorkDate = res?.workDate || this.musterWorkDate;
          this.musterLimit = Number(res?.limit || this.musterLimit);
          this.musterOffset = Number(res?.offset || 0);
        },
        error: () => {
          this.musterLoading = false;
        },
      });
  }

  nextPage(): void {
    if (this.musterOffset + this.musterLimit >= this.musterTotal) return;
    this.musterOffset += this.musterLimit;
    this.refreshMuster();
  }

  prevPage(): void {
    if (this.musterOffset <= 0) return;
    this.musterOffset = Math.max(0, this.musterOffset - this.musterLimit);
    this.refreshMuster();
  }

  personKey(person: SentinelMusterRollItem): string {
    return `${person.category}:${person.badgeCode || person.fullName}`;
  }

  isSafe(person: SentinelMusterRollItem): boolean {
    return this.safeKeys.has(this.personKey(person));
  }

  toggleSafe(person: SentinelMusterRollItem): void {
    const key = this.personKey(person);
    if (this.safeKeys.has(key)) {
      this.safeKeys.delete(key);
    } else {
      this.safeKeys.add(key);
    }
  }

  get safeCount(): number {
    return this.musterItems.filter((p) => this.isSafe(p)).length;
  }

  exportMusterCsv(): void {
    downloadMusterCsv(this.musterItems, this.safeKeys, (p) => this.personKey(p));
  }
}
