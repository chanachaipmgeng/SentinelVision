import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-live-auction',
  standalone: true,
  imports: [SharedModule,NgSelectModule],
  templateUrl: './live-auction.component.html',
  styleUrls: ['./live-auction.component.scss']
})
export class LiveAuctionComponent {

}
