import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../../shared/shared.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';

@Component({
  selector: 'app-create-invoice',
  standalone: true,
  imports: [SharedModule,FlatpickrModule,FormsModule,ReactiveFormsModule,NgSelectModule,CommonModule],
  providers:[FlatpickrDefaults],
  templateUrl: './create-invoice.component.html',
  styleUrl: './create-invoice.component.scss'
})
export class CreateInvoiceComponent {
  quantity: number = 1;

  decreaseQuantity() {
    if (this.quantity > 1) {
      this.quantity--; 
    }
  }

  increaseQuantity() {
    this.quantity++; 

 
  }
  quantity1: number = 1;

  decreaseQuantity1() {
    if (this.quantity1 > 1) {
      this.quantity1--; 
    }
  }

  increaseQuantity1() {
    this.quantity1++; 

 
  }
  flatpickrOptions: any = {
    inline: true,
  };
  ngOnInit(): void{

    this.flatpickrOptions = {
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
    };
  
    flatpickr('#inlinetime', this.flatpickrOptions);
  
      this.flatpickrOptions = {
        enableTime: true,
        dateFormat: 'Y-m-d H:i', // Specify the format you want
        defaultDate: '2023-11-07 14:30', // Set the default/preloaded time (adjust this to your desired time)
      };
  
      flatpickr('#pretime', this.flatpickrOptions);
  }
}
