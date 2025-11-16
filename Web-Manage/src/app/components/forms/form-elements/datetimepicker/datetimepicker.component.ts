import { Component } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { FlatpickrDefaults, FlatpickrModule } from 'angularx-flatpickr';
import flatpickr from 'flatpickr';
import { MaterialModuleModule } from '../../../../material-module/material-module.module';
import { SharedModule } from '../../../../shared/shared.module';


@Component({
  selector: 'app-datetimepicker',
  standalone: true,
  imports: [SharedModule,MaterialModuleModule,FormsModule,ReactiveFormsModule, MatDatepickerModule, FlatpickrModule],
  providers:[FlatpickrDefaults],
  templateUrl: './datetimepicker.component.html',
  styleUrl: './datetimepicker.component.scss'
})
export class DatetimepickerComponent {
  basicDemoValue = '2017-01-01';
  inlineDatePicker: Date = new Date();
  timePicker: Date | null = null;
  timePicker1: Date | null = null;
  timePicker2: Date | null = null;
  timePicker3: Date | null = null;
  timePicker4: Date | null = null;

  flatpickrOptions: any = {
    inline: true,
  };
  // flatpickrOptions: FlatpickrOptions;

  constructor() {}

  ngOnInit() {
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
