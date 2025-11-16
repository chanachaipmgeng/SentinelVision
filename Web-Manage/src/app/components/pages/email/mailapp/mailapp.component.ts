import { ChangeDetectorRef, Component, ElementRef, HostListener, NgZone, Renderer2, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FilePondComponent } from 'ngx-filepond';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { Editor, NgxEditorModule, Toolbar,Validators } from 'ngx-editor';
import { SharedModule } from '../../../../shared/shared.module';
import { SimplebarAngularModule } from 'simplebar-angular';
import { FormsModule,ReactiveFormsModule } from '@angular/forms';
import React from 'react';
import { NgSelectModule } from '@ng-select/ng-select';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';

@Component({
  selector: 'app-mailapp',
  standalone: true,
  imports: [SharedModule,NgxEditorModule,CommonModule,SimplebarAngularModule,FormsModule,ReactiveFormsModule,NgSelectModule],
  templateUrl: './mailapp.component.html',
  styleUrl: './mailapp.component.scss'
})
export class MailappComponent {
  constructor(private formBuilder: FormBuilder,private breakpointObserver: BreakpointObserver) {
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
  ngOnInit(){
    this.editor = new Editor();
  
  }
  isNotifyEmpty: boolean = this.breakpointObserver.isMatched(Breakpoints.Handset);



  @HostListener('window:resize', ['$event'])
  onResize(event: Event) {
    this.isNotifyEmpty = this.breakpointObserver.isMatched(Breakpoints.Handset);
  }

  toggleNotifyEmpty() {
    this.isNotifyEmpty = !this.isNotifyEmpty;
  }
}
