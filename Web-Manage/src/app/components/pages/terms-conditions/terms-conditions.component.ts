import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';

@Component({
  selector: 'app-terms-conditions',
  standalone: true,
  imports: [SharedModule,SimplebarAngularModule],
  templateUrl: './terms-conditions.component.html',
  styleUrls: ['./terms-conditions.component.scss']
})
export class TermsConditionsComponent {

  toggleClass = 'box-fullscreen';
  public fullScreen: boolean = true;

  fullScreenToggle() {
    document
      .querySelector('.fullscreentoggle')
      ?.classList.toggle('box-fullscreen');

  }

}
