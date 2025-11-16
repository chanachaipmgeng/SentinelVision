import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/buttons';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-buttons',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './buttons.component.html',
  styleUrls: ['./buttons.component.scss']
})
export class ButtonsComponent {
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

  

  ts1: string = codeData.buttonsTS1;
  ts2: string = codeData.buttonsTS2;
  ts3: string = codeData.buttonsTS3;
  ts4: string = codeData.buttonsTS4;
  ts5: string = codeData.buttonsTS5;
  ts6: string = codeData.buttonsTS6;
  ts7: string = codeData.buttonsTS7;
  ts8: string = codeData.buttonsTS8;
  ts9: string = codeData.buttonsTS9;
  ts10: string = codeData.buttonsTS10;
  ts11: string = codeData.buttonsTS11;
  ts12: string = codeData.buttonsTS12;
  ts13: string = codeData.buttonsTS13;
  ts14: string = codeData.buttonsTS14;
  ts15: string = codeData.buttonsTS15;
  ts16: string = codeData.buttonsTS16;
  ts17: string = codeData.buttonsTS17;
  ts18: string = codeData.buttonsTS18;
  ts19: string = codeData.buttonsTS19;
  ts20: string = codeData.buttonsTS20;
  ts21: string = codeData.buttonsTS21;
  ts22: string = codeData.buttonsTS22;
  toggleButton() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  
  
  toggleRoundedButton() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }  
  
  toggleLightButton() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleLightRoundedButton() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleOutlineButton() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleRoundedOutlinetButton() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleGradientButton() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleRoundedGradientButton() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleGhostButton() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
    }
  }  
  
  toggleRoundedGhostButton() {
    this.isContentVisible10 = !this.isContentVisible10;
    if (this.toggleClass10 === "line") {
      this.toggleClass10 = "s-slash-line";
    } else {
      this.toggleClass10 = "line";
    }
  }  
  
  toggleTagsButton() {
    this.isContentVisible11 = !this.isContentVisible11;
    if (this.toggleClass11 === "line") {
      this.toggleClass11 = "s-slash-line";
    } else {
      this.toggleClass11 = "line";
    }
  }  
  
  toggleAnchorButton() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  toggleLoadingButton() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  toggleIconButton() {
    this.isContentVisible14 = !this.isContentVisible14;
    if (this.toggleClass14 === "line") {
      this.toggleClass14 = "s-slash-line";
    } else {
      this.toggleClass14 = "line";
    }
  }  
  
  togglesocialButton() {
    this.isContentVisible15 = !this.isContentVisible15;
    if (this.toggleClass15 === "line") {
      this.toggleClass15 = "s-slash-line";
    } else {
      this.toggleClass15 = "line";
    }
  }  
  
  toggleSizesButton() {
    this.isContentVisible16 = !this.isContentVisible16;
    if (this.toggleClass16 === "line") {
      this.toggleClass16 = "s-slash-line";
    } else {
      this.toggleClass16 = "line";
    }
  }  
  
  toggleWidthButton() {
    this.isContentVisible17 = !this.isContentVisible17;
    if (this.toggleClass17 === "line") {
      this.toggleClass17 = "s-slash-line";
    } else {
      this.toggleClass17 = "line";
    }
  }  
  
  toggleShadowButton() {
    this.isContentVisible18 = !this.isContentVisible18;
    if (this.toggleClass18 === "line") {
      this.toggleClass18 = "s-slash-line";
    } else {
      this.toggleClass18 = "line";
    }
  }  
  
  toggleColorButton() {
    this.isContentVisible19 = !this.isContentVisible19;
    if (this.toggleClass19 === "line") {
      this.toggleClass19 = "s-slash-line";
    } else {
      this.toggleClass19 = "line";
    }
  }  
  
  toggleLabelButton() {
    this.isContentVisible20 = !this.isContentVisible20;
    if (this.toggleClass20 === "line") {
      this.toggleClass20 = "s-slash-line";
    } else {
      this.toggleClass20 = "line";
    }
  }  
  
  toggleCustomButton() {
    this.isContentVisible21 = !this.isContentVisible21;
    if (this.toggleClass21 === "line") {
      this.toggleClass21 = "s-slash-line";
    } else {
      this.toggleClass21 = "line";
    }
  }  
  
  toggleBlockButton() {
    this.isContentVisible22 = !this.isContentVisible22;
    if (this.toggleClass22 === "line") {
      this.toggleClass22 = "s-slash-line";
    } else {
      this.toggleClass22 = "line";
    }
  }  
  

}
