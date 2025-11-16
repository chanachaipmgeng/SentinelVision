import { Component, ElementRef, ViewChild } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-basic',
  standalone: true,
  imports: [SharedModule,RouterModule],
  templateUrl: './basic.component.html',
  styleUrls: ['./basic.component.scss']
})
export class BasicComponent {
   // Use @ViewChild to get references to the input elements in the template
   @ViewChild('oneInput') oneInput!: ElementRef<HTMLInputElement>;
   @ViewChild('twoInput') twoInput!: ElementRef<HTMLInputElement>;
   @ViewChild('threeInput') threeInput!: ElementRef<HTMLInputElement>;
   @ViewChild('fourInput') fourInput!: ElementRef<HTMLInputElement>;
 
   // Automatically move the focus to the next input field after entering a digit
   onDigitInput(event: KeyboardEvent, nextInput: HTMLInputElement | null): void {
     const inputElement = event.target as HTMLInputElement;
     if (inputElement.value.length > 0) {
       // If a digit is entered, move the focus to the next input field
       if (nextInput) {
         nextInput.focus();
       }
     }
   }
 
}
