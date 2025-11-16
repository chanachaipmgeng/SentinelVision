import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/dropdowns';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-dropdowns',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './dropdowns.component.html',
  styleUrls: ['./dropdowns.component.scss']
})
export class DropdownsComponent {
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
  isContentVisible16 = false;
  isContentVisible17 = false;
  isContentVisible18 = false;
  isContentVisible19 = false;
  isContentVisible20 = false;
  isContentVisible21 = false;
  isContentVisible22 = false;


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
  toggleClass16 = "line";
  toggleClass17 = "line";
  toggleClass18 = "line";
  toggleClass19 = "line";
  toggleClass20 = "line";
  toggleClass21 = "line";
  toggleClass22 = "line";

  

  ts1: string = codeData.dropdownTS1;
  ts2: string = codeData.dropdownTS2;
  ts3: string = codeData.dropdownTS3;
  ts4: string = codeData.dropdownTS4;
  ts5: string = codeData.dropdownTS5;
  ts6: string = codeData.dropdownTS6;
  ts7: string = codeData.dropdownTS7;
  ts8: string = codeData.dropdownTS8;
  ts9: string = codeData.dropdownTS9;
  ts10: string = codeData.dropdownTS10;
  ts11: string = codeData.dropdownTS11;
  ts12: string = codeData.dropdownTS12;
  ts13: string = codeData.dropdownTS13;
  ts14: string = codeData.dropdownTS14;
  ts15: string = codeData.dropdownTS15;
  ts16: string = codeData.dropdownTS16;
  ts17: string = codeData.dropdownTS17;
  ts18: string = codeData.dropdownTS18;
  ts19: string = codeData.dropdownTS19;
  ts20: string = codeData.dropdownTS20;
  ts21: string = codeData.dropdownTS21;
  ts22: string = codeData.dropdownTS22;
  toggleDropdowns() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  
  
  toggleSingle() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }  
  
  toggleRounded() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleOutline() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleOutline2() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleSplit() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleSizing() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleDropup() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleDropup1() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
    }
  }  
  
  toggleDropup2() {
    this.isContentVisible10 = !this.isContentVisible10;
    if (this.toggleClass10 === "line") {
      this.toggleClass10 = "s-slash-line";
    } else {
      this.toggleClass10 = "line";
    }
  }  
  
  toggleActive() {
    this.isContentVisible11 = !this.isContentVisible11;
    if (this.toggleClass11 === "line") {
      this.toggleClass11 = "s-slash-line";
    } else {
      this.toggleClass11 = "line";
    }
  }  
  
  toggleDisabled() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  toggleAuto() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  toggleForms() {
    this.isContentVisible14 = !this.isContentVisible14;
    if (this.toggleClass14 === "line") {
      this.toggleClass14 = "s-slash-line";
    } else {
      this.toggleClass14 = "line";
    }
  }  
  
  toggleAlignment() {
    this.isContentVisible15 = !this.isContentVisible15;
    if (this.toggleClass15 === "line") {
      this.toggleClass15 = "s-slash-line";
    } else {
      this.toggleClass15 = "line";
    }
  }  
  
  toggleDark() {
    this.isContentVisible16 = !this.isContentVisible16;
    if (this.toggleClass16 === "line") {
      this.toggleClass16 = "s-slash-line";
    } else {
      this.toggleClass16 = "line";
    }
  }  
  
  toggleCustom() {
    this.isContentVisible17 = !this.isContentVisible17;
    if (this.toggleClass17 === "line") {
      this.toggleClass17 = "s-slash-line";
    } else {
      this.toggleClass17 = "line";
    }
  }  
  
  toggleGhost() {
    this.isContentVisible18 = !this.isContentVisible18;
    if (this.toggleClass18 === "line") {
      this.toggleClass18 = "s-slash-line";
    } else {
      this.toggleClass18 = "line";
    }
  }  
  
  toggleItems() {
    this.isContentVisible19 = !this.isContentVisible19;
    if (this.toggleClass19 === "line") {
      this.toggleClass19 = "s-slash-line";
    } else {
      this.toggleClass19 = "line";
    }
  }  
  
  toggleHeaders() {
    this.isContentVisible20 = !this.isContentVisible20;
    if (this.toggleClass20 === "line") {
      this.toggleClass20 = "s-slash-line";
    } else {
      this.toggleClass20 = "line";
    }
  }  
  
  toggleDividers() {
    this.isContentVisible21 = !this.isContentVisible21;
    if (this.toggleClass21 === "line") {
      this.toggleClass21 = "s-slash-line";
    } else {
      this.toggleClass21 = "line";
    }
  }  
  
  toggleMenu() {
    this.isContentVisible22 = !this.isContentVisible22;
    if (this.toggleClass22 === "line") {
      this.toggleClass22 = "s-slash-line";
    } else {
      this.toggleClass22 = "line";
    }
  }  
  
}
