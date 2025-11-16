import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/paginations';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './pagination.component.html',
  styleUrls: ['./pagination.component.scss']
})
export class PaginationComponent {
  togglePagination() {
    this.isContentVisible1 = !this.isContentVisible1;
    if (this.toggleClass1 === "line") {
      this.toggleClass1 = "s-slash-line";
    } else {
      this.toggleClass1 = "line";
    }
  }
  toggleIcons() {
    this.isContentVisible2 = !this.isContentVisible2;
    if (this.toggleClass2 === "line") {
      this.toggleClass2 = "s-slash-line";
    } else {
      this.toggleClass2 = "line";
    }
  }
  
  
  toggleSizing() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleRight() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }  
  
  toggleDisabled() {
    this.isContentVisible5 = !this.isContentVisible5;
    if (this.toggleClass5 === "line") {
      this.toggleClass5 = "s-slash-line";
    } else {
      this.toggleClass5 = "line";
    }
  }  
  
  toggleStyle1() {
    this.isContentVisible6 = !this.isContentVisible6;
    if (this.toggleClass6 === "line") {
      this.toggleClass6 = "s-slash-line";
    } else {
      this.toggleClass6 = "line";
    }
  }  
  
  toggleStyle2() {
    this.isContentVisible7 = !this.isContentVisible7;
    if (this.toggleClass7 === "line") {
      this.toggleClass7 = "s-slash-line";
    } else {
      this.toggleClass7 = "line";
    }
  }  
  
  toggleStyle3() {
    this.isContentVisible8= !this.isContentVisible8;
    if (this.toggleClass8=== "line") {
      this.toggleClass8= "s-slash-line";
    } else {
      this.toggleClass8= "line";
    }
  }  
  
  toggleStyle4() {
    this.isContentVisible9 = !this.isContentVisible9;
    if (this.toggleClass9 === "line") {
      this.toggleClass9 = "s-slash-line";
    } else {
      this.toggleClass9 = "line";
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



  isContentVisible1 = false;
  isContentVisible2 = false;
  isContentVisible3 = false;
  isContentVisible4 = false;
  isContentVisible5 = false;
  isContentVisible6 = false;
  isContentVisible7 = false;
  isContentVisible8 = false;
  isContentVisible9 = false;

  ts1: string = codeData.paginationTS1;
  ts2: string = codeData.paginationTS2;
  ts3: string = codeData.paginationTS3;
  ts4: string = codeData.paginationTS4;
  ts5: string = codeData.paginationTS5;
  ts6: string = codeData.paginationTS6;
  ts7: string = codeData.paginationTS7;
  ts8: string = codeData.paginationTS8;
  ts9: string = codeData.paginationTS9;

}
