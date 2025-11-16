import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/listgroup';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-listgroup',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './listgroup.component.html',
  styleUrls: ['./listgroup.component.scss']
})
export class ListgroupComponent {

  // public fullScreen: boolean = false;
  toggleVisibility() {
    this.isContentVisible = !this.isContentVisible;
    if (this.toggleClass === "line") {
      this.toggleClass = "s-slash-line";
    } else {
      this.toggleClass = "line";
    }
  }
  toggleActive() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  
  
  toggleDisabled() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }  
  
  toggleFlush() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleLinks() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleButtons() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleContext() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleHover() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleSolid() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleCustom() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
    }
  }  
  
  toggleHeadings() {
    this.isContentVisible10 = !this.isContentVisible10;
    if (this.toggleClass10 === "line") {
      this.toggleClass10 = "s-slash-line";
    } else {
      this.toggleClass10 = "line";
    }
  }  
  
  toggleNumber() {
    this.isContentVisible11 = !this.isContentVisible11;
    if (this.toggleClass11 === "line") {
      this.toggleClass11 = "s-slash-line";
    } else {
      this.toggleClass11 = "line";
    }
  }  
  
  toggleList() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  toggleRadios() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  toggleBadges() {
    this.isContentVisible14 = !this.isContentVisible14;
    if (this.toggleClass14 === "line") {
      this.toggleClass14 = "s-slash-line";
    } else {
      this.toggleClass14 = "line";
    }
  }  
  
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
  toggleClass12 = "line";
  toggleClass13 = "line";
  toggleClass14 = "line";

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
  isContentVisible12 = false;
  isContentVisible13 = false;
  isContentVisible14 = false;
  ts1: string = codeData.listTS1;
  ts2: string = codeData.listTS2;
  ts3: string = codeData.listTS3;
  ts4: string = codeData.listTS4;
  ts5: string = codeData.listTS5;
  ts6: string = codeData.listTS6;
  ts7: string = codeData.listTS7;
  ts8: string = codeData.listTS8;
  ts9: string = codeData.listTS9;
  ts10: string = codeData.listTS10;
  ts11: string = codeData.listTS11;
  ts12: string = codeData.listTS12;
  ts13: string = codeData.listTS13;
  ts14: string = codeData.listTS14;
  ts15: string = codeData.listTS15;

}
