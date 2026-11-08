import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';

@Component({
  selector: 'app-sentinel-muster-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sentinel-muster-panel.component.html',
})
export class SentinelMusterPanelComponent implements OnInit, OnChanges {
  @Input() overview: any = null;

  companyId = '';
  edgeManifest: any = null;
  musterItems: any[] = [];
  musterTotal = 0;
  musterWorkDate: string | null = null;
  musterLoading = false;
  musterLimit = 100;
  musterOffset = 0;

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

  private applyOverviewMuster(ov: any): void {
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
}
