import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SentinelOverview } from '../sentinel.models';

@Component({
    selector: 'app-sentinel-kpi-row',
    imports: [CommonModule],
    templateUrl: './sentinel-kpi-row.component.html'
})
export class SentinelKpiRowComponent {
  @Input() overview: SentinelOverview | null = null;
}
