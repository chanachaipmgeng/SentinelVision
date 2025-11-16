import { Component } from '@angular/core';
import * as codeData from '../../../shared/prismData/basictables';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { SharedModule } from '../../../shared/shared.module';

@Component({
  selector: 'app-tables',
  standalone: true,
  imports: [SharedModule,MaterialModuleModule],
  templateUrl: './tables.component.html',
  styleUrls: ['./tables.component.scss']
})
export class TablesComponent {
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
  isContentVisible23 = false;
  isContentVisible24 = false;
  isContentVisible25 = false;
  isContentVisible26 = false;
  isContentVisible27 = false;
  isContentVisible28 = false;
  isContentVisible29 = false;
  isContentVisible30 = false;
  isContentVisible31 = false;
  isContentVisible32 = false;



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
  toggleClass23 = "line";
  toggleClass24 = "line";
  toggleClass25 = "line";
  toggleClass26 = "line";
  toggleClass27 = "line";
  toggleClass28 = "line";
  toggleClass29 = "line";
  toggleClass30 = "line";
  toggleClass31 = "line";
  toggleClass32 = "line";


  

  ts1: string = codeData.basicTablesTS1;
  ts2: string = codeData.basicTablesTS2;
  ts3: string = codeData.basicTablesTS3;
  ts4: string = codeData.basicTablesTS4;
  ts5: string = codeData.basicTablesTS5;
  ts6: string = codeData.basicTablesTS6;
  ts7: string = codeData.basicTablesTS7;
  ts8: string = codeData.basicTablesTS8;
  ts9: string = codeData.basicTablesTS9;
  ts10: string = codeData.basicTablesTS10;
  ts11: string = codeData.basicTablesTS11;
  ts12: string = codeData.basicTablesTS12;
  ts13: string = codeData.basicTablesTS13;
  ts14: string = codeData.basicTablesTS14;
  ts15: string = codeData.basicTablesTS15;
  ts16: string = codeData.basicTablesTS16;
  ts17: string = codeData.basicTablesTS17;
  ts18: string = codeData.basicTablesTS18;
  ts19: string = codeData.basicTablesTS19;
  ts20: string = codeData.basicTablesTS20;
  ts21: string = codeData.basicTablesTS21;
  ts22: string = codeData.basicTablesTS22;
  ts23: string = codeData.basicTablesTS23;
  ts24: string = codeData.basicTablesTS24;
  ts25: string = codeData.basicTablesTS25;
  ts26: string = codeData.basicTablesTS26;
  ts27: string = codeData.basicTablesTS27;
  ts28: string = codeData.basicTablesTS28;
  ts29: string = codeData.basicTablesTS29;
  ts30: string = codeData.basicTablesTS30;
  ts31: string = codeData.basicTablesTS31;
  ts32: string = codeData.basicTablesTS32;
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
  
  toggleInput12() {
    this.isContentVisible12 = !this.isContentVisible12;
    if (this.toggleClass12 === "line") {
      this.toggleClass12 = "s-slash-line";
    } else {
      this.toggleClass12 = "line";
    }
  }  
  
  toggleInput13() {
    this.isContentVisible13 = !this.isContentVisible13;
    if (this.toggleClass13 === "line") {
      this.toggleClass13 = "s-slash-line";
    } else {
      this.toggleClass13 = "line";
    }
  }  
  
  toggleInput14() {
    this.isContentVisible14 = !this.isContentVisible14;
    if (this.toggleClass14 === "line") {
      this.toggleClass14 = "s-slash-line";
    } else {
      this.toggleClass14 = "line";
    }
  }  
  
  toggleInput15() {
    this.isContentVisible15 = !this.isContentVisible15;
    if (this.toggleClass15 === "line") {
      this.toggleClass15 = "s-slash-line";
    } else {
      this.toggleClass15 = "line";
    }
  }  
  
  toggleInput16() {
    this.isContentVisible16 = !this.isContentVisible16;
    if (this.toggleClass16 === "line") {
      this.toggleClass16 = "s-slash-line";
    } else {
      this.toggleClass16 = "line";
    }
  }  
  
  toggleInput17() {
    this.isContentVisible17 = !this.isContentVisible17;
    if (this.toggleClass17 === "line") {
      this.toggleClass17 = "s-slash-line";
    } else {
      this.toggleClass17 = "line";
    }
  }  
  
  toggleInput18() {
    this.isContentVisible18 = !this.isContentVisible18;
    if (this.toggleClass18 === "line") {
      this.toggleClass18 = "s-slash-line";
    } else {
      this.toggleClass18 = "line";
    }
  }  
  
  toggleInput19() {
    this.isContentVisible19 = !this.isContentVisible19;
    if (this.toggleClass19 === "line") {
      this.toggleClass19 = "s-slash-line";
    } else {
      this.toggleClass19 = "line";
    }
  }  
  
  toggleInput20() {
    this.isContentVisible20 = !this.isContentVisible20;
    if (this.toggleClass20 === "line") {
      this.toggleClass20 = "s-slash-line";
    } else {
      this.toggleClass20 = "line";
    }
  }  
  
  toggleInput21() {
    this.isContentVisible21 = !this.isContentVisible21;
    if (this.toggleClass21 === "line") {
      this.toggleClass21 = "s-slash-line";
    } else {
      this.toggleClass21 = "line";
    }
  }  
  
  toggleInput22() {
    this.isContentVisible22 = !this.isContentVisible22;
    if (this.toggleClass22 === "line") {
      this.toggleClass22 = "s-slash-line";
    } else {
      this.toggleClass22 = "line";
    }
  }  
  toggleInput23() {
    this.isContentVisible23 = !this.isContentVisible23;
    if (this.toggleClass23 === "line") {
      this.toggleClass23 = "s-slash-line";
    } else {
      this.toggleClass23 = "line";
    }
  }  
  toggleInput24() {
    this.isContentVisible24 = !this.isContentVisible24;
    if (this.toggleClass24 === "line") {
      this.toggleClass24 = "s-slash-line";
    } else {
      this.toggleClass24 = "line";
    }
  }  
  toggleInput25() {
    this.isContentVisible25 = !this.isContentVisible25;
    if (this.toggleClass25 === "line") {
      this.toggleClass25 = "s-slash-line";
    } else {
      this.toggleClass25 = "line";
    }
  }  
  toggleInput26() {
    this.isContentVisible26 = !this.isContentVisible26;
    if (this.toggleClass26 === "line") {
      this.toggleClass26 = "s-slash-line";
    } else {
      this.toggleClass26 = "line";
    }
  }  
  toggleInput27() {
    this.isContentVisible27 = !this.isContentVisible27;
    if (this.toggleClass27 === "line") {
      this.toggleClass27 = "s-slash-line";
    } else {
      this.toggleClass27 = "line";
    }
  } 
  toggleInput28() {
    this.isContentVisible28 = !this.isContentVisible28;
    if (this.toggleClass28 === "line") {
      this.toggleClass28 = "s-slash-line";
    } else {
      this.toggleClass28 = "line";
    }
  } 
  toggleInput29() {
    this.isContentVisible29 = !this.isContentVisible29;
    if (this.toggleClass29 === "line") {
      this.toggleClass29 = "s-slash-line";
    } else {
      this.toggleClass29 = "line";
    }
  } 
  toggleInput30() {
    this.isContentVisible30 = !this.isContentVisible30;
    if (this.toggleClass30 === "line") {
      this.toggleClass30 = "s-slash-line";
    } else {
      this.toggleClass30 = "line";
    }
  } 
  toggleInput31() {
    this.isContentVisible31 = !this.isContentVisible31;
    if (this.toggleClass31 === "line") {
      this.toggleClass31 = "s-slash-line";
    } else {
      this.toggleClass31 = "line";
    }
  } 
  toggleInput32() {
    this.isContentVisible32 = !this.isContentVisible32;
    if (this.toggleClass32 === "line") {
      this.toggleClass32 = "s-slash-line";
    } else {
      this.toggleClass32 = "line";
    }
  }
}
