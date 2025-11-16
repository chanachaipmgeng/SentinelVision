import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/formlayouts';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-form-layouts',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FormsModule,ReactiveFormsModule],
  templateUrl: './form-layouts.component.html',
  styleUrls: ['./form-layouts.component.scss']
})
export class FormLayoutsComponent {
  ts1: string = codeData.layoutsTS1;
  ts2: string = codeData.layoutsTS2;
  ts3: string = codeData.layoutsTS3;
  ts4: string = codeData.layoutsTS4;
  ts5: string = codeData.layoutsTS5;
  ts6: string = codeData.layoutsTS6;
  ts7: string = codeData.layoutsTS7;
  ts8: string = codeData.layoutsTS8;
  ts9: string = codeData.layoutsTS9;
  ts10: string = codeData.layoutsTS10;
  ts11: string = codeData.layoutsTS11;
  toggleClass = "line";
  toggleClass1 = "line";
  toggleClass2 = "line";
  toggleClass3 = "line";
  toggleClass4 = "line";
  toggleClass5 = "line";
  toggleClass6 = "line";
  toggleClass7 = "line";
  toggleClass8 = "line";
  toggleClass9 = "line";
  toggleClass10 = "line";
  toggleClass11 = "line";
  isContentVisible = false;
  isContentVisible1 = false;
  isContentVisible2 = false;
  isContentVisible3 = false;
  isContentVisible4 = false;
  isContentVisible5 = false;
  isContentVisible6 = false;
  isContentVisible7 = false;
  isContentVisible8 = false;
  isContentVisible9 = false;
  isContentVisible10 = false;
  isContentVisible11 = false;
  toggleInput1(){
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  toggleInput2(){
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }
  toggleInput3(){
    this.isContentVisible3 = !this.isContentVisible3;
    if (this.toggleClass3 === "line") {
      this.toggleClass3 = "s-slash-line";
    } else {
      this.toggleClass3 = "line";
    }
  }
  toggleInput4(){
    this.isContentVisible4= !this.isContentVisible4;
    if (this.toggleClass4=== "line") {
      this.toggleClass4= "s-slash-line";
    } else {
      this.toggleClass4= "line";
    }
  }
  toggleInput5(){
    this.isContentVisible5= !this.isContentVisible5;
    if (this.toggleClass5=== "line") {
      this.toggleClass5= "s-slash-line";
    } else {
      this.toggleClass5= "line";
    }
  }
  toggleInput6(){
    this.isContentVisible6= !this.isContentVisible6;
    if (this.toggleClass6=== "line") {
      this.toggleClass6= "s-slash-line";
    } else {
      this.toggleClass6= "line";
    }
  }
  toggleInput7(){
    this.isContentVisible7= !this.isContentVisible7;
    if (this.toggleClass7=== "line") {
      this.toggleClass7= "s-slash-line";
    } else {
      this.toggleClass7= "line";
    }
  }
  toggleInput8(){
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }
  toggleInput9(){
    this.isContentVisible9= !this.isContentVisible9;
    if (this.toggleClass9=== "line") {
      this.toggleClass9= "s-slash-line";
    } else {
      this.toggleClass9= "line";
    }
  }
  toggleInput10(){
    this.isContentVisible10= !this.isContentVisible10;
    if (this.toggleClass10=== "line") {
      this.toggleClass10= "s-slash-line";
    } else {
      this.toggleClass10= "line";
    }
  }
  toggleInput11(){
    this.isContentVisible11= !this.isContentVisible11;
    if (this.toggleClass11=== "line") {
      this.toggleClass11= "s-slash-line";
    } else {
      this.toggleClass11= "line";
    }
  }
}
