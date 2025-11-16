import { Component } from '@angular/core';
import { Options ,NgxSliderModule} from "ngx-slider-v2";
import { SharedModule } from '../../../../shared/shared.module';
import { NouisliderModule } from 'ng2-nouislider';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';

@Component({
  selector: 'app-search-jobs',
  standalone: true,
  imports: [SharedModule,NgxSliderModule,MaterialModuleModule,FormsModule,ReactiveFormsModule],
  templateUrl: './search-jobs.component.html',
  styleUrls: ['./search-jobs.component.scss']
})
export class SearchJobsComponent {


}
