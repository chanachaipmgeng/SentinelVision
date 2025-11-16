import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/object';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-objectfit',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './objectfit.component.html',
  styleUrls: ['./objectfit.component.scss']
})
export class ObjectfitComponent {
  // public fullScreen: boolean = false;
  toggleObject() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  toggleObjectFit() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }
  
  
  toggleObjectFill() {
    this.isContentVisible3 = !this.isContentVisible3;
    if (this.toggleClass3 === "line") {
      this.toggleClass3 = "s-slash-line";
    } else {
      this.toggleClass3 = "line";
    }
  }  
  
  toggleFitScale() {
    this.isContentVisible4= !this.isContentVisible4;
    if (this.toggleClass4=== "line") {
      this.toggleClass4= "s-slash-line";
    } else {
      this.toggleClass4= "line";
    }
  }  
  
 
  toggleFitNone() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleFitContain() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleFitMd() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleFitLg() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleFitLgxl() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
    }
  }  
  
  toggleFitxxl() {
    this.isContentVisible10 = !this.isContentVisible10;
    if (this.toggleClass10 === "line") {
      this.toggleClass10 = "s-slash-line";
    } else {
      this.toggleClass10 = "line";
    }
  }  
  
  toggleFitvideo() {
    this.isContentVisible11 = !this.isContentVisible11;
    if (this.toggleClass11 === "line") {
      this.toggleClass11 = "s-slash-line";
    } else {
      this.toggleClass11 = "line";
    }
  }  
  
  toggleFitCovervideo() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  toggleFitFillvideo() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  toggleFitCoverscale() {
    this.isContentVisible14 = !this.isContentVisible14;
    if (this.toggleClass14 === "line") {
      this.toggleClass14 = "s-slash-line";
    } else {
      this.toggleClass14 = "line";
    }
  }  
  Video() {
    this.isContentVisible15 = !this.isContentVisible15;
    if (this.toggleClass15 === "line") {
      this.toggleClass15 = "s-slash-line";
    } else {
      this.toggleClass15 = "line";
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
  toggleClass15 = "line";
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
  isContentVisible15 = false;
  ts1: string = codeData.objectTS1;
  ts2: string = codeData.objectTS2;
  ts3: string = codeData.objectTS3;
  ts4: string = codeData.objectTS4;
  ts5: string = codeData.objectTS5;
  ts6: string = codeData.objectTS6;
  ts7: string = codeData.objectTS7;
  ts8: string = codeData.objectTS8;
  ts9: string = codeData.objectTS9;
  ts10: string = codeData.objectTS10;
  ts11: string = codeData.objectTS11;
  ts12: string = codeData.objectTS12;
  ts13: string = codeData.objectTS13;
  ts14: string = codeData.objectTS14;
  ts15: string = codeData.objectTS15;
}
