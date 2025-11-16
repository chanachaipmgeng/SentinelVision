import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-market-place',
  standalone: true,
  imports: [SharedModule,NgSelectModule],
  templateUrl: './market-place.component.html',
  styleUrls: ['./market-place.component.scss']
})
export class MarketPlaceComponent {

}
