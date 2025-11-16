import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-cards',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './cards.component.html',
  styleUrls: ['./cards.component.scss']
})
export class CardsComponent {
  toggleClass = 'box-fullscreen';
  public fullScreen: boolean = true;

  fullScreenToggle() {
    document
      .querySelector('.fullscreentoggle')
      ?.classList.toggle('box-fullscreen');

  }
}
