import { Component } from '@angular/core';
import flatpickr from 'flatpickr';
import { SharedModule } from '../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { MaterialModuleModule } from '../../../material-module/material-module.module';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-todolist',
  standalone: true,
  imports: [SharedModule,NgSelectModule,MaterialModuleModule,FlatpickrModule,FormsModule,ReactiveFormsModule],
  providers:[FlatpickrDefaults],
  templateUrl: './todolist.component.html',
  styleUrls: ['./todolist.component.scss']
})
export class TodolistComponent {
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
