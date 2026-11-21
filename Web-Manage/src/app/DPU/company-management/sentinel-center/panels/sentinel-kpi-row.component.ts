import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { SentinelOverview } from '../sentinel.models';
import { SentinelTab } from '../sentinel-routing';

@Component({
    selector: 'app-sentinel-kpi-row',
    imports: [CommonModule],
    templateUrl: './sentinel-kpi-row.component.html'
})
export class SentinelKpiRowComponent {
  @Input() overview: SentinelOverview | null = null;
  @Output() tabSelect = new EventEmitter<SentinelTab>();

  onStatClick(tab: SentinelTab): void {
    this.tabSelect.emit(tab);
  }
}
