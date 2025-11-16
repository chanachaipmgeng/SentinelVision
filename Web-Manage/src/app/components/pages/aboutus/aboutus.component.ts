import { Component } from '@angular/core';
import { CountUpModule } from 'ngx-countup';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-aboutus',
  standalone: true,
  imports: [SharedModule,CountUpModule],
  templateUrl: './aboutus.component.html',
  styleUrls: ['./aboutus.component.scss']
})
export class AboutusComponent {

}
