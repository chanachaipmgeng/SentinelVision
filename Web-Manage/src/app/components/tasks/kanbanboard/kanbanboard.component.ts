import { Component, ViewChild } from '@angular/core';
import { FilePondComponent, FilePondModule } from 'ngx-filepond';
import * as FilePond from 'filepond';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { SimplebarAngularModule } from 'simplebar-angular';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
@Component({
  selector: 'app-kanbanboard',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FlatpickrModule,MaterialModuleModule,SimplebarAngularModule,FilePondModule,FormsModule,ReactiveFormsModule],
  providers:[FlatpickrDefaults],
  templateUrl: './kanbanboard.component.html',
  styleUrls: ['./kanbanboard.component.scss']
})
export class KanbanboardComponent {
  selectedNames=['Angelina May'];
  names=[
    {id:1,name:'Angelina May'},
    {id:2,name:'Kiara advain'},
    {id:3,name:'Washed'},
    {id:4,name:'Solid'},
  ]
   selectedTags=['UI/UX'];
  tags=[
    {id:1,name:'UI/UX'},
    {id:2,name:'Marketing'},
    {id:3,name:'Finance'},
    {id:4,name:'Designing'},
    {id:5,name:'Authentication'},
    {id:6,name:'Product'},
    {id:7,name:'Development'},  
  ]
  @ViewChild("myPond") myPond!: FilePondComponent;

pondOptions: FilePond.FilePondOptions = {
  allowMultiple: true,
  labelIdle: "Drop files here to Upload...",
};
singlepondOptions: FilePond.FilePondOptions = {
  allowMultiple: false,
  labelIdle: "Drop files here to Upload...",
};

pondFiles: FilePond.FilePondOptions["files"] = [

];

pondHandleInit() {
  console.log("FilePond has initialised", this.myPond);
}

pondHandleAddFile(event: any) {
  console.log("A file was added", event);
}

pondHandleActivateFile(event: any) {
  console.log("A file was activated", event);
}
flatpickrOptions: any = {
  inline: true,
};
ngOnInit(): void{

  this.flatpickrOptions = {
    enableTime: true,
    noCalendar: true,
    dateFormat: 'H:i',
  };

  flatpickr('#inlinetime', this.flatpickrOptions);

    this.flatpickrOptions = {
      enableTime: true,
      dateFormat: 'Y-m-d H:i', // Specify the format you want
      defaultDate: '2023-11-07 14:30', // Set the default/preloaded time (adjust this to your desired time)
    };

    flatpickr('#pretime', this.flatpickrOptions);
}

}
