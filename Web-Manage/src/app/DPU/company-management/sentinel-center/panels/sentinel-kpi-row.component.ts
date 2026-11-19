import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SentinelOverview } from '../sentinel.models';
import { BentoGridComponent, BentoStatComponent } from '../../../../shared/components/bento';

@Component({
    selector: 'app-sentinel-kpi-row',
    imports: [CommonModule, BentoGridComponent, BentoStatComponent],
    templateUrl: './sentinel-kpi-row.component.html'
})
export class SentinelKpiRowComponent {
  @Input() overview: SentinelOverview | null = null;
}
