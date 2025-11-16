import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { BarRatingModule } from 'ngx-bar-rating';

@Component({
  selector: 'app-rating',
  standalone: true,
  imports: [SharedModule,BarRatingModule],
  templateUrl: './rating.component.html',
  styleUrls: ['./rating.component.scss']
})
export class RatingComponent {
  starRate = 0;
  starRate1 = 5;
  starRate2 = 4;
  starRate3 = 6;
  starRate4 = 5;
  starRate5 = 0;
  starRate6 = 3;
reset(){
 this.starRate6 = 0;
}
}
