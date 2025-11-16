import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';
import { NgSelectModule } from '@ng-select/ng-select';

@Component({
  selector: 'app-team',
  standalone: true,
  imports: [SharedModule,SimplebarAngularModule,NgSelectModule],
  templateUrl: './team.component.html',
  styleUrls: ['./team.component.scss']
})
export class TeamComponent {

}
