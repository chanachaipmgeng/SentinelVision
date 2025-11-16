import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/accordions';
import { SharedModule } from '../../../shared/shared.module';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-accordions',
  standalone: true,
  imports: [SharedModule,CommonModule],
  templateUrl: './accordions.component.html',
  styleUrls: ['./accordions.component.scss']
})
export class AccordionsComponent {
  

  toggleInput1() {
      this.isContentVisible1 = !this.isContentVisible1;
      if (this.toggleClass1 === "line") {
        this.toggleClass1 = "s-slash-line";
      } else {
        this.toggleClass1 = "line";
      }
    }
    
    
    toggleInput2() {
      this.isContentVisible2 = !this.isContentVisible2;
      if (this.toggleClass2 === "line") {
        this.toggleClass2 = "s-slash-line";
      } else {
        this.toggleClass2 = "line";
      }
    }  
    
    toggleInput3() {
      this.isContentVisible3= !this.isContentVisible3;
      if (this.toggleClass3=== "line") {
        this.toggleClass3= "s-slash-line";
      } else {
        this.toggleClass3= "line";
      }
    }  
    
    toggleInput4() {
      this.isContentVisible4 = !this.isContentVisible4;
      if (this.toggleClass4 === "line") {
        this.toggleClass4 = "s-slash-line";
      } else {
        this.toggleClass4 = "line";
      }
    }  
    
    toggleInput5() {
      this.isContentVisible5 = !this.isContentVisible5;
      if (this.toggleClass5 === "line") {
        this.toggleClass5 = "s-slash-line";
      } else {
        this.toggleClass5 = "line";
      }
    }  
    
    toggleInput6() {
      this.isContentVisible6 = !this.isContentVisible6;
      if (this.toggleClass6 === "line") {
        this.toggleClass6 = "s-slash-line";
      } else {
        this.toggleClass6 = "line";
      }
    }  
    
    toggleInput7() {
      this.isContentVisible7 = !this.isContentVisible7;
      if (this.toggleClass7 === "line") {
        this.toggleClass7 = "s-slash-line";
      } else {
        this.toggleClass7 = "line";
      }
    }  
    
    toggleInput8() {
      this.isContentVisible8= !this.isContentVisible8;
      if (this.toggleClass8=== "line") {
        this.toggleClass8= "s-slash-line";
      } else {
        this.toggleClass8= "line";
      }
    }  
    
    toggleInput9() {
      this.isContentVisible9 = !this.isContentVisible9;
      if (this.toggleClass9 === "line") {
        this.toggleClass9 = "s-slash-line";
      } else {
        this.toggleClass9 = "line";
      }
    }  
    
    toggleInput10() {
      this.isContentVisible10 = !this.isContentVisible10;
      if (this.toggleClass10 === "line") {
        this.toggleClass10 = "s-slash-line";
      } else {
        this.toggleClass10 = "line";
      }
    }  
    
    toggleInput11() {
      this.isContentVisible11 = !this.isContentVisible11;
      if (this.toggleClass11 === "line") {
        this.toggleClass11 = "s-slash-line";
      } else {
        this.toggleClass11 = "line";
      }
    }  
    
    

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

    ts1: string = codeData.accordionTS1;
    ts2: string = codeData.accordionTS2;
    ts3: string = codeData.accordionTS3;
    ts4: string = codeData.accordionTS4;
    ts5: string = codeData.accordionTS5;
    ts6: string = codeData.accordionTS6;
    ts7: string = codeData.accordionTS7;
    ts8: string = codeData.accordionTS8;
    ts9: string = codeData.accordionTS9;
    ts10: string = codeData.accordionTS10;
    ts11: string = codeData.accordionTS11;
  

}
