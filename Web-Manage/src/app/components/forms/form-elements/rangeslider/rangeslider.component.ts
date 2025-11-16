import { Component } from '@angular/core';
import { FormGroup, FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgxSliderModule, Options } from 'ngx-slider-v2';
import { SharedModule } from '../../../../shared/shared.module';
import * as codeData from '../../../../shared/prismData/rangeslider';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-rangeslider',
  standalone: true,
  imports: [SharedModule,NgxSliderModule,FormsModule,ReactiveFormsModule],
  templateUrl: './rangeslider.component.html',
  styleUrl: './rangeslider.component.scss'
})
export class RangesliderComponent {
  minValue: number = 50;
  maxValue: number = 200;
  minValue2 = 10;
  maxValue2 = 90;
  value3 = 20;
  value4 = 60;
  options: Options = {
    floor: 0,
    ceil: 250,
  };
  options1: Options = {
    floor: 0,
    ceil: 100,
    step: 5,
  };
  sliderForm: FormGroup = new FormGroup({
    sliderControl: new FormControl([20, 80]),
  });
    // RoundedSlider
    value: number = 30;
    options2: Options = {
      floor: 0,
      ceil: 100,
      showSelectionBar: true,
    };
      // SquareStyling
  sliderControl1: FormControl = new FormControl(100);

  options3: Options = {
    floor: 0,
    ceil: 250,
  };

  resetForm1(): void {
    this.sliderControl1.reset(100);
  }
  red = 0;
  green = 0;
  blue = 0;

  updateColor(): void {
    // No changes required for this method
  }

  getColor(): string {
    return `rgb(${this.red}, ${this.green}, ${this.blue})`;
  }
  sliderControl: FormControl = new FormControl(100);
  options4: Options = {
    floor: 0,
    ceil: 100,
    step: 0,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#5a66f1',
      to: '#5a66f1',
    },
  };
    // ColoredConnectelements
    value1: number = 6;
    options5: Options = {
      floor: 0,
      ceil: 12,
      showSelectionBar: true,
      getSelectionBarColor: (value: number): string => {
        if (value <= 3) {
          return 'red';
        }
        if (value <= 6) {
          return 'orange';
        }
        if (value <= 9) {
          return 'yellow';
        }
        return '#2AE02A';
      },
    };
      // VerticalSlide
  value2: number = 6;
  options6: Options = {
    floor: 0,
    ceil: 50,
    showSelectionBar: true,
    vertical: true,
  };

  minValue11: number = 10;
maxValue11: number = 90;
options18: Options = {
  floor: 0,
  ceil: 100,
  step: 10,
  showTicks: true
};
  // SoftLimites
  value5: number = 5;
  options10: Options = {
    floor: 0,
    ceil: 10,
    showTicks: true,
    ticksTooltip: (v: number): string => {
      return 'Tooltip for ' + v;
    },
  };
  minValue5 = 15;
  maxValue5 = 85;
  options7: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#845adf',
      to: '#845adf',
    },
  };
  minValue6 = 15;
  maxValue6 = 85;
  options8: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#23b7e5',
      to: '#23b7e5',
    },
  };
  minValue7 = 15;
  maxValue7 = 85;
  options9: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#eab308',
      to: '#eab308',
    },
  };
  minValue8 = 15;
  maxValue8 = 85;
  options12: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#4c75cf',
      to: '#4c75cf',
    },
  };
  minValue9 = 15;
  maxValue9 = 85;
  options13: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#22c55e',
      to: '#22c55e',
    },
  };
  minValue10 = 15;
  maxValue10 = 85;
  options14: Options = {
    ceil: 50,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#f43f5e',
      to: '#f43f5e',
    },
  };
  options11: Options = {
    floor: 0,
    ceil: 12,
    showSelectionBar: true,
    selectionBarGradient: {
      from: '#5a66f1',
      to: '#5a66f1',
    },
  };
  minValue12 = 15;
  maxValue12 = 85;
  options15: Options = {
    floor: 0,
    ceil: 100,
    step: 1,
    minRange: 10,
    maxRange: 30,
    pushRange: true,
  };

  // disabled = false;
  // max = 100;
  // min = 0;
  // showTicks = false;
  // step = 1;
  // thumbLabel = false;
  // value = 20;
  isContentVisible1 = false;
  isContentVisible2 = false;
  isContentVisible3 = false;
  isContentVisible4 = false;
  toggleClass1 = "line";
  toggleClass2 = "line";
  toggleClass3 = "line";
  toggleClass4 = "line";
    
  ts1: string = codeData.rangeTS1;
  ts2: string = codeData.rangeTS2;
  ts3: string = codeData.rangeTS3;
  ts4: string = codeData.rangeTS4;

  toggleDefault() {
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
  
  toggleRange() {
    this.isContentVisible3= !this.isContentVisible3;
    if (this.toggleClass3=== "line") {
      this.toggleClass3= "s-slash-line";
    } else {
      this.toggleClass3= "line";
    }
  }  
  
  toggleSteps() {
    this.isContentVisible4 = !this.isContentVisible4;
    if (this.toggleClass4 === "line") {
      this.toggleClass4 = "s-slash-line";
    } else {
      this.toggleClass4 = "line";
    }
  }
}
