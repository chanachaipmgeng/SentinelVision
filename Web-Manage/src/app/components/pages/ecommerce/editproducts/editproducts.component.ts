import { Component, ViewChild } from '@angular/core';
import { FormBuilder, FormGroup, FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { DROPZONE_CONFIG, DropzoneConfigInterface, DropzoneModule } from 'ngx-dropzone-wrapper';
import { Editor, NgxEditorModule, Toolbar, Validators } from 'ngx-editor';
import { FilePondComponent, FilePondModule } from 'ngx-filepond';
import * as FilePond from 'filepond';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { NgSelectModule } from '@ng-select/ng-select';
import { CommonModule } from '@angular/common';
const DEFAULT_DROPZONE_CONFIG: DropzoneConfigInterface = {
  // Change this to your upload POST address:
  url: 'https://httpbin.org/post',
  acceptedFiles: 'image/*',
  createImageThumbnails: true
};
@Component({
  selector: 'app-editproducts',
  standalone: true,
  imports: [SharedModule,FlatpickrModule,FilePondModule,DropzoneModule,FormsModule,ReactiveFormsModule,NgSelectModule,NgxEditorModule,CommonModule],
  providers:[  {
    provide: DROPZONE_CONFIG,
    useValue: DEFAULT_DROPZONE_CONFIG
  },FlatpickrDefaults],

  templateUrl: './editproducts.component.html',
  styleUrls: ['./editproducts.component.scss']
})
export class EditproductsComponent {

  public type: string = 'component';

  public disabled: boolean = false;
  constructor(private formBuilder: FormBuilder) {
    this.editorContent = this.formBuilder.group({});
  }

 
  // ngx-editor
  public editorContent!: FormGroup;
  editordoc = '';
  public editor!: Editor;
  toolbar: Toolbar = [
    ['bold', 'italic'],
    ['underline', 'strike'],
    ['code', 'blockquote'],
    ['ordered_list', 'bullet_list'],
    [{ heading: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] }],
    ['text_color', 'background_color'],
    ['align_left', 'align_center', 'align_right', 'align_justify'],
  ];

  form: any = new FormGroup({
    editorContent: new FormControl(
      { value: `<ul><li>Care Instructions: Machine Wash</li>
      <li> Neckline: The pullover is framed with a Crew Neck</li>
      <li>  Fit Type: Regular Fit</li>
      <li> Long Sleeves: The pullover is designed with Long Sleeves.</li>
      <li> Soft Hand feel: The fabric is extremely soft and comfortable, keeping you at ease for hours.</li>
      <li> Solid: The pullover is available in solid pattern.</li></ul>`, disabled: false },
      Validators.required()
    ),
  });

  genders = [
    {id: 1,name: 'All'},
    {id: 2,name: 'Female'},
    {id: 3,name: 'Male'},
    {id: 4,name: 'Others'},
  ];
  selectedGender = this.genders[1].name;
 //select 7
selectedCars = ['select'];
cars = [
    { id: 1, name: 'White'  },
    { id: 2, name: 'Black' },
    { id: 3, name: 'Red' },
    { id: 4, name: 'Orange' },
    { id: 5, name: 'Yellow' },
    { id: 6, name: 'Pink' },
    { id: 7, name: 'Black' },
    { id: 8, name: 'Purple' },
    { id: 9, name: 'Green' },





];
public config1: DropzoneConfigInterface = {
  clickable: true,
  maxFiles: 100,
  autoReset: null,
  errorReset: null,
  cancelReset: null
};
selectedTags=['select'];
tags=[
  {id:1,name:'Plain'},
  {id:2,name:'Relaxed'},
  {id:3,name:'Washed'},
  {id:4,name:'Solid'},



  
]
public onUploadInit(args: any): void {
  console.log('onUploadInit:', args);
}

public onUploadError(args: any): void {
  console.log('onUploadError:', args);
}

public onUploadSuccess(args: any): void {
  console.log('onUploadSuccess:', args);
}
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

}

pondHandleAddFile(event: any) {

}

pondHandleActivateFile(event: any) {

}

ngOnInit(){
  this.editor = new Editor();
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



}
