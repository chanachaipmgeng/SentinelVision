import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [SharedModule,NgSelectModule,NgApexchartsModule],
  templateUrl: './wallet.component.html',
  styleUrls: ['./wallet.component.scss']
})
export class WalletComponent {

}
