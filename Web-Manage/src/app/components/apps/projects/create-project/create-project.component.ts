import { Component, ViewChild } from '@angular/core';
import { FilePondComponent, FilePondModule } from 'ngx-filepond';
import * as FilePond from 'filepond';
import { AngularEditorConfig, AngularEditorModule } from '@kolkov/angular-editor';
import flatpickr from 'flatpickr';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-create-project',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FilePondModule,FlatpickrModule,FormsModule,ReactiveFormsModule,AngularEditorModule,HttpClientModule],
  providers:[FlatpickrDefaults],
  templateUrl: './create-project.component.html',
  styleUrls: ['./create-project.component.scss']
})
export class CreateProjectComponent {
  tags1: string[] = ["Marketing", "Sales", "Development", "Design", "Research"];

  selectedTags=['Angelina May'];
  tags=[
    {id:1,name:'Kiara advain'},
    {id:2,name:'Hercules Jhon'},
    {id:3,name:'Mayor Kim'},
    {id:4,name:'Alexa Biss'},
    {id:5,name:'Karley Dia'},
    {id:6,name:'Kim Jong'},
    {id:7,name:'Darren Sami'},
    {id:8,name:'Elizabeth'},
    {id:9,name:'Bear Gills'},
    {id:10,name:'Alex Carey'},
    
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
htmlContent:string = '';

config: AngularEditorConfig = {
  editable: true,
  spellcheck: true,
  height: '10rem',
  minHeight: '5rem',
  translate: 'no',
  defaultParagraphSeparator: 'p',
  defaultFontName: 'Arial',
  toolbarHiddenButtons: [
    ['bold']
    ],
  customClasses: [
    {
      name: "quote",
      class: "quote",
    },
    {
      name: 'redText',
      class: 'redText'
    },
    {
      name: "titleText",
      class: "titleText",
      tag: "h1",
    },
  ]
};
basicDemoValue = '2017-01-01';
inlineDatePicker: Date = new Date();
timePicker: Date | null = null;
timePicker1: Date | null = null;
timePicker2: Date | null = null;
timePicker3: Date | null = null;
timePicker4: Date | null = null;

flatpickrOptions: any = {
  inline: true,
};
// flatpickrOptions: FlatpickrOptions;

constructor() {}

ngOnInit() {
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
