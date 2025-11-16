import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-emptypage',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './emptypage.component.html',
  styleUrls: ['./emptypage.component.scss']
})
export class EmptypageComponent {

}
