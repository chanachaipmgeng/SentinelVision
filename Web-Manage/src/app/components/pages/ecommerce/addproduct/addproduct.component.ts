import { Component, ViewChild } from '@angular/core';
import { FormBuilder, FormGroup, FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AngularEditorConfig, AngularEditorModule } from '@kolkov/angular-editor';
import { DROPZONE_CONFIG, DropzoneComponent, DropzoneConfigInterface, DropzoneDirective, DropzoneModule } from 'ngx-dropzone-wrapper';
import { Editor, NgxEditorModule, Toolbar, Validators } from 'ngx-editor';
import { FilePondComponent } from 'ngx-filepond';
import { FilePondModule } from 'ngx-filepond';
// import { FilePondOptions } from 'filepond';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { HttpClientModule } from '@angular/common/http';
const DEFAULT_DROPZONE_CONFIG: DropzoneConfigInterface = {
  // Change this to your upload POST address:
  url: 'https://httpbin.org/post',
  acceptedFiles: 'image/*,application/pdf,.doc,.docx,.txt',
  createImageThumbnails: true
};
@Component({
  selector: 'app-addproduct',
  standalone: true,
  imports: [SharedModule,NgxEditorModule,FilePondModule,NgSelectModule,DropzoneModule,MaterialModuleModule,FlatpickrModule,FormsModule,ReactiveFormsModule,AngularEditorModule,HttpClientModule],
  providers:[  {
    provide: DROPZONE_CONFIG,
    useValue: DEFAULT_DROPZONE_CONFIG
  },FlatpickrDefaults],

  templateUrl: './addproduct.component.html',
  styleUrls: ['./addproduct.component.scss']
})
export class AddproductComponent {
  public type: string = 'component';

  public disabled: boolean = false;

  public config1: DropzoneConfigInterface = {
    clickable: true,
    maxFiles: 100,
    autoReset: null,
    errorReset: null,
    cancelReset: null
  };
  
  @ViewChild(DropzoneComponent, { static: false }) componentRef?: DropzoneComponent;
  @ViewChild(DropzoneDirective, { static: false }) directiveRef?: DropzoneDirective;
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
      { value: 'Type Text Here', disabled: false },
      Validators.required()
    ),
  });


  public toggleType(): void {
    this.type = (this.type === 'component') ? 'directive' : 'component';
  }

  public toggleDisabled1(): void {
    this.disabled = !this.disabled;
  }
  public resetDropzoneUploads(): void {
    if (this.type === 'directive' && this.directiveRef) {
      this.directiveRef.reset();
    } else if (this.type === 'component' && this.componentRef && this.componentRef.directiveRef) {
      this.componentRef.directiveRef.reset();
    }
  }

  public onUploadInit(args: any): void {
  }

  public onUploadError(args: any): void {
  }

  public onUploadSuccess(args: any): void {
  }
//select 1
selectedSimpleItem ='select' ;
simpleItems:any= [];
//select 2
selectedSimpleItem1 ='select' ;
simpleItems1:any= [];
//select 3
selectedSimpleItem2 ='select' ;
simpleItems2:any= [];
//select 4
selectedSimpleItem3 ='select' ;
simpleItems3:any= [];
//select 5
selectedSimpleItem4='select' ;
simpleItems4:any= [];
//select 6
selectedSimpleItem5='select' ;
simpleItems5:any= [];

//select 7
selectedCars = ['select'];
cars = [
    { id: 1, name: 'Volvo' , disabled: true },
    { id: 2, name: 'Saab' },
    { id: 3, name: 'Opel' },
    { id: 4, name: 'Audi' },
];
//select 8
selectedSimpleItem6='select' ;
simpleItems6:any= []; 
flatpickrOptions: any = {
  inline: true,
};
ngOnInit() {
  this.simpleItems = ['Jewellery','Ethnic & Festive','Grooming','Accesories','Footwear','Category','Clothing',];
  this.simpleItems1= ['Male','All','Female','Others'];
  this.simpleItems2= ['Small','Medium','Extra Large','Large'];
  this.simpleItems3= ['Armani','Lacoste','Arrrabi','Mufti'];
  this.simpleItems4= ['White','Red','Pink','Yellow','Orange','Green'];
  this.simpleItems5= ['Publish','Scheduled'];
  this.simpleItems6= ['In Stock','Out Of Stock'];
  this.editor = new Editor();
  this.flatpickrOptions = {
    enableTime: true,
    noCalendar: true,
    dateFormat: 'H:i',

  };
  myGroup: FormGroup;

  
  flatpickr('#inlinetime', this.flatpickrOptions);

    this.flatpickrOptions = {
      enableTime: true,
      dateFormat: 'Y-m-d H:i', // Specify the format you want
      defaultDate: '2023-11-07 14:30', // Set the default/preloaded time (adjust this to your desired time)
    };

    flatpickr('#pretime', this.flatpickrOptions);
}
editorConfig: AngularEditorConfig = {
  editable: true,
    spellcheck: true,
    height: 'auto',
    minHeight: '0',
    maxHeight: 'auto',
    width: 'auto',
    minWidth: '0',
    translate: 'yes',
    enableToolbar: true,
    showToolbar: true,
    placeholder: 'Enter text here...',
    defaultParagraphSeparator: '',
    defaultFontName: '',
    defaultFontSize: '',
    fonts: [
      {class: 'arial', name: 'Arial'},
      {class: 'times-new-roman', name: 'Times New Roman'},
      {class: 'calibri', name: 'Calibri'},
      {class: 'comic-sans-ms', name: 'Comic Sans MS'}
    ],
    customClasses: [
    {
      name: 'quote',
      class: 'quote',
    },
    {
      name: 'redText',
      class: 'redText'
    },
    {
      name: 'titleText',
      class: 'titleText',
      tag: 'h1',
    },
  ],
  uploadUrl: 'v1/image',

};


  @ViewChild('myPond')
  myPond!: FilePondComponent;

// pondOptions: FilePondOptions = {
//   allowMultiple: true,
//   labelIdle: 'Drop files here...'   
// }

// pondFiles: FilePondOptions["files"] = [
//   {
//     source: 'assets/photo.jpeg',
//     options: {
//       type: 'local'
//     }
//   }
// ]

pondHandleInit() {
}

pondHandleAddFile(event: any) {
}

pondHandleActivateFile(event: any) {
}
}
