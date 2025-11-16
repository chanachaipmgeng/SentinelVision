import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/buttongroup';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-buttongroup',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './buttongroup.component.html',
  styleUrls: ['./buttongroup.component.scss']
})
export class ButtongroupComponent {
  isContentVisible1 = false;
  isContentVisible2 = false;
  isContentVisible3 = false;
  isContentVisible4 = false;
  isContentVisible5 = false;
  isContentVisible6 = false;

  toggleClass1 = "line";
  toggleClass2 = "line";
  toggleClass3 = "line";
  toggleClass4 = "line";
  toggleClass5 = "line";
  toggleClass6 = "line";
  ts1: string = codeData.buttonsgroupTS1;
  ts2: string = codeData.buttonsgroupTS2;
  ts3: string = codeData.buttonsgroupTS3;
  ts4: string = codeData.buttonsgroupTS4;
  ts5: string = codeData.buttonsgroupTS5;
  ts6: string = codeData.buttonsgroupTS6;

  toggleBasic() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  
  toggleMixed() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }  
  
  toggleGroupBreak() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleSizing() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleVertical() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleButtonGroup() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
}
