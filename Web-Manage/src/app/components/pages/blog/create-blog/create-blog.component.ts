import { Component, ViewChild } from '@angular/core';
import { AngularEditorConfig, AngularEditorModule } from '@kolkov/angular-editor';
import { DROPZONE_CONFIG, DropzoneComponent, DropzoneConfigInterface, DropzoneDirective, DropzoneModule } from 'ngx-dropzone-wrapper';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { HttpClientModule } from '@angular/common/http';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

import { FilePondComponent } from 'ngx-filepond';
const DEFAULT_DROPZONE_CONFIG: DropzoneConfigInterface = {
  // Change this to your upload POST address:
  url: 'https://httpbin.org/post',
  acceptedFiles: 'image/*',
  createImageThumbnails: true
};
@Component({
  selector: 'app-create-blog',
  standalone: true,
  imports: [SharedModule,DropzoneModule,FlatpickrModule,AngularEditorModule,HttpClientModule,NgSelectModule,FormsModule,ReactiveFormsModule,CommonModule],
  providers:[  {
    provide: DROPZONE_CONFIG,
    useValue: DEFAULT_DROPZONE_CONFIG
  },FlatpickrDefaults],
  templateUrl: './create-blog.component.html',
  styleUrls: ['./create-blog.component.scss']
})
export class CreateBlogComponent {
  public type: string = 'component';

  public disabled: boolean = false;

  public config: DropzoneConfigInterface = {
    clickable: true,
    maxFiles: 1,
    autoReset: null,
    errorReset: null,
    cancelReset: null,
    maxFilesize:1
  };
  //First Selelct
  selectedSimpleItem = 'Select Category';
  simpleItems:any = [];
  // second Select
  selectedSimpleItem1 = 'Select';
  simpleItems1:any = [];
  //Select 3
  selectedBlogs = ['Landscape','Top Blog'];
  Blogs = [
      { id: 1, name: 'Adventure' },
      { id: 2, name: 'Blogger'},
      
  ];


  ngOnInit(): void {
    this.simpleItems=['Beauty','Fashion','Food','Nature','Sports']
    this.simpleItems1=['Hold','Published']
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
  htmlContent:string = '';
config1: AngularEditorConfig = {
  editable: true,
  spellcheck: true,
  height: '15rem',
  minHeight: '5rem',
  placeholder: 'Enter text here...', 
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


@ViewChild(DropzoneComponent, { static: false }) componentRef?: DropzoneComponent;
@ViewChild(DropzoneDirective, { static: false }) directiveRef?: DropzoneDirective;
public resetDropzoneUploads(): void {
  if (this.type === 'directive' && this.directiveRef) {
    this.directiveRef.reset();
  } else if (this.type === 'component' && this.componentRef && this.componentRef.directiveRef) {
    this.componentRef.directiveRef.reset();
  }
}

public onUploadInit(args: any): void {
  console.log('onUploadInit:', args);
}

public onUploadError(args: any): void {
  console.log('onUploadError:', args);
}

public onUploadSuccess(args: any): void {
  console.log('onUploadSuccess:', args);
}
flatpickrOptions: any = {
  inline: true,
};
// flatpickrOptions: FlatpickrOptions;

constructor() {}



}
