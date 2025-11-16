import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { RouterModule } from '@angular/router';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';

@Component({
  selector: 'app-search-candidate',
  standalone: true,
  imports: [SharedModule,NgSelectModule,RouterModule,MaterialModuleModule],
  templateUrl: './search-candidate.component.html',
  styleUrls: ['./search-candidate.component.scss']
})
export class SearchCandidateComponent {

}
