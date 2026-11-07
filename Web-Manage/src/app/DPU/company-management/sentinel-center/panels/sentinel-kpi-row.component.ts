import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-sentinel-kpi-row',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sentinel-kpi-row.component.html',
})
export class SentinelKpiRowComponent {
  @Input() overview: any = null;
}
