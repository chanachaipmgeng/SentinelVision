import { Component, ViewChild } from '@angular/core';
import { FilePondComponent } from 'ngx-filepond';
import * as FilePond from 'filepond';
import { FilePondModule } from "ngx-filepond";

import { DropzoneComponent , DropzoneDirective,
  DropzoneConfigInterface, 
  DropzoneModule,
  DROPZONE_CONFIG} from 'ngx-dropzone-wrapper';
import { SharedModule } from '../../../../shared/shared.module';
  
const DEFAULT_DROPZONE_CONFIG: DropzoneConfigInterface = {
  // Change this to your upload POST address:
  url: 'https://httpbin.org/post',
  acceptedFiles: 'image/*',
  createImageThumbnails: true
};

@Component({
  selector: 'app-fileuploads',
  standalone: true,
  imports: [SharedModule,FilePondModule,DropzoneModule],
  providers: [
    {
      provide: DROPZONE_CONFIG,
      useValue: DEFAULT_DROPZONE_CONFIG
    }
  ],
  templateUrl: './fileuploads.component.html',
  styleUrl: './fileuploads.component.scss'
})
export class FileuploadsComponent {
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
    // {
    //   source: "assets/photo.jpeg",
    //   options: {
    //     type: "local",
    //   },
    // },

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
  public type: string = 'component';

  public disabled: boolean = false;

  public config: DropzoneConfigInterface = {
    clickable: true,
    maxFiles: 100,
    autoReset: null,
    errorReset: null,
    cancelReset: null
  };
  @ViewChild(DropzoneComponent, { static: false }) componentRef?: DropzoneComponent;
  @ViewChild(DropzoneDirective, { static: false }) directiveRef?: DropzoneDirective;
  constructor() {}

  public toggleType(): void {
    this.type = (this.type === 'component') ? 'directive' : 'component';
  }

  public toggleDisabled(): void {
    this.disabled = !this.disabled;
  }

  public toggleAutoReset(): void {
    this.config.autoReset = this.config.autoReset ? null : 5000;
    this.config.errorReset = this.config.errorReset ? null : 5000;
    this.config.cancelReset = this.config.cancelReset ? null : 5000;
  }

  public toggleMultiUpload(): void {
    this.config.maxFiles = this.config.maxFiles ? 0 : 1;
  }

  public toggleClickAction(): void {
    this.config.clickable = !this.config.clickable;
  }

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
}
