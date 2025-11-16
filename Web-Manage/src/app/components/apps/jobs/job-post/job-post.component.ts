import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-job-post',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FormsModule,ReactiveFormsModule],
  templateUrl: './job-post.component.html',
  styleUrls: ['./job-post.component.scss']
})
export class JobPostComponent {
  selectedLanguages=['English'];
  languages=[
    {id:1,name:'French'},
    {id:2,name:'Arabic'},
    {id:3,name:'Hindi'},
    
  ]
  selectedQualifications=['Graduate'];
  Qualifications=[
    {id:1,name:'Diploma'},
    {id:2,name:'MBA'},
    {id:3,name:'MCA'},
    
  ]
  selectedSkills=['HTML'];
  Skills=[
    {id:1,name:'CSS'},
    {id:2,name:'JavaScript'},
    {id:3,name:'React'},
    
  ]
}
