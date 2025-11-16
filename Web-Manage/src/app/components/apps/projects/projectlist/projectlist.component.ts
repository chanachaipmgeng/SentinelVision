import { Component } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-projectlist',
  standalone: true,
  imports: [SharedModule,NgSelectModule,RouterModule],
  templateUrl: './projectlist.component.html',
  styleUrls: ['./projectlist.component.scss']
})
export class ProjectlistComponent {

}
