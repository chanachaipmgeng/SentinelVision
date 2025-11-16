import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-project-overview',
  standalone: true,
  imports: [SharedModule,NgSelectModule],
  templateUrl: './project-overview.component.html',
  styleUrls: ['./project-overview.component.scss']
})
export class ProjectOverviewComponent {

}
