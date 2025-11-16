import { Component } from '@angular/core';
import * as codeData from '../../../../shared/prismData/checks';
import { SharedModule } from '../../../../shared/shared.module';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-checksradios',
  standalone: true,
  imports: [SharedModule,CommonModule],
  templateUrl: './checksradios.component.html',
  styleUrl: './checksradios.component.scss'
})
export class ChecksradiosComponent {
  toggleChecks() {
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
  
  toggleRadios() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleDisabled2() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleDefault() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleISwitch() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleSizes() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleRadioSizes() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleInline() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
    }
  }  
  
  toggleReverse() {
    this.isContentVisible10 = !this.isContentVisible10;
    if (this.toggleClass10 === "line") {
      this.toggleClass10 = "s-slash-line";
    } else {
      this.toggleClass10 = "line";
    }
  }  
  
  toggleSwitch() {
    this.isContentVisible11 = !this.isContentVisible11;
    if (this.toggleClass11 === "line") {
      this.toggleClass11 = "s-slash-line";
    } else {
      this.toggleClass11 = "line";
    }
  }  
  
  toggleSwitch2() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  togglesizes1() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  
  toggleSizes2() {
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
  ts1: string = codeData.ChecksTS1;
  ts2: string = codeData.ChecksTS2;
  ts3: string = codeData.ChecksTS3;
  ts4: string = codeData.ChecksTS4;
  ts5: string = codeData.ChecksTS5;
  ts6: string = codeData.ChecksTS6;
  ts7: string = codeData.ChecksTS7;
  ts8: string = codeData.ChecksTS8;
  ts9: string = codeData.ChecksTS9;
  ts10: string = codeData.ChecksTS10;
  ts11: string = codeData.ChecksTS11;
  ts12: string = codeData.ChecksTS12;
  ts13: string = codeData.ChecksTS13;
  ts14: string = codeData.ChecksTS14;
  // ts15: string = codeData.ChecksTS15;
  status1: boolean = true;
  status2: boolean = true;
  status3: boolean = true;
  status4: boolean = true;
  status5: boolean = true;
  status6: boolean = true;
  status7: boolean = true;
  status8: boolean = true;
  status9: boolean = true;
  status10: boolean = true;
  status11: boolean = true;

  clickEvent1() {
    document.querySelector('.radio-first')?.classList.toggle('on')
  }
  clickEvent2() {
    document.querySelector('.toggle-secondary')?.classList.toggle('on');
  }
  clickEvent3() {
    document.querySelector('.toggle-warning')?.classList.toggle('on');
  }
  clickEvent4() {
    document.querySelector('.toggle-info ')?.classList.toggle('on');
  }
  clickEvent5() {
    document.querySelector('.toggle-success')?.classList.toggle('on');
  }
  clickEvent6() {
    document.querySelector('.toggle-danger')?.classList.toggle('on');
  }
  clickEvent7() {
    document.querySelector('.toggle-light')?.classList.toggle('on');
  } 
  clickEvent8() {
    document.querySelector('.toggle-dark')?.classList.toggle('on');
  } 
 
  clickEvent9() {
    document.querySelector('.toggle-sm')?.classList.toggle('on');
  }
  clickEvent10() {
    document.querySelector('.toggle-secondary1')?.classList.toggle('on');
  }
   clickEvent11() {
     document.querySelector('.toggle-lg')?.classList.toggle('on');
   }
}
