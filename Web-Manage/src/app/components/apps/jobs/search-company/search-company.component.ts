import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-search-company',
  standalone: true,
  imports: [SharedModule,NgSelectModule,RouterModule],
  templateUrl: './search-company.component.html',
  styleUrls: ['./search-company.component.scss']
})
export class SearchCompanyComponent {

}
