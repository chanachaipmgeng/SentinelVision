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

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEdgeManifest();
    if (!this.overview) {
      this.api.getOverview(this.companyId).subscribe((res) => (this.overview = res));
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['overview'] && changes['overview'].currentValue) {
      // parent refreshed KPI overview — muster roll updates via binding
    }
  }

  loadEdgeManifest(): void {
    if (!this.companyId) return;
    this.api.getEdgeSync(this.companyId).subscribe((res) => (this.edgeManifest = res));
  }
}
